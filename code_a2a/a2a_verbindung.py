#!/usr/bin/env python3
"""
A2A-Verbindung: kleine Hilfsschicht für die A2A-Clients dieser Lab-Reihe

Enthält alles, was ein Auftraggeber (A2A-Client) braucht, um Fachagenten (A2A-Server) zu beauftragen:
  1. Discovery     - Agent Cards aller Fachagenten aus agenten.json abrufen (Mini-Registry)
  2. Auftrag       - Nachricht (Message) senden, Aufgabe (Task) zurückbekommen
  3. Auswertung    - Zustand, Rückfragen und Artefakte lesbar machen
  4. Delegation    - einen Auftrag bis zum Endzustand begleiten (inkl. Rückfragen)

Wird verwendet von: a2a_client.py, planungs_agent_ollama.py, planungs_agent.py
"""

import json
import uuid
from pathlib import Path

import httpx
from google.protobuf.json_format import MessageToDict

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, get_text_parts, new_data_part, new_text_part
from a2a.types import AgentCard, Message, Role, SendMessageRequest, Task, TaskState

LAGER_AGENT_URL = "http://127.0.0.1:9999"
AGENTEN_DATEI = Path(__file__).with_name("agenten.json")   # Mini-Registry: Name -> Basisadresse

# Lesbare Namen der Task-Zustände
ZUSTAND = {
    TaskState.TASK_STATE_SUBMITTED: "SUBMITTED (eingereicht)",
    TaskState.TASK_STATE_WORKING: "WORKING (in Arbeit)",
    TaskState.TASK_STATE_INPUT_REQUIRED: "INPUT_REQUIRED (Rückfrage)",
    TaskState.TASK_STATE_AUTH_REQUIRED: "AUTH_REQUIRED (Anmeldung nötig)",
    TaskState.TASK_STATE_COMPLETED: "COMPLETED (erledigt)",
    TaskState.TASK_STATE_FAILED: "FAILED (fehlgeschlagen)",
    TaskState.TASK_STATE_REJECTED: "REJECTED (abgelehnt)",
    TaskState.TASK_STATE_CANCELED: "CANCELED (abgebrochen)",
}


def als_json(proto_objekt) -> str:
    """Wandelt ein A2A-Objekt in JSON um - so, wie es auch über die Leitung geht."""
    return json.dumps(MessageToDict(proto_objekt), indent=2, ensure_ascii=False)


class RemoteAgent:
    """Ein entfernter Agent, mit dem wir per A2A sprechen."""

    def __init__(self, base_url: str = LAGER_AGENT_URL, streaming: bool = False, kennung: str = ""):
        self.base_url = base_url
        self.kennung = kennung          # Kurzname aus agenten.json, z. B. "lager"
        self.streaming = streaming
        self.http = httpx.AsyncClient(timeout=60)
        self.card: AgentCard | None = None
        self.client = None

    # --- 1. Discovery ----------------------------------------------------------
    async def verbinden(self) -> AgentCard:
        """Lädt die Agent Card (GET /.well-known/agent-card.json) und baut den Client."""
        resolver = A2ACardResolver(httpx_client=self.http, base_url=self.base_url)
        self.card = await resolver.get_agent_card()
        self.client = await create_client(
            agent=self.card,
            client_config=ClientConfig(streaming=self.streaming, httpx_client=self.http),
        )
        return self.card

    def karte_beschreiben(self) -> str:
        """Kurzbeschreibung der Agent Card (z. B. für den System-Prompt eines LLM)."""
        c = self.card
        zeilen = [f"Agent \"{self.kennung}\": {c.name} - {c.description}", "Fähigkeiten (Skills):"]
        for s in c.skills:
            zeilen.append(f"  - {s.name} [{s.id}]: {s.description}")
            if s.examples:
                zeilen.append(f"    Beispiele: {'; '.join(s.examples)}")
        return "\n".join(zeilen)

    # --- 2. Auftrag senden -------------------------------------------------------
    async def senden(self, inhalt: str | dict, task_id: str = "", context_id: str = "",
                     bei_ereignis=None) -> Task:
        """
        Sendet eine Nachricht (SendMessage bzw. SendStreamingMessage).
        - inhalt: Text (-> text-Part) oder dict (-> data-Part)
        - task_id/context_id: gesetzt, wenn eine Rückfrage beantwortet wird
        - bei_ereignis: optionale Funktion, die jedes Streaming-Ereignis erhält
        Rückgabe: die Aufgabe (Task) im aktuellen Zustand
        """
        part = new_data_part(inhalt) if isinstance(inhalt, dict) else new_text_part(inhalt)
        nachricht = Message(
            role=Role.ROLE_USER,
            message_id=str(uuid.uuid4()),
            parts=[part],
            task_id=task_id,
            context_id=context_id,
        )
        task = None
        async for antwort in self.client.send_message(SendMessageRequest(message=nachricht)):
            if bei_ereignis:
                bei_ereignis(antwort)
            if antwort.HasField("task"):
                task = antwort.task
            elif antwort.HasField("message"):          # Agent antwortet ohne Task (direkte Antwort)
                return Task(history=[antwort.message])
            elif antwort.HasField("status_update") and task is not None:
                task.status.CopyFrom(antwort.status_update.status)
            elif antwort.HasField("artifact_update") and task is not None:
                task.artifacts.append(antwort.artifact_update.artifact)
        return task

    async def schliessen(self):
        if self.client:
            await self.client.close()
        await self.http.aclose()


# --- 3. Auswertung ----------------------------------------------------------------

def status_text(task: Task) -> str:
    """Text der Statusnachricht (z. B. die Rückfrage bei INPUT_REQUIRED)."""
    return " ".join(get_text_parts(task.status.message.parts))


def _ganzzahlen(wert):
    """Zahlen in data-Parts kommen als Kommazahl an (45.0) - für die Anzeige glätten."""
    if isinstance(wert, float) and wert.is_integer():
        return int(wert)
    if isinstance(wert, dict):
        return {k: _ganzzahlen(v) for k, v in wert.items()}
    if isinstance(wert, list):
        return [_ganzzahlen(v) for v in wert]
    return wert


def artefakte_text(task: Task) -> str:
    """Alle Artefakte als lesbarer Text inkl. strukturierter Daten."""
    zeilen = []
    for artefakt in task.artifacts:
        zeilen.append(f"Artefakt '{artefakt.name}':")
        for text in get_text_parts(artefakt.parts):
            zeilen.append(f"  Text:  {text}")
        for daten in get_data_parts(artefakt.parts):
            zeilen.append(f"  Daten: {json.dumps(_ganzzahlen(daten), ensure_ascii=False)}")
    return "\n".join(zeilen)


# --- 1b. Discovery für mehrere Fachagenten ---------------------------------------

async def agenten_laden(streaming: bool = False) -> dict[str, RemoteAgent]:
    """
    Liest agenten.json und lädt von jeder Basisadresse die Agent Card.
    Nicht erreichbare Agenten werden gemeldet und übersprungen.
    Rückgabe: {"lager": RemoteAgent, "bestellung": RemoteAgent, ...}
    """
    adressen = json.loads(AGENTEN_DATEI.read_text(encoding="utf-8"))
    agenten = {}
    for kennung, url in adressen.items():
        agent = RemoteAgent(url, streaming=streaming, kennung=kennung)
        try:
            await agent.verbinden()
            agenten[kennung] = agent
        except Exception:
            print(f" Hinweis: Fachagent '{kennung}' unter {url} nicht erreichbar, wird übersprungen.")
            await agent.schliessen()
    return agenten


async def alle_schliessen(agenten: dict[str, RemoteAgent]) -> None:
    for agent in agenten.values():
        await agent.schliessen()


# --- 4. Delegation: genau EINE Stelle, an der ein Agent einen anderen beauftragt ---------

async def an_agent_delegieren(agent: RemoteAgent, auftrag: str) -> str:
    """Schickt den Auftrag per A2A und begleitet die Aufgabe bis zu einem Endzustand."""
    name = agent.card.name
    print(f"\n[Orchestrator -> {name}] A2A-Auftrag: {auftrag}")
    task = await agent.senden(auftrag)
    print(f"[{name}] Zustand: {ZUSTAND[task.status.state]}")

    # Rückfrage? Dann antwortet der Mensch (Human in the loop), gleiche Task-ID
    while task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
        print(f"[{name}] Rückfrage: {status_text(task)}")
        antwort = input(f"Ihre Antwort an den {name}: ").strip()
        task = await agent.senden(antwort, task.id, task.context_id)
        print(f"[{name}] Zustand: {ZUSTAND[task.status.state]}")

    if task.status.state == TaskState.TASK_STATE_COMPLETED:
        ergebnis = artefakte_text(task)
    else:
        ergebnis = f"Aufgabe nicht erledigt ({ZUSTAND[task.status.state]}): {status_text(task)}"
    print(f"[{name}] Ergebnis:\n{ergebnis}")
    return ergebnis
