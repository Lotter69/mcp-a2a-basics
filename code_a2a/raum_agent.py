#!/usr/bin/env python3
"""
A2A-Server: Raumbuchungs-Agent des Netzwerklabors
Rolle: Fachagent (A2A-Server nach außen, MCP-Client nach innen, ohne LLM)

Der Raumbuchungs-Agent reserviert die Laborräume 104 und 105 für einen Wochentag.

- Nach AUSSEN: A2A, JSON-RPC über HTTP, Port 9997
- Nach INNEN:  MCP-Tool laborraum_belegung_abfragen

Regeln:
  - Wochentag fehlt                       -> Rückfrage           (INPUT_REQUIRED)
  - Wunschraum frei (oder kein Wunsch)    -> reserviert          (COMPLETED, Artefakt "reservierung")
  - Wunschraum belegt, anderer frei       -> Gegenvorschlag      (INPUT_REQUIRED, "ja"/"nein")
      "nein"                              -> abgebrochen         (CANCELED)
  - beide Räume belegt                    -> Ablehnung           (REJECTED)

Reservierungen merkt sich der Agent nur im Arbeitsspeicher (bis zum Neustart).

Start: python raum_agent.py
"""

import asyncio
import re

from a2a.helpers import new_data_part, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from fachagent_hilfen import agent_starten, mcp_tool_aufrufen, nachrichten_des_auftrags, text_und_daten

HOST = "127.0.0.1"
PORT = 9997
RAEUME = ["104", "105"]
TAGE = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]
RESERVIERUNGEN = {}   # (raum, tag) -> True, nur im Arbeitsspeicher


# =============================================================================
# 1. AGENT CARD
# =============================================================================

SKILL_RAUM = AgentSkill(
    id="laborraum_buchen",
    name="Laborraum reservieren",
    description=(
        "Prüft die Belegung der Laborräume 104 und 105 und reserviert einen freien Raum "
        "für einen Wochentag (Montag bis Freitag). Schlägt bei Belegung einen anderen Raum vor."
    ),
    tags=["raum", "reservierung", "labor"],
    examples=["Reserviere Raum 104 für Donnerstag.", "Ist am Mittwoch ein Laborraum frei?"],
    input_modes=["text/plain", "application/json"],
    output_modes=["text/plain", "application/json"],
)

AGENT_CARD = AgentCard(
    name="Raumbuchungs-Agent Netzwerklabor",
    description="Verwaltet die Belegung der Laborräume und nimmt Reservierungen an.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC",
                                         url=f"http://{HOST}:{PORT}", protocol_version="1.0")],
    skills=[SKILL_RAUM],
)


# =============================================================================
# 2. AUFTRAG VERSTEHEN (einfache Regeln, kein LLM)
# =============================================================================

def auftrag_verstehen(nachrichten) -> dict:
    auftrag = {"raum": None, "tag": None, "zustimmung": None}
    for nachricht in nachrichten:
        text, daten_liste = text_und_daten(nachricht)
        for daten in daten_liste:
            if isinstance(daten, dict):
                auftrag["raum"] = str(daten.get("raum", auftrag["raum"] or "")) or None
                auftrag["tag"] = daten.get("tag", auftrag["tag"])
        raum = re.search(r"\b(104|105)\b", text)
        if raum:
            auftrag["raum"] = raum.group(1)
        for tag in TAGE:
            if tag in text:
                auftrag["tag"] = tag
        woerter = re.findall(r"\w+", text)
        if "ja" in woerter or "ok" in woerter:
            auftrag["zustimmung"] = True
        if "nein" in woerter:
            auftrag["zustimmung"] = False
    return auftrag


async def ist_frei(raum: str, tag: str) -> bool:
    """Fragt das MCP-Tool und berücksichtigt eigene Reservierungen."""
    text = await mcp_tool_aufrufen("laborraum_belegung_abfragen", {"raum": raum, "tag": tag})
    return text.endswith("frei") and (raum, tag) not in RESERVIERUNGEN


# =============================================================================
# 3. AGENT-LOGIK
# =============================================================================

class RaumAgentExecutor(AgentExecutor):

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task:
            task = context.current_task
            print(f"\n[A2A] Folgenachricht zu Task {task.id[:8]}...")
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
            print(f"\n[A2A] Neuer Task {task.id[:8]}... (Zustand: SUBMITTED)")

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        def nachricht(text):
            return new_text_message(text, task_id=task.id, context_id=task.context_id)

        await updater.start_work(nachricht("Raumbuchungs-Agent prüft die Belegung ..."))
        print("   -> In Arbeit (Zustand: WORKING)")
        await asyncio.sleep(1)  # nur zur Veranschaulichung

        auftrag = auftrag_verstehen(nachrichten_des_auftrags(context, task))
        print(f"   Verstanden: {auftrag}")

        if auftrag["tag"] is None:
            print("   -> Rückfrage: Tag fehlt (Zustand: INPUT_REQUIRED)")
            await updater.requires_input(nachricht("Für welchen Wochentag (Montag bis Freitag)?"))
            return

        wunsch = auftrag["raum"]
        reihenfolge = [wunsch] + [r for r in RAEUME if r != wunsch] if wunsch else RAEUME
        freier_raum = None
        for raum in reihenfolge:
            if await ist_frei(raum, auftrag["tag"]):
                freier_raum = raum
                break

        if freier_raum is None:
            print("   -> Abgelehnt: alle Räume belegt (Zustand: REJECTED)")
            await updater.reject(nachricht(f"Am {auftrag['tag'].capitalize()} sind beide Laborräume belegt."))
            return

        # Gegenvorschlag, wenn der Wunschraum belegt ist
        if wunsch and freier_raum != wunsch:
            if auftrag["zustimmung"] is None:
                print(f"   -> Gegenvorschlag Raum {freier_raum} (Zustand: INPUT_REQUIRED)")
                await updater.requires_input(nachricht(
                    f"Raum {wunsch} ist am {auftrag['tag'].capitalize()} belegt. Raum {freier_raum} ist frei. "
                    f"Soll ich Raum {freier_raum} reservieren? (ja/nein)"))
                return
            if auftrag["zustimmung"] is False:
                print("   -> Abgebrochen (Zustand: CANCELED)")
                await updater.cancel(nachricht("Keine Reservierung vorgenommen."))
                return

        RESERVIERUNGEN[(freier_raum, auftrag["tag"])] = True
        ergebnis = {"raum": freier_raum, "tag": auftrag["tag"], "reserviert": True}
        await updater.add_artifact(
            name="reservierung",
            parts=[new_text_part(f"Raum {freier_raum} ist für {auftrag['tag'].capitalize()} reserviert.",
                                 media_type="text/plain"),
                   new_data_part(ergebnis, media_type="application/json")])
        print(f"   Artefakt 'reservierung': {ergebnis}")
        await updater.complete(nachricht("Reservierung abgeschlossen."))
        print("   -> Erledigt (Zustand: COMPLETED)")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Abbrechen wird nicht unterstützt.")


if __name__ == "__main__":
    agent_starten(AGENT_CARD, RaumAgentExecutor(), HOST, PORT)
