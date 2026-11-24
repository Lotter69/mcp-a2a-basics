#!/usr/bin/env python3
"""
A2A-Server: Lager-Agent des Netzwerklabors
Rolle: Fachagent (A2A-Server nach außen, MCP-Client nach innen, ohne LLM)

Der Lager-Agent ist ein eigenständiger Agent mit eigener Aufgabe:
Er beantwortet Anfragen zur Verfügbarkeit von Patchkabeln im Lager.

- Nach AUSSEN spricht er A2A (Agent2Agent-Protokoll, JSON-RPC über HTTP, Port 9999).
- Nach INNEN nutzt er sein Werkzeug über MCP: Er startet mcp_server.py und ruft
  das Tool patchkabel_bestand_abfragen auf. Davon sieht der anfragende Agent nichts.

Aufbau dieser Datei:
  1. Agent Card   - die "Visitenkarte" (was kann der Agent, wie erreicht man ihn?)
  2. Werkzeug     - Zugriff auf das MCP-Tool (wie in MCP-Basics)
  3. Agent-Logik  - AgentExecutor: verarbeitet Aufgaben (Tasks) und meldet Zustände
  4. Server-Setup - HTTP-Server mit den A2A-Routen

Bibliothek: a2a-sdk 1.x (A2A-Spezifikation 1.0), mcp 2.x
Start:      python lager_agent.py
"""

import asyncio
import re

from a2a.helpers import (
    get_data_parts,
    get_text_parts,
    new_data_part,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from fachagent_hilfen import agent_starten, mcp_tool_aufrufen, nachrichten_des_auftrags

HOST = "127.0.0.1"
PORT = 9999          # Lager 9999, Bestellung 9998, Raumbuchung 9997 (siehe agenten.json)


# =============================================================================
# 1. AGENT CARD - die Visitenkarte des Agenten
#    Abrufbar unter http://127.0.0.1:9999/.well-known/agent-card.json
# =============================================================================

SKILL_BESTAND = AgentSkill(
    id="bestand_pruefen",
    name="Patchkabel-Bestand prüfen",
    description=(
        "Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager "
        "VORHANDEN ist, und meldet Bestand und Fehlmenge. Bestellt nichts."
    ),
    tags=["lager", "patchkabel", "netzwerklabor"],
    examples=[
        "Haben wir 30 blaue Patchkabel?",
        "Wie viele rote Patchkabel sind auf Lager?",
        '{"farbe": "blau", "menge": 30}',
    ],
    input_modes=["text/plain", "application/json"],
    output_modes=["text/plain", "application/json"],
)

AGENT_CARD = AgentCard(
    name="Lager-Agent Netzwerklabor",
    description="Verwaltet das Materiallager des Netzwerklabors und beantwortet Bestandsanfragen.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",          # Transport: JSON-RPC 2.0 über HTTP
            url=f"http://{HOST}:{PORT}",         # Hierhin schickt der Client seine Anfragen
            protocol_version="1.0",              # A2A-Protokollversion
        )
    ],
    skills=[SKILL_BESTAND],
)


# =============================================================================
# 2. WERKZEUG - das MCP-Tool aus Teil 1 (MCP-Basics)
#    Der Lager-Agent ist hier MCP-Client (Agent <-> Werkzeug).
#    mcp_tool_aufrufen() steht in fachagent_hilfen.py und startet mcp_server.py über stdio.
# =============================================================================

async def mcp_bestand_abfragen(farbe: str) -> str:
    """Ruft das Tool patchkabel_bestand_abfragen des MCP-Servers auf."""
    return await mcp_tool_aufrufen("patchkabel_bestand_abfragen", {"farbe": farbe})


def zahl_aus_tool_text(text: str, farbe: str) -> int:
    """Liest die Stückzahl aus dem Text des MCP-Tools."""
    if farbe == "gesamt":
        treffer = re.search(r"Gesamt:\s*(\d+)", text)
    else:
        treffer = re.search(r":\s*(\d+)\s*Stück", text)
    return int(treffer.group(1)) if treffer else 0


# =============================================================================
# 3. AGENT-LOGIK - der AgentExecutor
#    Wird für jede eingehende Nachricht aufgerufen. Er liest die Nachricht,
#    meldet Zustandsänderungen der Aufgabe (Task) und liefert Ergebnisse (Artifacts).
# =============================================================================

FARBEN_IM_SORTIMENT = {"blau", "rot", "gesamt"}
FARBEN_NICHT_IM_SORTIMENT = {"grün", "gruen", "gelb", "schwarz", "weiß", "weiss", "grau", "orange"}


def auftrag_verstehen(nachrichten) -> dict:
    """
    Ermittelt Farbe und Menge aus allen bisherigen Nachrichten des Auftraggebers.
    Strukturierte Daten (data-Part) haben Vorrang vor Text (text-Part).
    Spätere Nachrichten (z. B. Antwort auf eine Rückfrage) ergänzen frühere.

    Hinweis: Der Lager-Agent verwendet hier einfache Regeln statt eines LLM.
    Für den anfragenden Agenten ist das nicht sichtbar - er sieht nur die Agent Card.
    """
    auftrag = {"farbe": None, "menge": None}
    for nachricht in nachrichten:
        # a) strukturierte Daten, z. B. {"farbe": "blau", "menge": 30}
        for daten in get_data_parts(nachricht.parts):
            if isinstance(daten, dict):
                if daten.get("farbe"):
                    auftrag["farbe"] = str(daten["farbe"]).lower()
                if daten.get("menge") is not None:
                    auftrag["menge"] = int(daten["menge"])
        # b) freier Text, z. B. "Haben wir 30 blaue Patchkabel?"
        text = " ".join(get_text_parts(nachricht.parts)).lower()
        woerter = re.findall(r"\w+", text)
        for wort in woerter:
            if wort.startswith("blau"):
                auftrag["farbe"] = "blau"
            elif wort in ("rot", "rote", "roten", "roter", "rotes"):
                auftrag["farbe"] = "rot"
            elif wort in ("gesamt", "insgesamt", "alle", "gesamtbestand"):
                auftrag["farbe"] = "gesamt"
            elif any(wort.startswith(f) for f in FARBEN_NICHT_IM_SORTIMENT):
                auftrag["farbe"] = wort
        menge = re.search(r"\b(\d+)\b(?!\s*m\b)", text)   # "30" ja, "1 m" nein
        if menge:
            auftrag["menge"] = int(menge.group(1))
    return auftrag


class LagerAgentExecutor(AgentExecutor):
    """Verarbeitet Aufträge an den Lager-Agenten."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # --- 3.1 Aufgabe (Task) holen oder neu anlegen --------------------------
        if context.current_task:                       # Folgenachricht zu einer bestehenden Aufgabe
            task = context.current_task
            print(f"\n[A2A] Folgenachricht zu Task {task.id[:8]}...")
        else:                                          # Neue Aufgabe -> Zustand SUBMITTED
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
            print(f"\n[A2A] Neuer Task {task.id[:8]}... (Zustand: SUBMITTED)")

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # Alle Nachrichten des Auftraggebers dieser Aufgabe (Verlauf + neue Nachricht)
        nachrichten = nachrichten_des_auftrags(context, task)
        print(f"   Nachricht: {' '.join(get_text_parts(context.message.parts)) or get_data_parts(context.message.parts)}")

        # --- 3.2 Zustand WORKING melden ----------------------------------------
        await updater.start_work(new_text_message("Lager-Agent prüft die Anfrage ...",
                                                  task_id=task.id, context_id=task.context_id))
        print("   -> In Arbeit (Zustand: WORKING)")
        await asyncio.sleep(1)  # nur zur Veranschaulichung: Zwischenstand bleibt kurz sichtbar

        auftrag = auftrag_verstehen(nachrichten)
        print(f"   Verstanden: {auftrag}")

        # --- 3.3 Fehlende Angabe? -> Rückfrage, Zustand INPUT_REQUIRED ----------
        if auftrag["farbe"] is None:
            print("   -> Rückfrage (Zustand: INPUT_REQUIRED)")
            await updater.requires_input(new_text_message(
                "Welche Farbe wird benötigt? Im Sortiment sind blau und rot (oder 'gesamt').",
                task_id=task.id, context_id=task.context_id))
            return                                     # Aufgabe pausiert, bis die Antwort kommt

        # --- 3.4 Nicht im Sortiment? -> Zustand REJECTED -------------------------
        if auftrag["farbe"] not in FARBEN_IM_SORTIMENT:
            print("   -> Abgelehnt (Zustand: REJECTED)")
            await updater.reject(new_text_message(
                f"Patchkabel in der Farbe '{auftrag['farbe']}' führt das Lager nicht. "
                "Im Sortiment: blau und rot (je 1 m).",
                task_id=task.id, context_id=task.context_id))
            return

        # --- 3.5 Werkzeug benutzen (MCP) -----------------------------------------
        tool_text = await mcp_bestand_abfragen(auftrag["farbe"])
        bestand = zahl_aus_tool_text(tool_text, auftrag["farbe"])

        # --- 3.6 Ergebnis als Artefakt liefern -----------------------------------
        ergebnis = {"farbe": auftrag["farbe"], "laenge_m": 1, "bestand": bestand}
        if auftrag["menge"] is not None:
            ergebnis["angefragt"] = auftrag["menge"]
            ergebnis["ausreichend"] = bestand >= auftrag["menge"]
            ergebnis["fehlmenge"] = max(0, auftrag["menge"] - bestand)
            zusammenfassung = (
                f"{auftrag['menge']} Stück angefragt, {bestand} Stück auf Lager: "
                + ("ausreichend." if ergebnis["ausreichend"]
                   else f"es fehlen {ergebnis['fehlmenge']} Stück.")
            )
        else:
            zusammenfassung = tool_text

        await updater.add_artifact(
            name="bestandsauskunft",
            parts=[
                new_text_part(zusammenfassung, media_type="text/plain"),
                new_data_part(ergebnis, media_type="application/json"),
            ],
        )
        print(f"   Artefakt 'bestandsauskunft': {ergebnis}")

        # --- 3.7 Zustand COMPLETED ------------------------------------------------
        await updater.complete(new_text_message("Bestandsprüfung abgeschlossen.",
                                                task_id=task.id, context_id=task.context_id))
        print("   -> Erledigt (Zustand: COMPLETED)")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Abbrechen wird vom Lager-Agenten nicht unterstützt.")


# =============================================================================
# 4. SERVER-SETUP - HTTP-Server mit den A2A-Routen (siehe fachagent_hilfen.py)
# =============================================================================

if __name__ == "__main__":
    agent_starten(AGENT_CARD, LagerAgentExecutor(), HOST, PORT)
