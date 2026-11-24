# Laborübung 1: Analyse der A2A-Kommunikation mit Wireshark

> Gegenstück in Teil 1: [Analyse der LLM-Kommunikation mit Wireshark](04_client_llm.md)

![line](images/banner.png)

## Lernziele

Nach Abschluss dieser Laborübung können Sie:

- Den Netzwerkverkehr zwischen zwei Agenten auf dem Loopback-Interface mitschneiden
- Discovery (`GET /.well-known/agent-card.json`) und Aufträge (`POST /`, JSON-RPC) im Mitschnitt finden
- Den Aufbau einer A2A-Nachricht (Header `A2A-Version`, `method`, `message`, `parts`) im Klartext lesen
- Antwort mit Task, Zustand und Artefakt interpretieren
- Den Unterschied zwischen einer normalen Antwort und Streaming (Server-Sent Events) im Mitschnitt erkennen
- Erklären, warum A2A-Verkehr in Wireshark sichtbar ist, MCP-Verkehr über stdio aber nicht

---

## Voraussetzungen

### Software
- Wireshark mit **Npcap** und der Option **„Support loopback traffic“**
- Python-venv mit den Bibliotheken aus `requirements.txt` [siehe Hinführung zu A2A](06_a2a_lab.md)
- Für Teil C: Ollama mit `qwen2.5-coder:3b`

### Vorbereitung
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
pip show a2a-sdk     # Version 1.3.x
```

---

## Teil A: Discovery und ein einfacher Auftrag

### Schritt 1: Wireshark starten und Loopback-Interface wählen

1. Wireshark über das Startmenü starten
2. Doppelklick auf **„Adapter for loopback traffic capture“**

Die Aufzeichnung läuft.

---

### Schritt 2: Lager-Agent starten

**Aktion (PowerShell-Fenster 1):**
```powershell
python lager_agent.py
```

---

### Schritt 3: Client starten und einen Auftrag senden

**Aktion (PowerShell-Fenster 2):**
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
python a2a_client.py
```

**Eingabe:**
```
Haben wir 30 blaue Patchkabel?
```

Danach Client mit `exit` beenden.

---

### Schritt 4: Aufzeichnung stoppen und filtern

1. In Wireshark **Stopp** (rotes Quadrat)
2. Display-Filter eingeben und mit Enter bestätigen:
   ```
   tcp.port == 9999
   ```

> **Hinweis:** Port 9999 ist kein Standard-Port für HTTP. Zeigt Wireshark in der Spalte **Protocol** nur `TCP` statt `HTTP`, dann: Rechtsklick auf ein Paket → **Decode As …** → Feld *Current* auf **HTTP** stellen → **OK**. Alternativ funktioniert **Follow → TCP Stream** auch ohne diese Einstellung.

Mit dem Filter `http` sehen Sie danach nur noch die HTTP-Nachrichten.

---

### Schritt 5: Discovery-Anfrage finden

**Suchen Sie die Zeile mit:**
- **Protocol:** HTTP
- **Info:** `GET /.well-known/agent-card.json HTTP/1.1`

**Aktion:** Rechtsklick → **Follow → HTTP Stream** (oder TCP Stream)

**Sie sehen (Rot = Anfrage des Clients, Blau = Antwort des Lager-Agenten):**
```http
GET /.well-known/agent-card.json HTTP/1.1
Host: 127.0.0.1:9999
Accept: */*
User-Agent: python-httpx/0.28.1

HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"name":"Lager-Agent Netzwerklabor","description":"Verwaltet das Materiallager ...",
 "supportedInterfaces":[{"url":"http://127.0.0.1:9999","protocolBinding":"JSONRPC","protocolVersion":"1.0"}],
 "version":"1.0.0","capabilities":{"streaming":true}, ... "skills":[{"id":"bestand_pruefen", ...}]}
```

**Beobachten Sie:**
- Discovery ist eine ganz normale HTTP-GET-Anfrage. Es gibt keinen Handshake wie `initialize` bei MCP.
- Der Client erfährt hier die Adresse für seine Aufträge (`supportedInterfaces[0].url`).

---

### Schritt 6: Den Auftrag finden (SendMessage)

Im selben Stream (die Verbindung wird wiederverwendet) oder als nächste HTTP-Zeile in der Paketliste: **`POST / HTTP/1.1`**

**HTTP-Anfrage:**
```http
POST / HTTP/1.1
Host: 127.0.0.1:9999
A2A-Version: 1.0
Content-Type: application/json

{"method":"SendMessage",
 "params":{"message":{"messageId":"4d1f4189-...","role":"ROLE_USER",
                      "parts":[{"text":"Haben wir 30 blaue Patchkabel?"}]},
           "configuration":{}},
 "id":"7b347477-...","jsonrpc":"2.0"}
```

**Beobachten Sie:**

| Element | Bedeutung |
|---|---|
| `POST /` | Alle A2A-Aufträge gehen an dieselbe Adresse |
| Header `A2A-Version: 1.0` | Der Client nennt die Protokollversion. Ohne ihn lehnt der Server ab (siehe Laborübung 2) |
| `"jsonrpc": "2.0"`, `"id"` | JSON-RPC 2.0, wie bei MCP. Die `id` ordnet die Antwort der Anfrage zu |
| `"method": "SendMessage"` | Die gewünschte A2A-Operation |
| `"role": "ROLE_USER"` | Die Nachricht kommt vom Auftraggeber (die Rolle heißt auch bei einem Agenten als Auftraggeber `ROLE_USER`) |
| `"parts": [{"text": ...}]` | Der Inhalt, hier ein Text-Part |
| fehlende `taskId` | Neue Aufgabe |

---

### Schritt 7: Die Antwort analysieren

**HTTP-Antwort (formatiert und gekürzt):**
```json
{
  "result": {
    "task": {
      "id": "d1b8e91d-...",
      "contextId": "9b59f8fa-...",
      "status": {
        "state": "TASK_STATE_COMPLETED",
        "message": { "role": "ROLE_AGENT", "parts": [ { "text": "Bestandsprüfung abgeschlossen." } ] },
        "timestamp": "2026-11-24T09:24:46.359552Z"
      },
      "artifacts": [
        {
          "artifactId": "301b640b-...",
          "name": "bestandsauskunft",
          "parts": [
            { "text": "30 Stück angefragt, 45 Stück auf Lager: ausreichend.", "mediaType": "text/plain" },
            { "data": { "farbe": "blau", "bestand": 45.0, "angefragt": 30.0, "ausreichend": true,
                        "fehlmenge": 0.0, "laenge_m": 1.0 }, "mediaType": "application/json" }
          ]
        }
      ],
      "history": [
        { "role": "ROLE_USER",  "parts": [ { "text": "Haben wir 30 blaue Patchkabel?" } ] },
        { "role": "ROLE_AGENT", "parts": [ { "text": "Lager-Agent prüft die Anfrage ..." } ] }
      ]
    }
  },
  "id": "7b347477-...",
  "jsonrpc": "2.0"
}
```

**Beobachten Sie:**
- Das Ergebnis ist eine **Aufgabe** (`task`) mit ID, Zustand und Verlauf, keine einfache Textantwort.
- Das eigentliche Arbeitsergebnis steht in **`artifacts`**, getrennt vom Gesprächsverlauf in **`history`**.
- Wo ist der MCP-Aufruf `tools/call`? Er taucht **nirgends** auf.

> **Hinweis:** Umlaute erscheinen im Stream-Fenster eventuell als `\u00fc` oder als zwei Sonderzeichen. Das ist nur die Darstellung. Übertragen wird UTF-8.

---

## Teil B: Rückfrage und Streaming

### Schritt 8: Neue Aufzeichnung mit Rückfrage

1. Wireshark: neue Aufzeichnung starten (grüne Haifischflosse, „Continue without saving“)
2. Fenster 2: `python a2a_client.py`
3. Eingaben nacheinander: `Ich brauche 50 Patchkabel`, dann `rot`, dann `exit`
4. Aufzeichnung stoppen, Filter `http` setzen

**Aufgabe:** Finden Sie die **zwei** `POST /`-Anfragen.

- Welchen `state` hat die Antwort auf die erste Anfrage?
- Welche zwei zusätzlichen Felder enthält die `message` der zweiten Anfrage?
- Vergleichen Sie die `id` der beiden Tasks.

**Erwartet:** erste Antwort `TASK_STATE_INPUT_REQUIRED`, zweite Anfrage mit `taskId` und `contextId`, beide Tasks mit derselben ID.

---

### Schritt 9: Streaming mitschneiden

1. Neue Aufzeichnung starten
2. Fenster 2: `python a2a_client.py --stream`
3. Eingabe: `Haben wir 60 blaue Patchkabel?`, dann `exit`
4. Aufzeichnung stoppen, **Follow → HTTP Stream** auf den `POST /`

**HTTP-Anfrage:** wie vorher, aber `"method": "SendStreamingMessage"`

**HTTP-Antwort:**
```http
HTTP/1.1 200 OK
content-type: text/event-stream; charset=utf-8
Transfer-Encoding: chunked

data: {"result": {"task": {"id": "3dc7...", "status": {"state": "TASK_STATE_SUBMITTED"}, ...}}, "id": ..., "jsonrpc": "2.0"}

data: {"result": {"statusUpdate": {"taskId": "3dc7...", "status": {"state": "TASK_STATE_WORKING", ...}}}, ...}

data: {"result": {"artifactUpdate": {"taskId": "3dc7...", "artifact": {"name": "bestandsauskunft", ...}}}, ...}

data: {"result": {"statusUpdate": {"taskId": "3dc7...", "status": {"state": "TASK_STATE_COMPLETED", ...}}}, ...}
```

**Beobachten Sie:**
- `content-type: text/event-stream`: Die Antwort ist ein **Ereignisstrom** (Server-Sent Events). Die Verbindung bleibt offen, bis der Task einen Endzustand erreicht.
- Jede Zeile `data:` ist ein vollständiges JSON-RPC-Ergebnis mit **einem** Ereignis: zuerst der Task, dann Zustandswechsel (`statusUpdate`) und Ergebnisse (`artifactUpdate`).
- In der Paketliste liegen die einzelnen Ereignisse zeitlich auseinander (der Lager-Agent wartet absichtlich eine Sekunde im Zustand WORKING).

---

## Teil C: Zwei Agenten und ein LLM

### Schritt 10: Den Planungs-Agenten mitschneiden

1. Neue Aufzeichnung starten
2. Fenster 2: `python planungs_agent_ollama.py`
3. Eingabe: `Im Kurs sind 12 Teilnehmende, jede Person braucht 2 blaue Patchkabel. Reicht unser Bestand?`
4. Nach der Antwort `exit`, Aufzeichnung stoppen
5. Display-Filter:
   ```
   tcp.port == 9999 || tcp.port == 11434
   ```
   (Port 11434 gegebenenfalls ebenfalls per **Decode As …** als HTTP dekodieren)

**Aufgabe:** Ordnen Sie die HTTP-Anfragen in zeitlicher Reihenfolge:

| Nr. | Anfrage | Von → An | Inhalt |
|---|---|---|---|
| 1 | `GET /.well-known/agent-card.json` | Planungs-Agent → Lager-Agent | Discovery |
| 2 | `POST /api/chat` | Planungs-Agent → Ollama | Frage + Beschreibung des Lager-Agenten im System-Prompt |
| 3 | `POST /` | Planungs-Agent → Lager-Agent | A2A `SendMessage` mit dem Auftrag des LLM |
| 4 | `POST /api/chat` | Planungs-Agent → Ollama | Verlauf + Ergebnis des Lager-Agenten |

**Beobachten Sie in Anfrage 2:** Der System-Prompt enthält Name, Beschreibung und Skills des Lager-Agenten, also Inhalte der **Agent Card**. Das LLM kennt den Lager-Agenten nur über diese Beschreibung.

**Beobachten Sie in Anfrage 3:** Der Text im A2A-Auftrag stammt vom LLM (z. B. „Haben wir 24 blaue Patchkabel?“), nicht vom Benutzer.

---

## Schritt 11: Reflexion und weitere Experimente

- Warum sehen Sie den A2A-Verkehr in Wireshark, den MCP-Verkehr zwischen Lager-Agent und `mcp_server.py` aber nicht?

- Welche Informationen erhält das LLM über den Lager-Agenten? Welche nicht?

- Welche Informationen erhält der Lager-Agent über den Kurs? Welche nicht?

- Was müsste sich ändern, wenn der Lager-Agent auf einem anderen Rechner im Schulnetz läuft? Was würde dann ein Mitschnitt im Netz zeigen?

- Was wäre der Unterschied im Mitschnitt, wenn Sie `planungs_agent.py` (Claude) statt Ollama benutzen?

- Woran erkennt der Lager-Agent, dass „rot“ die Antwort auf seine Rückfrage ist?

---

**Zusätzliche Experimente:**

1. **Strukturierte Daten:** Senden Sie im Client `{"farbe": "rot", "menge": 40}` und vergleichen Sie den `parts`-Eintrag der Anfrage mit einem Text-Auftrag.
2. **Ablehnung:** Senden Sie `10 grüne Patchkabel` und suchen Sie den Zustand in der Antwort. Erscheint ein `artifacts`-Eintrag?
3. **Frage ohne Lagerbezug** im Planungs-Agenten: Wie viele `POST /`-Anfragen an Port 9999 entstehen?

---

**Weiter mit Laborübung 2: A2A-Protokoll von Hand!** →

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.0

![line](images/banner.png)
<p align="center">
<a href="08_a2a_architecture.md"><img src="images/previous.png" width="150px"></a>
<a href="10_a2a_protokoll.md"><img src="images/next.png" width="150px"></a>
</p>
