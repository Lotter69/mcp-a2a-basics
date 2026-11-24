#!/usr/bin/env python3
"""
A2A-Client ohne LLM: direkt mit den Fachagenten sprechen

Hier übernimmt der MENSCH die Rolle des Orchestrators: Er wählt selbst,
welcher Fachagent einen Auftrag bekommt. Der Client macht sichtbar, was im
A2A-Protokoll passiert:
  - Discovery: Er lädt beim Start die Agent Cards aller Fachagenten aus agenten.json.
  - Jede Eingabe wird als Nachricht (Message) an den gewählten Fachagenten gesendet.
  - Der Fachagent antwortet mit einer Aufgabe (Task) und ihrem Zustand.
  - Bei einer Rückfrage (INPUT_REQUIRED) gehört die nächste Eingabe zur selben Aufgabe.

Start:   python a2a_client.py                 SendMessage: eine Anfrage, EINE Antwort (Endzustand)
         python a2a_client.py --stream        SendStreamingMessage: Zwischenstände als einzelne Ereignisse
         python a2a_client.py --roh           zusätzlich das vollständige JSON jeder Antwort anzeigen
         python a2a_client.py --stream --roh  beides kombiniert

--stream ändert, WAS gesendet wird (andere A2A-Methode).
--roh    ändert nur, WIE VIEL angezeigt wird (das Protokoll bleibt gleich).
"""

import asyncio
import json
import sys

from a2a.client import A2AClientError, AgentCardResolutionError
from a2a.types import TaskState

from a2a_verbindung import (ZUSTAND, agenten_laden, alle_schliessen, als_json,
                            artefakte_text, status_text)

ROH = "--roh" in sys.argv
STREAM = "--stream" in sys.argv


def ereignis_anzeigen(antwort):
    """Wird beim Streaming für jedes einzelne Ereignis aufgerufen."""
    if antwort.HasField("task"):
        print(f"   [Ereignis] task          -> {ZUSTAND[antwort.task.status.state]}")
    elif antwort.HasField("status_update"):
        s = antwort.status_update.status
        print(f"   [Ereignis] statusUpdate  -> {ZUSTAND[s.state]}")
    elif antwort.HasField("artifact_update"):
        print(f"   [Ereignis] artifactUpdate -> '{antwort.artifact_update.artifact.name}'")
    if ROH:
        print(als_json(antwort))


async def main():
    agenten = await agenten_laden(streaming=STREAM)
    if not agenten:
        raise AgentCardResolutionError("Kein Fachagent aus agenten.json erreichbar.")

    print("A2A-Client (ohne LLM) gestartet - Sie sind der Orchestrator")
    print(f"Streaming: {'ja (SendStreamingMessage)' if STREAM else 'nein (SendMessage)'}"
          f"   Rohes JSON: {'ja' if ROH else 'nein'}")
    print(f"{len(agenten)} Fachagent(en) laut Agent Cards:")
    for kennung, agent in agenten.items():
        c = agent.card
        print(f"   [{kennung}] {c.name}  {c.supported_interfaces[0].url}")
        for s in c.skills:
            print(f"        Skill {s.id}: {s.description}")
    print("\nBefehle: 'agent <name>' wechselt den Fachagenten, 'karte' zeigt seine Agent Card,")
    print("         'neu' beginnt eine neue Aufgabe, 'exit' beendet.")
    print("Eingabe in { } wird als strukturierte Daten (data-Part) gesendet, z. B. {\"farbe\": \"rot\", \"menge\": 10}")
    print("=" * 60)

    aktuell = "lager" if "lager" in agenten else next(iter(agenten))
    task_id = context_id = ""          # leer = neue Aufgabe
    while True:
        prompt = "Antwort auf Rückfrage" if task_id else "Ihre Nachricht"
        eingabe = input(f"\n[{aktuell}] {prompt} (oder 'exit'): ").strip()
        if eingabe.lower() == "exit":
            break
        if eingabe.lower() == "neu":
            task_id = context_id = ""
            print("Neue Aufgabe - die bisherige wird nicht fortgesetzt.")
            continue
        if eingabe.lower().startswith("agent"):
            wahl = eingabe[5:].strip().lower()
            if wahl in agenten:
                aktuell, task_id, context_id = wahl, "", ""
                print(f"Aufträge gehen jetzt an: {agenten[aktuell].card.name}")
            else:
                print(f"Unbekannt. Verfügbar: {', '.join(agenten)}")
            continue
        if eingabe.lower() == "karte":
            print(als_json(agenten[aktuell].card))
            continue
        if not eingabe:
            continue

        inhalt = json.loads(eingabe) if eingabe.startswith("{") else eingabe
        task = await agenten[aktuell].senden(inhalt, task_id, context_id,
                                             bei_ereignis=ereignis_anzeigen if STREAM else None)

        if ROH and not STREAM:
            print(als_json(task))

        print(f"\nTask-ID:    {task.id}")
        print(f"Context-ID: {task.context_id}")
        print(f"Zustand:    {ZUSTAND.get(task.status.state, task.status.state)}")
        if status_text(task):
            print(f"Nachricht:  {status_text(task)}")
        if task.artifacts:
            print(artefakte_text(task))

        if task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
            task_id, context_id = task.id, task.context_id     # nächste Eingabe gehört zu diesem Task
        else:
            task_id = context_id = ""

    await alle_schliessen(agenten)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n Programm beendet.")
    except (AgentCardResolutionError, A2AClientError) as e:
        print(f"\n Fehler: Fachagent nicht erreichbar.\n ({e})")
        print("\n Stellen Sie sicher, dass:")
        print("  1. die Fachagenten in einem eigenen Fenster laufen:")
        print("     python fachagenten_starten.py   (alle drei)  oder  python lager_agent.py")
        print("  2. die Agent Card im Browser erreichbar ist, z. B.:")
        print("     http://127.0.0.1:9999/.well-known/agent-card.json")
