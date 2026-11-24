#!/usr/bin/env python3
"""
A2A-Server: Bestell-Agent des Netzwerklabors
Rolle: Fachagent (A2A-Server nach außen, MCP-Client nach innen, ohne LLM)

Der Bestell-Agent bestellt Patchkabel beim Lieferanten nach (simuliert).
Er führt auch Farben, die das Lager nicht hat (gelb, grün, schwarz).

- Nach AUSSEN: A2A, JSON-RPC über HTTP, Port 9998
- Nach INNEN:  MCP-Tool patchkabel_katalog_abfragen (Preis, Lieferzeit)

Regeln (seine eigene Entscheidung, nicht die des Auftraggebers):
  - Farbe oder Menge fehlt              -> Rückfrage        (INPUT_REQUIRED)
  - Farbe nicht im Katalog              -> Ablehnung        (REJECTED)
  - Summe über dem Budget von 250 Euro  -> Ablehnung        (REJECTED)
  - Summe über 50 Euro                  -> Freigabe erfragen (INPUT_REQUIRED, "ja"/"nein")
      "nein"                            -> abgebrochen      (CANCELED)
  - sonst                               -> bestellt         (COMPLETED, Artefakt "bestellbestaetigung")

Start: python bestell_agent.py
"""

import asyncio
import re
import uuid

from a2a.helpers import new_data_part, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from fachagent_hilfen import agent_starten, mcp_tool_aufrufen, nachrichten_des_auftrags, text_und_daten

HOST = "127.0.0.1"
PORT = 9998
FREIGABE_AB_EURO = 50.0
BUDGET_EURO = 250.0


# =============================================================================
# 1. AGENT CARD
# =============================================================================

SKILL_BESTELLEN = AgentSkill(
    id="material_bestellen",
    name="Patchkabel nachbestellen",
    description=(
        "Bestellt Patchkabel (1 m) beim Lieferanten NACH, auch Farben, die das Lager nicht führt "
        "(blau, rot, gelb, gruen, schwarz). Nennt Preis und Lieferzeit. Prüft KEINEN Lagerbestand. "
        "Bestellungen über 50 Euro brauchen eine Freigabe."
    ),
    tags=["bestellung", "lieferant", "patchkabel"],
    examples=["Bestelle 20 gelbe Patchkabel nach.", '{"farbe": "gelb", "menge": 20}'],
    input_modes=["text/plain", "application/json"],
    output_modes=["text/plain", "application/json"],
)

AGENT_CARD = AgentCard(
    name="Bestell-Agent Netzwerklabor",
    description="Bestellt Verbrauchsmaterial für das Netzwerklabor beim Lieferanten nach.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC",
                                         url=f"http://{HOST}:{PORT}", protocol_version="1.0")],
    skills=[SKILL_BESTELLEN],
)


# =============================================================================
# 2. AUFTRAG VERSTEHEN (einfache Regeln, kein LLM)
# =============================================================================

FARBWOERTER = {"blau": "blau", "rot": "rot", "gelb": "gelb", "grün": "gruen", "gruen": "gruen",
               "schwarz": "schwarz", "weiß": "weiss", "weiss": "weiss", "lila": "lila", "orange": "orange"}


def auftrag_verstehen(nachrichten) -> dict:
    """Farbe, Menge und Freigabe aus allen Nachrichten des Auftraggebers."""
    auftrag = {"farbe": None, "menge": None, "freigabe": None}
    for nachricht in nachrichten:
        text, daten_liste = text_und_daten(nachricht)
        for daten in daten_liste:
            if isinstance(daten, dict):
                auftrag["farbe"] = daten.get("farbe", auftrag["farbe"])
                if daten.get("menge") is not None:
                    auftrag["menge"] = int(daten["menge"])
        for wort in re.findall(r"\w+", text):
            for stamm, farbe in FARBWOERTER.items():
                if wort.startswith(stamm) and (stamm != "rot" or wort in ("rot", "rote", "roten", "roter")):
                    auftrag["farbe"] = farbe
            if wort in ("ja", "freigeben", "freigegeben", "ok"):
                auftrag["freigabe"] = True
            if wort in ("nein", "abbrechen", "stopp"):
                auftrag["freigabe"] = False
        menge = re.search(r"\b(\d+)\b(?!\s*m\b)", text)
        if menge:
            auftrag["menge"] = int(menge.group(1))
    return auftrag


def katalog_lesen(text: str) -> tuple[float, int] | None:
    """Liest Preis und Lieferzeit aus dem Text des MCP-Tools."""
    treffer = re.search(r"([\d.]+) Euro pro Stück, Lieferzeit (\d+)", text)
    return (float(treffer.group(1)), int(treffer.group(2))) if treffer else None


# =============================================================================
# 3. AGENT-LOGIK
# =============================================================================

class BestellAgentExecutor(AgentExecutor):

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

        await updater.start_work(nachricht("Bestell-Agent prüft die Bestellung ..."))
        print("   -> In Arbeit (Zustand: WORKING)")
        await asyncio.sleep(1)  # nur zur Veranschaulichung

        auftrag = auftrag_verstehen(nachrichten_des_auftrags(context, task))
        print(f"   Verstanden: {auftrag}")

        # Farbe nicht im Katalog? -> Ablehnung (vor jeder Rückfrage)
        if auftrag["farbe"] is not None and auftrag["farbe"] not in ("blau", "rot", "gelb", "gruen", "schwarz"):
            print("   -> Abgelehnt: nicht im Katalog (Zustand: REJECTED)")
            await updater.reject(nachricht(f"Patchkabel in '{auftrag['farbe']}' führt der Lieferant nicht."))
            return

        # Rückfrage, wenn Angaben fehlen
        if auftrag["farbe"] is None or auftrag["menge"] is None:
            fehlt = "Farbe" if auftrag["farbe"] is None else "Menge"
            print(f"   -> Rückfrage: {fehlt} fehlt (Zustand: INPUT_REQUIRED)")
            await updater.requires_input(nachricht(
                f"Welche {fehlt} soll bestellt werden?" if fehlt == "Farbe"
                else "Wie viele Patchkabel sollen bestellt werden?"))
            return

        # Werkzeug: Preis und Lieferzeit beim Lieferanten
        katalog = katalog_lesen(await mcp_tool_aufrufen("patchkabel_katalog_abfragen",
                                                        {"farbe": auftrag["farbe"]}))
        preis, lieferzeit = katalog
        summe = round(preis * auftrag["menge"], 2)

        # Eigene Regeln: Budget und Freigabe
        if summe > BUDGET_EURO:
            print(f"   -> Abgelehnt: {summe:.2f} Euro über Budget (Zustand: REJECTED)")
            await updater.reject(nachricht(
                f"Die Bestellung kostet {summe:.2f} Euro und überschreitet das Budget von {BUDGET_EURO:.0f} Euro."))
            return
        if summe > FREIGABE_AB_EURO and auftrag["freigabe"] is None:
            print(f"   -> Freigabe nötig: {summe:.2f} Euro (Zustand: INPUT_REQUIRED)")
            await updater.requires_input(nachricht(
                f"Die Bestellung über {auftrag['menge']} {auftrag['farbe']}e Patchkabel kostet {summe:.2f} Euro. "
                "Bestellungen über 50 Euro brauchen eine Freigabe. Freigeben? (ja/nein)"))
            return
        if auftrag["freigabe"] is False:
            print("   -> Abgebrochen (Zustand: CANCELED)")
            await updater.cancel(nachricht("Bestellung nicht freigegeben, Vorgang abgebrochen."))
            return

        # Bestellen (simuliert) und Ergebnis als Artefakt
        ergebnis = {"bestellnummer": "B-" + uuid.uuid4().hex[:6].upper(), "farbe": auftrag["farbe"],
                    "menge": auftrag["menge"], "einzelpreis_euro": preis, "summe_euro": summe,
                    "lieferzeit_werktage": lieferzeit}
        await updater.add_artifact(
            name="bestellbestaetigung",
            parts=[new_text_part(f"Bestellt: {auftrag['menge']} x {auftrag['farbe']} für {summe:.2f} Euro, "
                                 f"Lieferung in {lieferzeit} Werktagen.", media_type="text/plain"),
                   new_data_part(ergebnis, media_type="application/json")])
        print(f"   Artefakt 'bestellbestaetigung': {ergebnis}")
        await updater.complete(nachricht("Bestellung ausgelöst."))
        print("   -> Erledigt (Zustand: COMPLETED)")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Abbrechen wird nicht unterstützt.")


if __name__ == "__main__":
    agent_starten(AGENT_CARD, BestellAgentExecutor(), HOST, PORT)
