#!/usr/bin/env python3
"""
A2A-Client ohne LLM: direkt mit dem Lager-Agenten sprechen

Dieser Client macht sichtbar, was im A2A-Protokoll passiert:
  - Discovery: Er lädt zuerst die Agent Card des Lager-Agenten.
  - Jede Eingabe wird als Nachricht (Message) gesendet.
  - Der Lager-Agent antwortet mit einer Aufgabe (Task) und ihrem Zustand.
  - Bei einer Rückfrage (INPUT_REQUIRED) gehört die nächste Eingabe zur selben Aufgabe.

Start:   python a2a_client.py            (eine Anfrage, eine Antwort)
         python a2a_client.py --stream   (Zwischenstände als Ereignisse)
         python a2a_client.py --roh      (zusätzlich vollständiges JSON anzeigen)
"""

import asyncio
import json
import sys

from a2a.types import TaskState

from a2a_verbindung import ZUSTAND, RemoteAgent, als_json, artefakte_text, status_text

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
    agent = RemoteAgent(streaming=STREAM)
    card = await agent.verbinden()

    print("A2A-Client (ohne LLM) gestartet")
    print(f"Verbunden mit: {card.name} (Version {card.version})")
    print(f"Endpunkt:      {card.supported_interfaces[0].url}  "
          f"[{card.supported_interfaces[0].protocol_binding}, A2A {card.supported_interfaces[0].protocol_version}]")
    print(f"Streaming:     {'ja' if STREAM else 'nein'}")
    print(f"{len(card.skills)} Skill(s) laut Agent Card:")
    for s in card.skills:
        print(f"   - {s.id}: {s.description}")
    print("\nBefehle: 'exit' beendet, 'neu' beginnt eine neue Aufgabe, 'karte' zeigt die Agent Card")
    print("Eingabe in { } wird als strukturierte Daten (data-Part) gesendet, z. B. {\"farbe\": \"rot\", \"menge\": 10}")
    print("=" * 60)

    task_id = context_id = ""          # leer = neue Aufgabe
    while True:
        prompt = "Antwort auf Rückfrage" if task_id else "Ihre Nachricht an den Lager-Agenten"
        eingabe = input(f"\n{prompt} (oder 'exit'): ").strip()
        if eingabe.lower() == "exit":
            break
        if eingabe.lower() == "neu":
            task_id = context_id = ""
            print("Neue Aufgabe - die bisherige wird nicht fortgesetzt.")
            continue
        if eingabe.lower() == "karte":
            print(als_json(card))
            continue
        if not eingabe:
            continue

        inhalt = json.loads(eingabe) if eingabe.startswith("{") else eingabe
        task = await agent.senden(inhalt, task_id, context_id,
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

    await agent.schliessen()


if __name__ == "__main__":
    asyncio.run(main())
