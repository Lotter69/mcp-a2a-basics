# Laborübung 1: Analyse der A2A-Kommunikation mit Wireshark

> Gegenstück in Teil 1: [Analyse der LLM-Kommunikation mit Wireshark](04_client_llm.md)

![line](images/banner.png)

## Lernziele

Nach Abschluss dieser Laborübung können Sie:

- Den Netzwerkverkehr zwischen Orchestrator (A2A-Client) und Fachagenten (A2A-Server) auf dem Loopback-Interface mitschneiden
- Die drei Fachagenten im Mitschnitt an ihren **Ports** unterscheiden (Lager 9999, Bestellung 9998, Raumbuchung 9997)
- Die Discovery mehrerer Agent Cards (`GET /.well-known/agent-card.json`) und Aufträge (`POST /`, JSON-RPC) im Mitschnitt finden
- Den Aufbau einer A2A-Nachricht (Header `A2A-Version`, `method`, `message`, `parts`) im Klartext lesen
- Antwort mit Task, Zustand und Artefakt interpretieren, auch bei Rückfrage (`INPUT_REQUIRED`)
- Den Unterschied zwischen einer normalen Antwort und Streaming (Server-Sent Events) im Mitschnitt erkennen
- Im Mitschnitt erkennen, welchen Fachagenten das LLM des Orchestrators gewählt hat
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

### Wer läuft auf welchem Port?

| Programm | Rolle | Port | Protokoll |
|---|---|---|---|
| `lager_agent.py` | Fachagent (A2A-Server) | **9999** | A2A über HTTP |
| `bestell_agent.py` | Fachagent (A2A-Server) | **9998** | A2A über HTTP |
| `raum_agent.py` | Fachagent (A2A-Server) | **9997** | A2A über HTTP |
| Ollama | LLM-Server | **11434** | HTTP (Ollama-API) |
| `a2a_client.py`, `planungs_agent_ollama.py` | Orchestrator (A2A-Client) | zufälliger Port (vom Betriebssystem vergeben) | – |
| `mcp_server.py` | Werkzeug (MCP-Server) | **kein Port** | MCP über stdio |

### HTTP auf den Ports 9997 bis 9999 erkennen (einmalig)

Die Ports 9997 bis 9999 sind keine Standard-Ports für HTTP. Damit Wireshark in der Spalte **Protocol** `HTTP` statt nur `TCP` anzeigt, tragen Sie die Ports einmalig ein:

1. **Bearbeiten → Einstellungen** (Edit → Preferences)
2. Links **Protocols → HTTP**
3. Im Feld **TCP port(s)** am Ende ergänzen: `,9997-9999,11434`
4. **OK**

> **Alternative:** Nach der Aufzeichnung Rechtsklick auf ein Paket → **Decode As …** → Feld *Current* auf **HTTP** stellen. Diese Einstellung gilt nur für **einen** Port. Für jeden weiteren Port mit **+** eine Zeile hinzufügen und den Port in der Spalte *Value* eintragen. **Follow → TCP Stream** funktioniert auch ganz ohne diese Einstellung.

---

## Teil A: Discovery und ein einfacher Auftrag

### Schritt 1: Fachagenten starten

**Aktion (PowerShell-Fenster 1):**
```powershell
python fachagenten_starten.py
```

Warten Sie, bis alle drei Fachagenten ihre Adresse ausgegeben haben.

---

### Schritt 2: Wireshark starten und Loopback-Interface wählen

1. Wireshark über das Startmenü starten
2. Doppelklick auf **„Adapter for loopback traffic capture“**

Die Aufzeichnung läuft.

---

### Schritt 3: Client starten und einen Auftrag senden

**Aktion (PowerShell-Fenster 2):**
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
python a2a_client.py
```

**Eingabe** (geht an den Lager-Agenten, Prompt `[lager]`):
```
Haben wir 30 blaue Patchkabel?
```

Danach Client mit `exit` beenden.

---

### Schritt 4: Aufzeichnung stoppen und filtern

1. In Wireshark **Stopp** (rotes Quadrat)
2. Display-Filter eingeben und mit Enter bestätigen:
   ```
   tcp.port in {9997 9998 9999}
   ```
   (gleichwertig: `tcp.port == 9997 || tcp.port == 9998 || tcp.port == 9999`)

Mit dem Filter `http` sehen Sie danach nur noch die HTTP-Nachrichten.

---

### Schritt 5: Discovery-Anfragen finden

**Suchen Sie die Zeilen mit:**
- **Protocol:** HTTP
- **Info:** `GET /.well-known/agent-card.json HTTP/1.1`

**Sie finden drei solche Anfragen**, kurz hintereinander, bevor Sie überhaupt etwas eingegeben haben:

| Nr. | Ziel-Port | Fachagent | Antwort enthält Skill |
|---|---|---|---|
| 1 | 9999 | Lager-Agent | `bestand_pruefen` |
| 2 | 9998 | Bestell-Agent | `material_bestellen` |
| 3 | 9997 | Raumbuchungs-Agent | `laborraum_buchen` |

> **Tipp:** Blenden Sie die Spalten Quell- und Zielport ein (Rechtsklick auf den Spaltenkopf → **Column Preferences**, oder im Paketdetail bei *Transmission Control Protocol* → *Destination Port* → Rechtsklick → **Apply as Column**).

**Aktion:** Rechtsklick auf die erste GET-Zeile → **Follow → HTTP Stream** (oder TCP Stream)

**Sie sehen (Rot = Anfrage des Clients, Blau = Antwort des Lager-Agenten):**
```http
GET /.well-known/agent-card.json HTTP/1.1
Host: 127.0.0.1:9999
Accept: */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
User-Agent: python-httpx/0.28.1

HTTP/1.1 200 OK
server: uvicorn
content-length: 864
content-type: application/json

{"name":"Lager-Agent Netzwerklabor","description":"Verwaltet das Materiallager ...",
 "supportedInterfaces":[{"url":"http://127.0.0.1:9999","protocolBinding":"JSONRPC","protocolVersion":"1.0"}],
 "version":"1.0.0","capabilities":{"streaming":true}, ... "skills":[{"id":"bestand_pruefen", ...}]}
```

**Beobachten Sie:**
- Discovery ist eine ganz normale HTTP-GET-Anfrage. Es gibt keinen Handshake wie `initialize` bei MCP.
- Der Client kennt aus `agenten.json` nur die **Basis-URL** jedes Fachagenten. Die Adresse für Aufträge erfährt er erst hier (`supportedInterfaces[0].url`).
- Der Client lädt **alle drei** Agent Cards, obwohl Sie danach nur den Lager-Agenten beauftragen.

**Aufgabe:** Öffnen Sie **Statistiken → Konversationen** (Statistics → Conversations), Reiter **TCP**. Wie viele TCP-Verbindungen hat der Client aufgebaut, und zu welchen Ports?

**Erwartet:** drei Verbindungen, je eine zu Port 9999, 9998 und 9997. Jeder Fachagent ist ein eigener Server.

---

### Schritt 6: Den Auftrag finden (SendMessage)

Im selben Stream wie die erste Discovery-Anfrage (die Verbindung zu Port 9999 wird wiederverwendet, `Connection: keep-alive`) oder als nächste HTTP-Zeile in der Paketliste: **`POST / HTTP/1.1`** an Port **9999**

**HTTP-Anfrage:**
```http
POST / HTTP/1.1
Host: 127.0.0.1:9999
A2A-Version: 1.0
Content-Type: application/json

{"method":"SendMessage",
 "params":{"message":{"messageId":"63de593d-...","role":"ROLE_USER",
                      "parts":[{"text":"Haben wir 30 blaue Patchkabel?"}]},
           "configuration":{}},
 "id":"274c5947-...","jsonrpc":"2.0"}
```

**Beobachten Sie:**

| Element | Bedeutung |
|---|---|
| `POST /` an Port 9999 | Alle A2A-Aufträge an **diesen** Fachagenten gehen an dieselbe Adresse. Der Port bestimmt, welcher Fachagent beauftragt wird |
| Header `A2A-Version: 1.0` | Der Client nennt die Protokollversion. Ohne ihn lehnt der Server ab (siehe Laborübung 2) |
| `"jsonrpc": "2.0"`, `"id"` | JSON-RPC 2.0, wie bei MCP. Die `id` ordnet die Antwort der Anfrage zu |
| `"method": "SendMessage"` | Die gewünschte A2A-Operation |
| `"role": "ROLE_USER"` | Die Nachricht kommt vom Auftraggeber (die Rolle heißt auch bei einem Agenten als Auftraggeber `ROLE_USER`) |
| `"parts": [{"text": ...}]` | Der Inhalt, hier ein Text-Part |
| fehlende `taskId` | Neue Aufgabe |

**Aufgabe:** Gibt es `POST /`-Anfragen an Port 9998 oder 9997? (Erwartet: nein, dort gab es nur die Discovery.)

---

### Schritt 7: Die Antwort analysieren

**HTTP-Antwort (formatiert und gekürzt):**
```json
{
  "result": {
    "task": {
      "id": "de80b232-...",
      "contextId": "07b09a79-...",
      "status": {
        "state": "TASK_STATE_COMPLETED",
        "message": { "role": "ROLE_AGENT", "parts": [ { "text": "Bestandsprüfung abgeschlossen." } ] },
        "timestamp": "2026-11-24T14:51:41.123456Z"
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
  "id": "274c5947-...",
  "jsonrpc": "2.0"
}
```

**Beobachten Sie:**
- Das Ergebnis ist eine **Aufgabe** (`task`) mit ID, Zustand und Verlauf, keine einfache Textantwort.
- Das eigentliche Arbeitsergebnis steht in **`artifacts`**, getrennt vom Gesprächsverlauf in **`history`**.
- Wo ist der MCP-Aufruf `tools/call`, mit dem der Lager-Agent den Bestand abgefragt hat? Er taucht **nirgends** auf. Vergleichen Sie mit Fenster 1: Dort steht `[MCP]  tools/call patchkabel_bestand_abfragen {'farbe': 'blau'}`.

> **Hinweis:** Umlaute erscheinen im Stream-Fenster eventuell als `\u00fc` oder als zwei Sonderzeichen. Das ist nur die Darstellung. Übertragen wird UTF-8.

---

## Teil B: Rückfrage beim Bestell-Agenten und Streaming

### Schritt 8: Freigabe-Rückfrage mitschneiden

1. Wireshark: neue Aufzeichnung starten (grüne Haifischflosse, „Continue without saving“)
2. Fenster 2: `python a2a_client.py`
3. Eingaben nacheinander:
   ```
   agent bestellung
   Bestelle 100 grüne Patchkabel
   ja
   exit
   ```
4. Aufzeichnung stoppen, Filter setzen:
   ```
   tcp.port == 9998 && http
   ```

**Aufgabe:** Finden Sie die **zwei** `POST /`-Anfragen an den Bestell-Agenten.

- Welchen `state` hat die Antwort auf die erste Anfrage? Wie lautet der Text in `status.message`?
- Welche zwei zusätzlichen Felder enthält die `message` der zweiten Anfrage?
- Vergleichen Sie die `id` der beiden Tasks.
- In welcher Antwort steht ein `artifacts`-Eintrag, und wie heißt das Artefakt?

**Erwartet:**

| | Anfrage | Antwort |
|---|---|---|
| 1. `POST /` | `"parts":[{"text":"Bestelle 100 grüne Patchkabel"}]`, **ohne** `taskId` | `"state":"TASK_STATE_INPUT_REQUIRED"`, Text: „Die Bestellung über 100 gruene Patchkabel kostet 180.00 Euro. Bestellungen über 50 Euro brauchen eine Freigabe. Freigeben? (ja/nein)“ |
| 2. `POST /` | `"parts":[{"text":"ja"}]` **mit** `"taskId"` und `"contextId"` der ersten Antwort | `"state":"TASK_STATE_COMPLETED"`, Artefakt `bestellbestaetigung` mit Text- und data-Part |

**Beobachten Sie:**
- Beide Tasks haben **dieselbe** ID. Die Freigabe „ja“ gehört zur Bestellung, weil der Client die `taskId` mitschickt.
- Den Preis von 180 Euro hat der Bestell-Agent mit seinem MCP-Tool `patchkabel_katalog_abfragen` ermittelt. Im Mitschnitt sehen Sie nur das Ergebnis seiner Regel („über 50 Euro brauchen eine Freigabe“), nicht den Werkzeugaufruf.

> **Variante:** Antworten Sie statt `ja` mit `nein`. Welchen Zustand hat dann die zweite Antwort? (Erwartet: `TASK_STATE_CANCELED`, kein Artefakt.)

---

### Schritt 9: Streaming mitschneiden

1. Neue Aufzeichnung starten
2. Fenster 2: `python a2a_client.py --stream`
3. Eingabe: `Haben wir 60 blaue Patchkabel?`, dann `exit`
4. Aufzeichnung stoppen, Filter `tcp.port == 9999 && http`, **Follow → HTTP Stream** auf den `POST /`

> **Zur Erinnerung:** `--stream` ändert, **was** gesendet wird (andere A2A-Methode). `--roh` ändert nur, **wie viel** der Client anzeigt, und ist im Mitschnitt nicht zu erkennen.

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

## Teil C: Orchestrator mit LLM und drei Fachagenten

### Schritt 10: Den Orchestrator mitschneiden

1. Neue Aufzeichnung starten
2. Fenster 2: `python planungs_agent_ollama.py`
3. Erste Eingabe: `Im Kurs sind 12 Teilnehmende, jede Person braucht 2 blaue Patchkabel. Reicht unser Bestand?`
4. Zweite Eingabe: `Der Lieferant soll uns 20 schwarze Kabel schicken.`
5. Nach der Antwort `exit`, Aufzeichnung stoppen
6. Display-Filter:
   ```
   tcp.port in {9997 9998 9999 11434} && http
   ```

**Aufgabe:** Ordnen Sie die HTTP-Anfragen in zeitlicher Reihenfolge:

| Nr. | Anfrage | Von → An (Port) | Inhalt |
|---|---|---|---|
| 1 | `GET /.well-known/agent-card.json` | Orchestrator → Lager-Agent (9999) | Discovery |
| 2 | `GET /.well-known/agent-card.json` | Orchestrator → Bestell-Agent (9998) | Discovery |
| 3 | `GET /.well-known/agent-card.json` | Orchestrator → Raumbuchungs-Agent (9997) | Discovery |
| 4 | `POST /api/chat` | Orchestrator → Ollama (11434) | Frage + Beschreibung **aller drei** Fachagenten im System-Prompt |
| 5 | `POST /` | Orchestrator → Lager-Agent (**9999**) | A2A `SendMessage` mit dem Auftrag des LLM |
| 6 | `POST /api/chat` | Orchestrator → Ollama (11434) | Verlauf + Ergebnis des Fachagenten |
| 7 | `POST /api/chat` | Orchestrator → Ollama (11434) | zweite Frage |
| 8 | `POST /` | Orchestrator → Bestell-Agent (**9998**) | A2A `SendMessage` mit dem Auftrag des LLM |
| 9 | `POST /api/chat` | Orchestrator → Ollama (11434) | Verlauf + Bestellbestätigung |

Wählt das LLM einen anderen Fachagenten oder delegiert es gar nicht, weicht Ihr Mitschnitt ab. Genau das ist dann ein guter Anlass für die Diskussion.

**Beobachten Sie in Anfrage 4:** Der System-Prompt enthält unter „Verfügbare Agenten (laut Agent Cards)“ Name, Beschreibung, Skills und Beispiele aller drei Fachagenten, also Inhalte der **Agent Cards**. Das LLM kennt die Fachagenten nur über diese Beschreibungen.

**Beobachten Sie in der Antwort auf Anfrage 4:** Das LLM antwortet mit `{"agent": "lager", "auftrag": "..."}`. Die **Auswahl** des Fachagenten steht hier im Klartext.

**Beobachten Sie in Anfrage 5 und 8:** Die Auswahl des LLM wird im Netz zum **Ziel-Port**. Der Text im A2A-Auftrag stammt vom LLM (z. B. „Haben wir 24 blaue Patchkabel?“), nicht vom Benutzer.

---

## Schritt 11: Reflexion und weitere Experimente

- Warum sehen Sie den A2A-Verkehr in Wireshark, den MCP-Verkehr zwischen den Fachagenten und `mcp_server.py` aber nicht?

- Woran erkennen Sie im Mitschnitt, welchen Fachagenten das LLM gewählt hat? (Zwei Stellen: Antwort von Ollama und Ziel-Port des `POST /`.)

- Welche Informationen erhält das LLM über die Fachagenten? Welche nicht?

- Welche Informationen erhält der Bestell-Agent über den Kurs? Welche nicht?

- Was müsste sich ändern, wenn die Fachagenten auf einem anderen Rechner im Schulnetz laufen? Was würde dann ein Mitschnitt im Netz zeigen, und was folgt daraus für die Freigabe von Bestellungen?

- Woran erkennt der Bestell-Agent, dass „ja“ die Antwort auf seine Rückfrage ist?

---

**Zusätzliche Experimente:**

1. **Strukturierte Daten:** Senden Sie im Client `{"farbe": "rot", "menge": 40}` an den Lager-Agenten und vergleichen Sie den `parts`-Eintrag der Anfrage mit einem Text-Auftrag.
2. **Ablehnung:** Senden Sie `10 grüne Patchkabel` an den Lager-Agenten und `Bestelle 200 rote Patchkabel` an den Bestell-Agenten. Suchen Sie jeweils den Zustand in der Antwort. Erscheint ein `artifacts`-Eintrag?
3. **Gegenvorschlag:** Senden Sie `agent raum` und `Reserviere Raum 104 für Donnerstag`. Finden Sie die Rückfrage im Mitschnitt (Port 9997).
4. **Frage ohne Fachagent** im Orchestrator (`Was ist ein Patchkabel?`): Wie viele `POST /`-Anfragen an die Ports 9997 bis 9999 entstehen?
5. **Ein Fachagent fehlt:** Starten Sie nur `python lager_agent.py` und dann den Client. Wie viele Discovery-Anfragen sehen Sie, und was antwortet das Betriebssystem auf die Verbindungsversuche zu 9998 und 9997? (Tipp: Filter `tcp.flags.reset == 1`)

---

**Weiter mit Laborübung 2: A2A-Protokoll von Hand!** →

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.1 (drei Fachagenten, Ports 9997 bis 9999)

![line](images/banner.png)
<p align="center">
<a href="08_a2a_architecture.md"><img src="images/previous.png" width="150px"></a>
<a href="10_a2a_protokoll.md"><img src="images/next.png" width="150px"></a>
</p>
