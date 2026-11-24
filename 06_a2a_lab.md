# Hinführung zu A2A (Agent2Agent-Protokoll)

![line](images/banner.png)

## Einführung
In der Reihe [*MCP-Basics*](01_lab.md) hat ein LLM über das Model Context Protocol **Werkzeuge** benutzt. Der „Agent“ war dort das Zusammenspiel aus dem Python-Programm `mcp_client_ollama.py` und dem LLM:

- Das **LLM** entscheidet, **welches** der drei Tools gebraucht wird und **mit welchen Parametern** (z. B. `{"tool": "patchkabel_bestand_abfragen", "farbe": "blau"}`).
- Der **Python-Client** führt diese Entscheidung aus: Er sendet `tools/call` an den MCP-Server und gibt das Ergebnis an das LLM zurück.

Der Aufrufer bestimmt bei MCP also **jedes Detail** des Aufrufs. Der MCP-Server führt nur aus und entscheidet selbst nichts.

Sobald mehrere Agenten zusammenarbeiten, ändert sich die Frage. Ein Agent soll eine Aufgabe nicht selbst erledigen, sondern an einen **anderen Agenten** abgeben, der eigene Daten, eigene Werkzeuge und eigene Regeln hat und oft von jemand anderem betrieben wird. Der beauftragende Agent will dann nicht mehr bestimmen, *wie* die Aufgabe gelöst wird. Er erteilt nur einen **Auftrag**, beantwortet Rückfragen und bekommt am Ende ein Ergebnis. **Wie** der Auftrag erledigt wird, entscheidet der beauftragte Agent selbst.

Dafür gibt es das **Agent2Agent-Protokoll (A2A)**. Es wurde von Google gestartet, liegt heute bei der Linux Foundation und ist seit Version 1.0 stabil. Merksatz für diese Reihe:

> **MCP verbindet einen Agenten mit seinen Werkzeugen. A2A verbindet einen Agenten mit einem Kollegen.**

## Rollen: Orchestrator, Fachagent, Werkzeug

In jedem Multi-Agenten-System tauchen dieselben drei Rollen auf, egal ob es um Laborplanung, eine Klassenfahrt oder einen Onlineshop geht. Diese Reihe verwendet durchgehend diese Bezeichnungen:

| Rolle (universell) | im Beispiel | Protokoll | LLM | Aufgabe |
|---|---|---|---|---|
| **Orchestrator** | Laborplanungs-Agent (`planungs_agent_ollama.py`) | A2A-Client | ja | versteht die Benutzeranfrage, zerlegt sie, wählt den passenden Fachagenten, beauftragt ihn und fasst die Ergebnisse zusammen |
| **Fachagent** | Lager-Agent, Bestell-Agent, Raumbuchungs-Agent | A2A-Server nach außen, MCP-Client nach innen | optional (hier nein) | erledigt einen Auftrag seines Fachgebiets selbstständig und meldet seinen Zustand (erledigt, Rückfrage, abgelehnt, abgebrochen) |
| **Werkzeug** (Tool-Server) | `mcp_server.py` mit drei Tools | MCP-Server | nein | führt eine genau beschriebene Funktion aus |

**Wer ist Client, wer ist Server?** Die Begriffe kommen in beiden Protokollen vor und bedeuten jeweils nur „wer fragt“ und „wer antwortet“:

| | Client (fragt, beauftragt) | Server (antwortet, wird beauftragt) |
|---|---|---|
| **MCP** (Teil 1) | `mcp_client_ollama.py` | `mcp_server.py` (Werkzeug) |
| **MCP** (Teil 2) | jeder Fachagent intern | `mcp_server.py` (Werkzeug) |
| **A2A** (Teil 2) | Orchestrator (`planungs_agent_ollama.py`) oder `a2a_client.py` | jeder Fachagent |

Ein Fachagent ist also **beides**: A2A-Server gegenüber dem Orchestrator und MCP-Client gegenüber seinem Werkzeug. Wenn im Folgenden vom „Server“ die Rede ist, steht immer dabei, ob der A2A-Server (Fachagent) oder der MCP-Server (Werkzeug) gemeint ist.

> **Kernerkenntnis: Der Lager-Agent ist der MCP-Client, der zum Agenten aufgerüstet wurde.**
>
> Vorher (Teil 1): `mcp_client_ollama.py` (mit LLM) ──MCP──> `mcp_server.py`
>
> Jetzt (Teil 2): Orchestrator (mit LLM) ══A2A══> Lager-Agent ──MCP──> `mcp_server.py`
>
> Der Lager-Agent hat sein **LLM abgegeben** (es sitzt jetzt im Orchestrator) und dafür eine **A2A-Schnittstelle mit Agent Card** bekommen. Zum Agenten wird er nicht durch ein LLM, sondern weil er einen Auftrag **selbstständig erledigt** und seinen **Zustand meldet** (erledigt, Rückfrage, abgelehnt). Agenten gibt es auch ohne LLM.
>
> Bild dazu: Der MCP-Server ist das **Werkzeug**. Der Lager-Agent ist der **Kollege, der das Werkzeug bedient**. Der Orchestrator ist die **Kollegin, die den Auftrag vergibt**.

## Grundbegriffe: Agent und Harness

> **Was macht etwas zum Agenten?**
> Ein Agent **nimmt wahr**, **entscheidet** und **handelt**, und zwar in einer **Schleife** und auf ein **Ziel** hin. Er macht so lange weiter, bis er das Ziel für erreicht hält (oder nicht weiterkommt und das meldet). Dabei arbeitet er mit einer gewissen Selbstständigkeit: Niemand gibt ihm jeden einzelnen Schritt vor.
>
> **Wer** entscheidet, ist zweitrangig. Das kann ein LLM sein, aber auch feste Regeln. In der Fachliteratur unterscheidet man z. B. Reflex-, Regel- und Planungs-Agenten. Ein Sprachmodell allein ist also noch kein Agent, und ein Agent braucht nicht unbedingt ein Sprachmodell.

> **Was ist ein Harness?**
> Ein LLM erzeugt nur Text. Damit daraus ein Agent wird, braucht es ein Programm **um das Modell herum**, den *Harness* (engl. Geschirr, Gurtzeug). Er
> - führt die Schleife aus (Modell fragen, Antwort auswerten, wieder fragen),
> - bietet dem Modell die Werkzeuge an und führt dessen Werkzeugaufrufe aus,
> - verwaltet den Verlauf (Kontext) und den System-Prompt,
> - entscheidet, wann Schluss ist: wenn das Modell ohne Werkzeugaufruf antwortet, nach einer Höchstzahl von Schritten oder wenn ein Mensch zustimmen muss.

**Im Beispiel dieser Reihe:**

| Programm | Rolle | Wer entscheidet? | Agent? |
|---|---|---|---|
| `mcp_client_ollama.py` (Teil 1) | – | LLM | Mini-Harness um das LLM: Verlauf, System-Prompt, Tool-JSON erkennen, `tools/call`. Macht nur **einen** Werkzeugschritt, noch keine echte Schleife |
| `planungs_agent_ollama.py` | Orchestrator | LLM | Harness um das LLM, das statt eines Tools einen **Fachagenten** auswählt und beauftragt |
| `a2a_client.py` | Orchestrator (Mensch) | **Sie** | kein Agent, sondern ein Werkzeug für Sie: Sie wählen den Fachagenten selbst |
| `lager_agent.py`, `bestell_agent.py`, `raum_agent.py` | Fachagent | feste Regeln | **Agenten ohne LLM**: nehmen einen Auftrag an, entscheiden (erledigen, nachfragen, ablehnen), handeln mit ihrem Werkzeug und melden ihren Zustand |
| `mcp_server.py` | Werkzeug | niemand | führt genau das aus, was verlangt wird |

Mehr dazu in [Kapitel 08, Agent und Harness im Beispiel](08_a2a_architecture.md#agent-und-harness-im-beispiel).

## Lernziele

- Die Rollen **Orchestrator**, **Fachagent** und **Werkzeug** unterscheiden und den Programmen des Beispiels zuordnen
- Die Begriffe **Agent** und **Harness** erklären
- Den Unterschied zwischen einem Werkzeug (MCP) und einem Kollegen-Agenten (A2A) an einem Beispiel erklären
- Fachagenten (A2A-Server) starten und ihre **Agent Cards** über die Discovery-Adresse `/.well-known/agent-card.json` abrufen
- Aufträge an Fachagenten senden und den **Lebenslauf einer Aufgabe (Task)** beobachten: eingereicht, in Arbeit, Rückfrage, erledigt, abgelehnt, abgebrochen
- **Messages, Parts und Artifacts** unterscheiden
- Nachvollziehen, wie ein Orchestrator mit LLM anhand der Agent Cards den passenden Fachagenten auswählt
- Kommunikationsvorgänge (Benutzer, LLM, A2A, MCP) ordnen und trennen

## Szenario
Sie bereiten weiterhin den Netzwerktechnikkurs vor. Inzwischen gibt es im Labor drei getrennte Zuständigkeiten, jede mit einem eigenen **Fachagenten**:

| Fachagent | Adresse | Fachgebiet | Werkzeug (MCP-Tool) |
|---|---|---|---|
| **Lager-Agent** | `http://127.0.0.1:9999` | prüft, ob genug Patchkabel **vorhanden** sind | `patchkabel_bestand_abfragen` |
| **Bestell-Agent** | `http://127.0.0.1:9998` | **bestellt** Patchkabel beim Lieferanten nach, über 50 Euro nur mit Freigabe | `patchkabel_katalog_abfragen` |
| **Raumbuchungs-Agent** | `http://127.0.0.1:9997` | reserviert Laborraum 104 oder 105, schlägt bei Belegung den anderen Raum vor | `laborraum_belegung_abfragen` |

Alle drei Fachagenten arbeiten **ohne LLM** mit festen Regeln und nutzen intern die Tools aus *MCP-Basics*. Wie sie intern arbeiten, ist ihre Sache.

Der **Laborplanungs-Agent** ist der **Orchestrator**. Er unterstützt Sie bei der Kursplanung, rechnet aus, wie viel Material ein Kurs braucht, hat aber **keinen** Zugriff auf Lager, Lieferant oder Raumplan. Er lädt beim Start die Agent Cards aller Fachagenten und entscheidet mit seinem LLM, welcher Fachagent welchen Auftrag bekommt.

```
                                        ┌══A2A══> Lager-Agent         :9999 ──MCP──> patchkabel_bestand_abfragen
 Benutzer ──> Laborplanungs-Agent ══════╪══A2A══> Bestell-Agent       :9998 ──MCP──> patchkabel_katalog_abfragen
              (Orchestrator, LLM)       └══A2A══> Raumbuchungs-Agent  :9997 ──MCP──> laborraum_belegung_abfragen
                                                  (Fachagenten, Regeln)              (Werkzeug: mcp_server.py)
```

## Voraussetzungen

- Python 3.11 oder höher
- Abgeschlossener Teil 1 [*MCP-Basics*](01_lab.md) (empfohlen, nicht zwingend)
- Für Lab 03: Ollama 0.13.3 oder höher mit dem Modell `qwen2.5-coder:3b` (wie in Teil 1, kein API-Schlüssel nötig)
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

| Datei | Rolle | Aufgabe |
|---|---|---|
| `mcp_server.py` | Werkzeug | MCP-Server mit drei Tools (identisch mit [`code/mcp_server.py`](code/mcp_server.py) aus Teil 1) |
| `lager_agent.py` | Fachagent | **A2A-Server** auf Port 9999, nutzt das Tool `patchkabel_bestand_abfragen` |
| `bestell_agent.py` | Fachagent | **A2A-Server** auf Port 9998, nutzt das Tool `patchkabel_katalog_abfragen` |
| `raum_agent.py` | Fachagent | **A2A-Server** auf Port 9997, nutzt das Tool `laborraum_belegung_abfragen` |
| `fachagent_hilfen.py` | – | gemeinsame Hilfen der Fachagenten (MCP-Aufruf, Server starten) |
| `fachagenten_starten.py` | – | startet alle drei Fachagenten in **einem** Fenster |
| `agenten.json` | – | Liste der Fachagenten mit ihrer Basis-URL (hier beginnt die Discovery) |
| `a2a_verbindung.py` | – | Hilfsschicht für A2A-Clients (Discovery, Senden, Auswerten, Delegieren) |
| `a2a_client.py` | Orchestrator (Sie) | **A2A-Client ohne LLM**: Sie wählen den Fachagenten selbst |
| `planungs_agent_ollama.py` | Orchestrator | **Laborplanungs-Agent** mit Ollama: das LLM wählt den Fachagenten |
| `anfragen\*.json` | – | Rohe JSON-RPC-Anfragen für Laborübung 2 |
| `requirements.txt` | – | Bibliotheken mit Versionsbereichen (wie in *MCP-Basics*) |

> **Wichtig:** Ein Ordner für alles, eine virtuelle Umgebung für alles.

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

**Erwartet:** `a2a-sdk` in Version **1.3.x** (setzt die A2A-Spezifikation **1.0** um), `mcp` in Version **2.x** und `ollama`.

> **Wichtig:** Viele Tutorials im Netz beziehen sich noch auf A2A 0.3 (Methoden wie `message/send`, Felder wie `"kind": "text"`). Diese Schreibweise funktioniert mit dem Code dieser Reihe nicht. Achten Sie bei eigenen Recherchen auf die Version.

Ollama prüfen Sie wie in [*MCP-Basics*, Schritt 3](01_lab.md) mit `ollama list` (Modell `qwen2.5-coder:3b` muss vorhanden sein).

---

# Lab 01: Fachagenten starten und ihre Visitenkarten lesen

Ein A2A-Agent ist ein **Webserver**. Er läuft dauerhaft und wartet auf Aufträge, anders als der MCP-Server aus *MCP-Basics*, den der Client bei Bedarf als Unterprozess gestartet hat. Deshalb arbeiten Sie ab jetzt mit **zwei Fenstern**:

| Fenster | Darin läuft | Rolle |
|---|---|---|
| **Fenster 1** | die Fachagenten (A2A-Server) | wird beauftragt, protokolliert, was **intern** passiert |
| **Fenster 2** | `a2a_client.py` oder `planungs_agent_ollama.py` (A2A-Client) | beauftragt |

### Schritt 1: Den Lager-Agenten allein starten

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

> **Wichtig:** Das Fenster bleibt offen und zeigt keinen Prompt mehr, denn der Agent wartet jetzt auf Aufträge. Alle weiteren Befehle geben Sie in einem **zweiten** PowerShell-Fenster ein.

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
      "description": "Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager VORHANDEN ist, und meldet Bestand und Fehlmenge. Bestellt nichts.",
      "examples": ["Haben wir 30 blaue Patchkabel?", "..."]
    }
  ]
}
```

**Beobachten Sie:**
- Die Agent Card ist die **Visitenkarte** des Fachagenten. Jeder, der die Adresse kennt, kann sie lesen. Das nennt man **Discovery**.
- Die Adresse `/.well-known/agent-card.json` ist im Standard festgelegt. Der **A2A-Client** (später der Orchestrator) muss deshalb vom **A2A-Server** (dem Fachagenten) nur die **Basis-URL** kennen, hier `http://127.0.0.1:9999`. Den Rest (Name, Fähigkeiten, Adresse für Aufträge) liest er aus der Agent Card.
- Die Karte beschreibt **was** der Agent kann (Skills), nicht **wie**. Vom MCP-Tool, das der Lager-Agent intern benutzt, steht hier nichts.

> **Vergleich mit MCP:** Dort lieferte `tools/list` ein genaues `inputSchema` mit Parametern und erlaubten Werten. Eine Agent Card enthält kein solches Schema. Ein Kollege bekommt einen Auftrag in natürlicher Sprache oder als Daten, kein Formular.

### Schritt 3: Alle drei Fachagenten starten

Beenden Sie den Lager-Agenten in Fenster 1 mit **Strg+C** und starten Sie alle drei Fachagenten gemeinsam:

```powershell
python fachagenten_starten.py
```

**Erwartete Ausgabe (Reihenfolge kann abweichen):**
```
[Lager] Lager-Agent Netzwerklabor (A2A-Server)
[Lager] Agent Card: http://127.0.0.1:9999/.well-known/agent-card.json
...
[Bestellung] Bestell-Agent Netzwerklabor (A2A-Server)
[Bestellung] Agent Card: http://127.0.0.1:9998/.well-known/agent-card.json
...
[Raum] Raumbuchungs-Agent Netzwerklabor (A2A-Server)
[Raum] Agent Card: http://127.0.0.1:9997/.well-known/agent-card.json
...
```

Jeder Fachagent ist ein eigener Webserver mit **eigenem Port** und **eigener Agent Card**. Das Skript startet die drei Programme nur gemeinsam und stellt jeder Zeile den Namen des Agenten voran. Mit **Strg+C** beenden Sie alle drei.

> **Alternative:** Sie können jeden Fachagenten auch in einem eigenen Fenster starten (`python lager_agent.py`, `python bestell_agent.py`, `python raum_agent.py`).

### Schritt 4: Agent Cards vergleichen

Öffnen Sie im Browser auch die beiden anderen Agent Cards:

```
http://127.0.0.1:9998/.well-known/agent-card.json
http://127.0.0.1:9997/.well-known/agent-card.json
```

**Aufgabe:** Lesen Sie die Skill-Beschreibungen von Lager-Agent und Bestell-Agent. Beide haben mit Patchkabeln zu tun. Woran soll ein Orchestrator erkennen, an wen er „Haben wir 20 gelbe Kabel?“ schicken muss? Welche Wörter in den Beschreibungen helfen dabei?

Die Liste der Basis-URLs steht in `agenten.json`. Von hier aus lädt jeder A2A-Client dieser Reihe beim Start alle Agent Cards:

```json
{
  "lager":      "http://127.0.0.1:9999",
  "bestellung": "http://127.0.0.1:9998",
  "raum":       "http://127.0.0.1:9997"
}
```

---

# Lab 02: Fachagenten direkt beauftragen (ohne LLM)

Zuerst lassen wir das LLM weg. **Sie selbst** sind jetzt der Orchestrator: Sie wählen den Fachagenten aus und formulieren den Auftrag. So sehen Sie das Protokoll ohne Ablenkung.

**Aktion (PowerShell-Fenster 2, venv aktiv, Fachagenten laufen in Fenster 1):**
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
python a2a_client.py
```

**Erwartete Ausgabe:**
```
A2A-Client (ohne LLM) gestartet - Sie sind der Orchestrator
Streaming: nein (SendMessage)   Rohes JSON: nein
3 Fachagent(en) laut Agent Cards:
   [lager] Lager-Agent Netzwerklabor  http://127.0.0.1:9999
        Skill bestand_pruefen: Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager VORHANDEN ist, ...
   [bestellung] Bestell-Agent Netzwerklabor  http://127.0.0.1:9998
        Skill material_bestellen: Bestellt Patchkabel (1 m) beim Lieferanten NACH, ...
   [raum] Raumbuchungs-Agent Netzwerklabor  http://127.0.0.1:9997
        Skill laborraum_buchen: Prüft die Belegung der Laborräume 104 und 105 und reserviert ...

Befehle: 'agent <name>' wechselt den Fachagenten, 'karte' zeigt seine Agent Card,
         'neu' beginnt eine neue Aufgabe, 'exit' beendet.
Eingabe in { } wird als strukturierte Daten (data-Part) gesendet, z. B. {"farbe": "rot", "menge": 10}
============================================================

[lager] Ihre Nachricht (oder 'exit'):
```

Der Client hat **drei Agent Cards** geladen, bevor Sie irgendetwas eingegeben haben. In eckigen Klammern im Prompt steht, an welchen Fachagenten Ihre Nachricht geht (zu Beginn `[lager]`).

> **Meldung „Fehler: Fachagent nicht erreichbar“?** Dann läuft in Fenster 1 kein Fachagent. Starten Sie `python fachagenten_starten.py` (Lab 01, Schritt 3). Läuft nur ein Teil der Fachagenten, meldet der Client `Hinweis: Fachagent '…' nicht erreichbar, wird übersprungen` und arbeitet mit den übrigen weiter.

### Aufgabe 2.1: Ein einfacher Auftrag

**Eingabe:** `Haben wir 30 blaue Patchkabel?`

```
Task-ID:    e0522d9a-...
Context-ID: c145cbeb-...
Zustand:    COMPLETED (erledigt)
Nachricht:  Bestandsprüfung abgeschlossen.
Artefakt 'bestandsauskunft':
  Text:  30 Stück angefragt, 45 Stück auf Lager: ausreichend.
  Daten: {"angefragt": 30, "laenge_m": 1, "fehlmenge": 0, "farbe": "blau", "ausreichend": true, "bestand": 45}
```

Sehen Sie gleichzeitig in **Fenster 1** nach: Dort steht, dass der Lager-Agent einen Task angelegt, die Nachricht verstanden und sein MCP-Tool aufgerufen hat:

```
[Lager] [A2A] Neuer Task e0522d9a... (Zustand: SUBMITTED)
[Lager]    Nachricht: Haben wir 30 blaue Patchkabel?
[Lager]    -> In Arbeit (Zustand: WORKING)
[Lager]    Verstanden: {'farbe': 'blau', 'menge': 30}
[Lager]    [MCP]  tools/call patchkabel_bestand_abfragen {'farbe': 'blau'}
[Lager]    [MCP]  Ergebnis: Bestand blaue 1m Patchkabel: 45 Stück
[Lager]    Artefakt 'bestandsauskunft': {...}
[Lager]    -> Erledigt (Zustand: COMPLETED)
```

**Beobachten Sie:**
- Aus Ihrer Nachricht wurde eine **Aufgabe (Task)** mit eigener ID und einem **Zustand**.
- Das Ergebnis kommt als **Artefakt** mit zwei Teilen (**Parts**): einem Text für Menschen und strukturierten Daten für Programme.
- Den MCP-Aufruf sehen nur Sie in Fenster 1. Über A2A kommt beim Auftraggeber nur das Ergebnis an.

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

**Erwartet:** `REJECTED (abgelehnt)` mit der Begründung, dass das Lager grüne Kabel nicht führt. Der Lager-Agent ruft sein Tool gar nicht erst auf (siehe Fenster 1).

### Aufgabe 2.4: Strukturierte Daten statt Text

**Eingabe:** `{"farbe": "rot", "menge": 40}`

Der Client schickt die Eingabe jetzt als **data-Part** statt als Text-Part. Das Ergebnis ist dasselbe, aber der Lager-Agent muss nichts mehr „verstehen“, weil die Angaben bereits strukturiert sind.

### Aufgabe 2.5: Den Bestell-Agenten beauftragen

**Eingabe:** `agent bestellung`

```
Aufträge gehen jetzt an: Bestell-Agent Netzwerklabor
```

Der Prompt zeigt jetzt `[bestellung]`. Probieren Sie nacheinander:

| Eingabe | Erwarteter Zustand | Warum? |
|---|---|---|
| `Bestelle 20 gelbe Patchkabel` | `COMPLETED`, Artefakt `bestellbestaetigung` (36.00 Euro) | unter 50 Euro, keine Freigabe nötig |
| `Bestelle 100 grüne Patchkabel` | `INPUT_REQUIRED`: „… kostet 180.00 Euro … Freigeben? (ja/nein)“ | über 50 Euro: Der Fachagent fragt nach einer **Freigabe** |
| Antwort `ja` | `COMPLETED` | Freigabe erteilt |
| `Bestelle 50 gelbe Patchkabel`, Antwort `nein` | `CANCELED (abgebrochen)` | Auftraggeber verweigert die Freigabe |
| `Bestelle 200 rote Patchkabel` | `REJECTED`: „… überschreitet das Budget von 250 Euro.“ | Regel des Fachagenten, keine Rückfrage möglich |
| `Bestelle 10 lila Patchkabel` | `REJECTED`: „Patchkabel in 'lila' führt der Lieferant nicht.“ | unbekannte Farbe |

**Beobachten Sie:**
- Grüne Kabel lehnt der **Lager-Agent** ab (nicht im Lager), der **Bestell-Agent** kann sie bestellen. Jeder Fachagent hat seine eigenen Regeln.
- Die Freigabe-Rückfrage ist eine **Entscheidung**, die der Fachagent bewusst an den Auftraggeber zurückgibt. Typisch für Agenten, die etwas tun, das Geld kostet.
- In Fenster 1 sehen Sie, dass der Bestell-Agent das Tool `patchkabel_katalog_abfragen` aufruft, um den Preis zu ermitteln.

### Aufgabe 2.6: Den Raumbuchungs-Agenten beauftragen

**Eingabe:** `agent raum`, dann `Reserviere Raum 104 für Donnerstag`

```
Zustand:    INPUT_REQUIRED (Rückfrage)
Nachricht:  Raum 104 ist am Donnerstag belegt. Raum 105 ist frei. Soll ich Raum 105 reservieren? (ja/nein)
```

**Eingabe:** `ja`

```
Zustand:    COMPLETED (erledigt)
Nachricht:  Reservierung abgeschlossen.
Artefakt 'reservierung':
  Text:  Raum 105 ist für Donnerstag reserviert.
  Daten: {"raum": "105", "tag": "donnerstag", "reserviert": true}
```

**Beobachten Sie:** Der Raumbuchungs-Agent erledigt nicht einfach, was verlangt wurde. Er prüft mit seinem Tool **beide** Räume (Fenster 1) und macht einen **Gegenvorschlag**. Stellen Sie denselben Auftrag noch einmal: Jetzt sind beide Räume am Donnerstag belegt und der Auftrag wird abgelehnt (`REJECTED`). Der Fachagent merkt sich seine Reservierungen, solange er läuft.

Probieren Sie auch `Reserviere Raum 105` ohne Wochentag: Der Fachagent fragt nach dem Tag.

### Aufgabe 2.7: Streaming (--stream) und rohes JSON (--roh)

Der Client kennt zwei Schalter, die Unterschiedliches bewirken:

| Schalter | ändert | Wirkung |
|---|---|---|
| ohne | – | Methode **SendMessage**: eine Anfrage, **eine** Antwort mit dem Endzustand |
| `--stream` | **was gesendet wird** | Methode **SendStreamingMessage**: eine Anfrage, **mehrere Ereignisse** nacheinander (Server-Sent Events) |
| `--roh` | **wie viel angezeigt wird** | zusätzlich das vollständige JSON jeder Antwort bzw. jedes Ereignisses. Am Protokoll ändert sich nichts |

Beide Schalter lassen sich kombinieren: `python a2a_client.py --stream --roh`.

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

**Beobachten Sie:** Ohne Streaming kommt **eine** Antwort mit dem Endzustand. Mit Streaming kommen **mehrere Ereignisse** nacheinander, Sie sehen den Lebenslauf der Aufgabe live. Zwischen WORKING und dem Artefakt liegt etwa eine Sekunde, weil der Lager-Agent zur Veranschaulichung kurz wartet.

**Vergleichen Sie mit Fenster 1:** Der Lager-Agent protokolliert dieselben Zustände aus seiner Sicht (`SUBMITTED`, `WORKING`, `COMPLETED`) und zusätzlich, was nur er sieht: wie er den Auftrag verstanden hat und welchen MCP-Aufruf er macht. Fenster 2 zeigt, was davon **über A2A** beim Auftraggeber ankommt.

> **Tipp:** Fehlt im Client ein Ereignis, zeigt `curl.exe` aus [Kapitel 10, Schritt 8](10_a2a_protokoll.md), was der Fachagent tatsächlich gesendet hat. So lässt sich unterscheiden, ob der Server oder der Client die Ursache ist.

**Befehle im Client:** `agent <name>` wechselt den Fachagenten, `karte` zeigt dessen Agent Card, `neu` verwirft eine offene Rückfrage, `exit` beendet.

---

# Lab 03: Der Orchestrator wählt den Fachagenten (mit LLM)

Jetzt übernimmt der **Laborplanungs-Agent** die Rolle des Orchestrators, die Sie in Lab 02 selbst hatten. Sein LLM plant, rechnet und **entscheidet anhand der Agent Cards**, welcher Fachagent einen Auftrag bekommt.

**Aktion (Fenster 2, die Fachagenten laufen weiter in Fenster 1):**
```powershell
python planungs_agent_ollama.py
```

**Erwartete Ausgabe:**
```
 Ollama A2A Laborplanungs-Agent (Orchestrator) gestartet
 Modell: qwen2.5-coder:3b
 3 Fachagenten verfügbar:
   - [lager] Lager-Agent Netzwerklabor: Prüft, ob eine gewünschte Anzahl Patchkabel ...
   - [bestellung] Bestell-Agent Netzwerklabor: Bestellt Patchkabel (1 m) beim Lieferanten NACH, ...
   - [raum] Raumbuchungs-Agent Netzwerklabor: Prüft die Belegung der Laborräume 104 und 105 ...
 Befehle: 'exit' beendet, 'neu' startet ein neues Gespräch
```

> **Vergleich mit MCP-Basics:** `planungs_agent_ollama.py` ist wie [`mcp_client_ollama.py`](code/mcp_client_ollama.py) aufgebaut. Dort lud der Client beim Start mit `tools/list` **drei Tools**, das LLM wählte eines und antwortete z. B. mit `{"tool": "patchkabel_bestand_abfragen", "farbe": "blau"}`. Hier lädt der Orchestrator beim Start **drei Agent Cards**, das LLM wählt einen Fachagenten und antwortet z. B. mit `{"agent": "lager", "auftrag": "Haben wir 24 blaue Patchkabel?"}`. Der Unterschied: Das Tool bekam **Parameter**, der Fachagent bekommt einen **Auftrag**.

### Aufgabe 3.1: Planen, auswählen, delegieren

**Eingabe:** `Im Kurs sind 12 Teilnehmende, jede Person braucht 2 blaue Patchkabel. Reicht unser Bestand?`

**Erwarteter Ablauf (Beispiel):**
```
 Verarbeite Anfrage... (1 Nachrichten im Verlauf)
 LLM wählt Fachagent: lager

[Orchestrator -> Lager-Agent Netzwerklabor] A2A-Auftrag: Haben wir 24 blaue Patchkabel?
[Lager-Agent Netzwerklabor] Zustand: COMPLETED (erledigt)
[Lager-Agent Netzwerklabor] Ergebnis:
Artefakt 'bestandsauskunft':
  Text:  24 Stück angefragt, 45 Stück auf Lager: ausreichend.
  ...

 Antwort:
   Ja, der Bestand reicht. Sie benötigen 24 blaue Patchkabel, im Lager sind 45 vorhanden.
```

**Beobachten Sie die Arbeitsteilung:**
- Das **LLM des Orchestrators** rechnet 12 × 2 = 24, **wählt** den Lager-Agenten und formuliert den Auftrag.
- Der **Lager-Agent** prüft den Bestand mit seinem MCP-Tool (Fenster 1).
- Das LLM formuliert aus dem Artefakt die Antwort für Sie.

### Aufgabe 3.2: Welcher Fachagent ist zuständig?

Stellen Sie die folgenden Fragen und notieren Sie, welchen Fachagenten das LLM wählt (Zeile `LLM wählt Fachagent:`):

| Testfrage | Erwarteter Fachagent |
|---|---|
| Reichen 20 blaue Kabel für den Kurs? | `lager` |
| Der Lieferant soll uns 20 schwarze Kabel schicken. | `bestellung` |
| Haben wir 20 gelbe Kabel? | `lager` (das Lager führt Gelb nicht und lehnt ab) |
| Wir brauchen nächste Woche 30 grüne Kabel, das Lager hat keine. Kümmere dich darum. | `bestellung` (Freigabe-Rückfrage, da 54 Euro) |
| Wir brauchen am Montag einen Laborraum, am liebsten 104. | `raum` (Gegenvorschlag Raum 105) |
| Was ist ein Patchkabel? | keiner (das LLM antwortet selbst) |

Die Testfragen weichen absichtlich von den Beispielen im System-Prompt des Orchestrators ab, damit das LLM wirklich auswählen muss.

Stellt ein Fachagent eine Rückfrage (z. B. die Freigabe beim Bestell-Agenten oder den Gegenvorschlag beim Raumbuchungs-Agenten), reicht der Orchestrator sie an Sie weiter: `Ihre Antwort an den Bestell-Agent Netzwerklabor:`. Antworten Sie mit `ja` oder `nein`.

> **Hinweis:** Ein kleines Modell wie `qwen2.5-coder:3b` entscheidet nicht immer gleich. Gerade Lager und Bestellung kann es verwechseln, weil beide mit Patchkabeln zu tun haben. Manchmal ergänzt es Angaben selbst, manchmal antwortet es ohne zu delegieren. Diese Unterschiede eignen sich gut für die Diskussion: Wer entscheidet hier was, und welche Wörter in den Agent Cards helfen dem LLM bei der Auswahl?

### Aufgabe 3.3: Rückfrage an den Menschen weiterreichen

**Eingabe:** `Wir brauchen 50 Patchkabel für den Aufbau, reicht das?`

Fehlt im Auftrag die Farbe, stellt der Lager-Agent eine Rückfrage. Der Orchestrator gibt sie an Sie weiter (`Ihre Antwort an den Lager-Agent Netzwerklabor:`). Antworten Sie z. B. mit `rot`.

---

## Aufräumen

- Orchestrator und Client mit `exit` beenden
- Fachagenten in Fenster 1 mit **Strg+C** beenden
- `deactivate`

---

## Weitere mögliche Lernaufgaben

- Ergänzen Sie im Lager-Agenten einen zweiten Skill (z. B. `kabel_reservieren`) und prüfen Sie, wie sich die Agent Card ändert.
- Lassen Sie einen Fachagenten statt einfacher Regeln selbst ein LLM benutzen. Muss der Orchestrator dafür geändert werden?
- Bauen Sie einen vierten Fachagenten (eigener Port, eigene Agent Card, Eintrag in `agenten.json`). Ideen in [`zusatz_fachagenten.md`](zusatz_fachagenten.md).
- Starten Sie einen Fachagenten auf einem zweiten Rechner (Adresse in `HOST` und in `agenten.json` anpassen). Was ändert sich an der Sicherheit?
- Bauen Sie `mcp_client_ollama.py` aus Teil 1 zu einem echten Agent-Loop aus, der mehrere Werkzeugschritte nacheinander macht (siehe [Kapitel 08](08_a2a_architecture.md#transferaufgabe-vom-mini-harness-zum-agent-loop)).
- Übertragen Sie die Rollen auf das Klassenfahrt-Beispiel: Wer ist Orchestrator, welche Fachagenten gibt es (Unterkunft, Wetter, Budget), welche Werkzeuge benutzen sie?

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
- Version: v1.1 (a2a-sdk 1.3.1, A2A-Spezifikation 1.0, mcp 2.3.0; drei Fachagenten, Rollen, nur Ollama)

![line](images/banner.png)
<p align="center">
<a href="05_inspector.md"><img src="images/previous.png" width="150px"></a>
<a href="07_a2a_agent.md"><img src="images/next.png" width="150px"></a>
</p>
