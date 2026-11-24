# Hinführung zu A2A (Agent2Agent-Protokoll)

![line](images/banner.png)

## Einführung
In der Reihe [*MCP-Basics*](01_lab.md) hat ein LLM über das Model Context Protocol ein **Werkzeug** benutzt: Der MCP-Client hat dem LLM das Tool `patchkabel_bestand_abfragen` angeboten, das LLM hat entschieden, es aufzurufen, und der MCP-Server hat die Funktion ausgeführt. Der aufrufende Agent bestimmt dabei, **was** passiert: welches Tool, mit welchen Parametern.

Sobald mehrere Agenten zusammenarbeiten, ändert sich die Frage. Ein Agent soll eine Aufgabe nicht selbst erledigen, sondern an einen **anderen Agenten** abgeben, der eigene Daten, eigene Werkzeuge und eigene Regeln hat und oft von jemand anderem betrieben wird. Der beauftragende Agent will dann nicht mehr bestimmen, *wie* die Aufgabe gelöst wird. Er will einen Auftrag erteilen, Rückfragen beantworten und am Ende ein Ergebnis bekommen.

Dafür gibt es das **Agent2Agent-Protokoll (A2A)**. Es wurde von Google gestartet, liegt heute bei der Linux Foundation und ist seit Version 1.0 stabil. Merksatz für diese Reihe:

> **MCP verbindet einen Agenten mit seinen Werkzeugen. A2A verbindet einen Agenten mit einem Kollegen.**

## Lernziele

- Den Unterschied zwischen einem Werkzeug (MCP) und einem Kollegen-Agenten (A2A) an einem Beispiel erklären
- Einen A2A-Server (Agent) starten und seine **Agent Card** über die Discovery-Adresse `/.well-known/agent-card.json` abrufen
- Aufträge an einen Agenten senden und den **Lebenslauf einer Aufgabe (Task)** beobachten: eingereicht, in Arbeit, Rückfrage, erledigt, abgelehnt
- **Messages, Parts und Artifacts** unterscheiden
- Ein LLM-gestütztes Agentensystem nachvollziehen, in dem ein Agent per A2A delegiert und der andere Agent intern sein MCP-Tool nutzt
- Kommunikationsvorgänge (Benutzer, LLM, A2A, MCP) ordnen und trennen

## Szenario
Sie bereiten weiterhin den Netzwerktechnikkurs vor. Inzwischen gibt es im Labor zwei getrennte Zuständigkeiten:

- Der **Lager-Agent** gehört zur Materialverwaltung. Er kennt den Lagerbestand und benutzt dafür das MCP-Tool aus *MCP-Basics*. Wie er intern arbeitet, ist seine Sache.
- Der **Laborplanungs-Agent** unterstützt Sie bei der Kursplanung. Er rechnet aus, wie viel Material ein Kurs braucht, hat aber **keinen** Zugriff auf das Lager. Für Bestandsfragen beauftragt er den Lager-Agenten über A2A.

Der vereinfachte Lagerbestand umfasst weiterhin blaue und rote Patchkabel mit einer Länge von jeweils 1 m.

```
 Benutzer ──> Laborplanungs-Agent ══A2A══> Lager-Agent ──MCP──> Tool patchkabel_bestand_abfragen
               (LLM: plant, rechnet)        (eigene Logik)        (Python-Funktion, Lagerdaten)
```

## Voraussetzungen

- Python 3.11 oder höher
- Abgeschlossener Teil 1 [*MCP-Basics*](01_lab.md) (empfohlen, nicht zwingend)
- Für Lab 03: Ollama 0.13.3 oder höher mit z. B. `qwen2.5-coder:3b` **oder** Anthropic API Key
- Für die Laborübungen: Wireshark mit Npcap (Loopback), PowerShell, `curl.exe` (in Windows 10/11 enthalten)

## Vorbereitende Aufgaben

### Schritt 1: Python Installation überprüfen

```powershell
python --version
```

**Erwartete Ausgabe:** `Python 3.11.x` oder höher

---

### Schritt 2: Projektordner erstellen

```powershell
mkdir C:\akademietag_2026\a2a_basics\a2a-demo
cd C:\akademietag_2026\a2a_basics\a2a-demo
```

> **Hinweis:** Auf den bereitgestellten Notebooks ist dieser Ordner bereits vorhanden und befüllt.

Kopieren Sie die Dateien in den Ordner [siehe code in diesem Kapitel:](code_a2a/)

| Datei | Rolle |
|---|---|
| `mcp_server.py` | MCP-Server mit dem Tool `patchkabel_bestand_abfragen` (unverändert aus [`code/`](code/), Teil 1) |
| `lager_agent.py` | **A2A-Server**: der Lager-Agent (nutzt intern `mcp_server.py`) |
| `a2a_verbindung.py` | Hilfsschicht für A2A-Clients (Discovery, Senden, Auswerten, Delegieren) |
| `a2a_client.py` | **A2A-Client ohne LLM**: direkt mit dem Lager-Agenten sprechen |
| `planungs_agent_ollama.py` | **Laborplanungs-Agent** mit Ollama |
| `planungs_agent.py` | **Laborplanungs-Agent** mit Anthropic (optional) |
| `anfragen\*.json` | Rohe JSON-RPC-Anfragen für Laborübung 2 |
| `requirements.txt` | Bibliotheken mit Versionsbereichen (wie in *MCP-Basics*) |
| `.env.example` | Vorlage für den Anthropic-Schlüssel (optional) |

> **Wichtig:** Ein Ordner für alles. Anders als in *MCP-Basics* gibt es keinen getrennten Ordner je API-Provider, weil nur der Planungs-Agent ein LLM benutzt.

---

### Schritt 3: Virtuelle Umgebung erstellen und aktivieren

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Erfolg:** Ihr Prompt beginnt mit `(venv)`.

> **Tipp:** Verweigert PowerShell das Skript, hilft einmalig `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

### Schritt 4: Bibliotheken installieren

```powershell
pip install -r requirements.txt
pip show a2a-sdk
```

**Erwartet:** `a2a-sdk` in Version **1.3.x** (setzt die A2A-Spezifikation **1.0** um) und `mcp` in Version **2.x**.

> **Wichtig:** Viele Tutorials im Netz beziehen sich noch auf A2A 0.3 (Methoden wie `message/send`, Felder wie `"kind": "text"`). Diese Schreibweise funktioniert mit dem Code dieser Reihe nicht. Achten Sie bei eigenen Recherchen auf die Version.

---

### Schritt 5 (nur Anthropic): .env Datei anlegen

```powershell
notepad .env
```

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Ollama prüfen Sie wie in [*MCP-Basics*, Schritt 3b](01_lab.md) mit `ollama list` (Modell `qwen2.5-coder:3b` muss vorhanden sein).

---

# Lab 01: Den Lager-Agenten starten und seine Visitenkarte lesen

Ein A2A-Agent ist ein **Webserver**. Er läuft dauerhaft und wartet auf Aufträge, anders als der MCP-Server aus *MCP-Basics*, den der Client bei Bedarf als Unterprozess gestartet hat.

### Schritt 1: Lager-Agent starten

**Aktion (PowerShell-Fenster 1, venv aktiv):**
```powershell
python lager_agent.py
```

**Erwartete Ausgabe:**
```
Lager-Agent Netzwerklabor (A2A-Server)
Agent Card: http://127.0.0.1:9999/.well-known/agent-card.json
JSON-RPC:   http://127.0.0.1:9999/
Beenden mit Strg+C
```

> **Wichtig:** Lassen Sie dieses Fenster während aller Labs geöffnet. Hier protokolliert der Lager-Agent, was **intern** passiert, auch seine MCP-Aufrufe. Davon bekommt der anfragende Agent nichts mit.

### Schritt 2: Agent Card im Browser öffnen (Discovery)

Öffnen Sie im Browser:

```
http://127.0.0.1:9999/.well-known/agent-card.json
```

**Sie sehen (gekürzt):**
```json
{
  "name": "Lager-Agent Netzwerklabor",
  "description": "Verwaltet das Materiallager des Netzwerklabors und beantwortet Bestandsanfragen.",
  "supportedInterfaces": [
    { "url": "http://127.0.0.1:9999", "protocolBinding": "JSONRPC", "protocolVersion": "1.0" }
  ],
  "version": "1.0.0",
  "capabilities": { "streaming": true },
  "skills": [
    {
      "id": "bestand_pruefen",
      "name": "Patchkabel-Bestand prüfen",
      "description": "Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager vorhanden ist, ...",
      "examples": ["Haben wir 30 blaue Patchkabel?", "..."]
    }
  ]
}
```

**Beobachten Sie:**
- Die Agent Card ist die **Visitenkarte** des Agenten. Jeder, der die Adresse kennt, kann sie lesen. Das nennt man **Discovery**.
- Die Adresse `/.well-known/agent-card.json` ist im Standard festgelegt. Ein Client muss also nur den Server kennen, um herauszufinden, was der Agent kann und wie man mit ihm spricht.
- Die Karte beschreibt **was** der Agent kann (Skills), nicht **wie**. Vom MCP-Tool, das der Lager-Agent intern benutzt, steht hier nichts.

> **Vergleich mit MCP:** Dort lieferte `tools/list` ein genaues `inputSchema` mit Parametern und erlaubten Werten. Eine Agent Card enthält kein solches Schema. Ein Kollege bekommt einen Auftrag in natürlicher Sprache oder als Daten, kein Formular.

---

# Lab 02: Mit dem Lager-Agenten direkt sprechen (ohne LLM)

Zuerst lassen wir das LLM weg. So sehen Sie das Protokoll ohne Ablenkung.

**Aktion (PowerShell-Fenster 2, venv aktiv):**
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
python a2a_client.py
```

**Erwartete Ausgabe:**
```
A2A-Client (ohne LLM) gestartet
Verbunden mit: Lager-Agent Netzwerklabor (Version 1.0.0)
Endpunkt:      http://127.0.0.1:9999  [JSONRPC, A2A 1.0]
Streaming:     nein
1 Skill(s) laut Agent Card:
   - bestand_pruefen: Prüft, ob eine gewünschte Anzahl Patchkabel ...
```

Der Client hat die Agent Card geladen, bevor Sie irgendetwas eingegeben haben.

### Aufgabe 2.1: Ein einfacher Auftrag

**Eingabe:** `Haben wir 30 blaue Patchkabel?`

```
Task-ID:    3cba4ffe-...
Context-ID: cdc3c707-...
Zustand:    COMPLETED (erledigt)
Nachricht:  Bestandsprüfung abgeschlossen.
Artefakt 'bestandsauskunft':
  Text:  30 Stück angefragt, 45 Stück auf Lager: ausreichend.
  Daten: {"angefragt": 30, "farbe": "blau", "laenge_m": 1, "bestand": 45, "ausreichend": true, "fehlmenge": 0}
```

Sehen Sie gleichzeitig in **Fenster 1** nach: Dort steht, dass der Lager-Agent einen Task angelegt, die Nachricht verstanden und das MCP-Tool aufgerufen hat.

**Beobachten Sie:**
- Aus Ihrer Nachricht wurde eine **Aufgabe (Task)** mit eigener ID und einem **Zustand**.
- Das Ergebnis kommt als **Artefakt** mit zwei Teilen (**Parts**): einem Text für Menschen und strukturierten Daten für Programme.

### Aufgabe 2.2: Rückfrage (INPUT_REQUIRED)

**Eingabe:** `Ich brauche 50 Patchkabel`

```
Zustand:    INPUT_REQUIRED (Rückfrage)
Nachricht:  Welche Farbe wird benötigt? Im Sortiment sind blau und rot (oder 'gesamt').
```

Der Prompt wechselt auf **„Antwort auf Rückfrage“**. **Eingabe:** `rot`

```
Zustand:    COMPLETED (erledigt)
Artefakt 'bestandsauskunft':
  Text:  50 Stück angefragt, 32 Stück auf Lager: es fehlen 18 Stück.
```

**Beobachten Sie:** Die Task-ID ist bei beiden Antworten **dieselbe**. Die Antwort „rot“ allein wäre unverständlich. Erst weil der Client die Task-ID mitschickt, weiß der Lager-Agent, dass „rot“ zur Anfrage über 50 Kabel gehört.

### Aufgabe 2.3: Ablehnung (REJECTED)

**Eingabe:** `10 grüne Patchkabel`

**Erwartet:** `REJECTED (abgelehnt)` mit der Begründung, dass grüne Kabel nicht im Sortiment sind. Der Lager-Agent ruft sein Tool gar nicht erst auf (siehe Fenster 1).

### Aufgabe 2.4: Strukturierte Daten statt Text

**Eingabe:** `{"farbe": "rot", "menge": 40}`

Der Client schickt die Eingabe jetzt als **data-Part** statt als Text-Part. Das Ergebnis ist dasselbe, aber der Lager-Agent muss nichts mehr „verstehen“, weil die Angaben bereits strukturiert sind.

### Aufgabe 2.5: Streaming

Beenden Sie den Client mit `exit` und starten Sie ihn neu:

```powershell
python a2a_client.py --stream
```

**Eingabe:** `Haben wir 60 blaue Patchkabel?`

```
   [Ereignis] task          -> SUBMITTED (eingereicht)
   [Ereignis] statusUpdate  -> WORKING (in Arbeit)
   [Ereignis] artifactUpdate -> 'bestandsauskunft'
   [Ereignis] statusUpdate  -> COMPLETED (erledigt)
```

**Beobachten Sie:** Ohne Streaming kommt **eine** Antwort mit dem Endzustand. Mit Streaming kommen **mehrere Ereignisse** nacheinander, Sie sehen den Lebenslauf der Aufgabe live. Mit `--roh` zeigt der Client zusätzlich das vollständige JSON jeder Antwort.

**Befehle im Client:** `exit` beendet, `neu` verwirft eine offene Rückfrage, `karte` zeigt die Agent Card.

---

# Lab 03: Zwei Agenten arbeiten zusammen (mit LLM)

Jetzt übernimmt der **Laborplanungs-Agent** die Rolle des Clients. Er hat ein LLM, das plant und rechnet, und delegiert Bestandsfragen an den Lager-Agenten.

**Aktion (Fenster 2, Lager-Agent läuft weiter in Fenster 1):**
```powershell
python planungs_agent_ollama.py
```
(Mit Anthropic: `python planungs_agent.py`)

**Erwartete Ausgabe:**
```
 Ollama A2A Laborplanungs-Agent gestartet
 Modell: qwen2.5-coder:3b
 1 Agent verfügbar: Lager-Agent Netzwerklabor
   - Skill bestand_pruefen: Prüft, ob eine gewünschte Anzahl Patchkabel ...
```

> **Vergleich mit MCP-Basics:** `planungs_agent_ollama.py` ist wie [`mcp_client_ollama.py`](code/mcp_client_ollama.py) aufgebaut. Dort antwortete das LLM mit `{"tool": "patchkabel_bestand_abfragen", "farbe": "blau"}` und der Client rief ein **Tool** auf. Hier antwortet es mit `{"agent": "lager", "auftrag": "..."}` und der Client beauftragt einen **Agenten**. Statt `list_tools()` beim Start lädt der Client die **Agent Card**.

### Aufgabe 3.1: Planen und delegieren

**Eingabe:** `Im Kurs sind 12 Teilnehmende, jede Person braucht 2 blaue Patchkabel. Reicht unser Bestand?`

**Erwarteter Ablauf (Beispiel):**
```
 Verarbeite Anfrage... (1 Nachrichten im Verlauf)

[Planungs-Agent -> Lager-Agent] A2A-Auftrag: Haben wir 24 blaue Patchkabel?
[Lager-Agent] Zustand: COMPLETED (erledigt)
[Lager-Agent] Ergebnis:
Artefakt 'bestandsauskunft':
  Text:  24 Stück angefragt, 45 Stück auf Lager: ausreichend.
  ...

 Antwort:
   Ja, der Bestand reicht. Sie benötigen 24 blaue Patchkabel, im Lager sind 45 vorhanden.
```

**Beobachten Sie die Arbeitsteilung:**
- Das **LLM des Planungs-Agenten** rechnet 12 × 2 = 24 und formuliert den Auftrag.
- Der **Lager-Agent** prüft den Bestand mit seinem MCP-Tool (Fenster 1).
- Das LLM formuliert aus dem Artefakt die Antwort für Sie.

### Aufgabe 3.2: Rückfrage an den Menschen weiterreichen

**Eingabe:** `Wir brauchen 50 Patchkabel für den Aufbau, reicht das?`

Fehlt im Auftrag die Farbe, stellt der Lager-Agent eine Rückfrage. Der Planungs-Agent gibt sie an Sie weiter (`Ihre Antwort an den Lager-Agenten:`). Antworten Sie z. B. mit `rot`.

> **Hinweis:** Ein kleines Modell wie `qwen2.5-coder:3b` formuliert den Auftrag nicht immer gleich. Manchmal ergänzt es die Farbe selbst, manchmal antwortet es ohne zu delegieren. Gerade diese Unterschiede eignen sich gut für die Diskussion: Wer entscheidet hier was?

### Aufgabe 3.3: Frage ohne Lagerbezug

**Eingabe:** `Was ist der Unterschied zwischen einem Patchkabel und einem Crossover-Kabel?`

**Erwartet:** Der Planungs-Agent antwortet selbst, **ohne** A2A-Auftrag. In Fenster 1 passiert nichts.

---

## Aufräumen

- Planungs-Agent und Client mit `exit` beenden
- Lager-Agent in Fenster 1 mit **Strg+C** beenden
- `deactivate`

---

## Weitere mögliche Lernaufgaben

- Ergänzen Sie in `lager_agent.py` einen zweiten Skill (z. B. `kabel_reservieren`) und prüfen Sie, wie sich die Agent Card ändert.
- Lassen Sie den Lager-Agenten statt einfacher Regeln selbst ein LLM benutzen. Muss der Planungs-Agent dafür geändert werden?
- Starten Sie den Lager-Agenten auf einem zweiten Rechner (Adresse in `HOST` und `LAGER_AGENT_URL` anpassen). Was ändert sich an der Sicherheit?
- Übertragen Sie das Muster auf das Klassenfahrt-Beispiel: Ein Planungs-Agent fragt den Buchungsagenten einer Jugendherberge an.

---

## Zusätzliche Ressourcen

- **A2A-Spezifikation:** https://a2a-protocol.org/latest/specification/
- **A2A Python SDK:** https://github.com/a2aproject/a2a-python
- **A2A Beispiele:** https://github.com/a2aproject/a2a-samples
- **A2A Inspector (Weboberfläche zum Testen von Agenten):** https://github.com/a2aproject/a2a-inspector
- **Model Context Protocol:** https://modelcontextprotocol.io/

---

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.0 (a2a-sdk 1.3.1, A2A-Spezifikation 1.0, mcp 2.3.0)

![line](images/banner.png)
<p align="center">
<a href="05_inspector.md"><img src="images/previous.png" width="150px"></a>
<a href="07_a2a_agent.md"><img src="images/next.png" width="150px"></a>
</p>
