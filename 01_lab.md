# Hinführung zu MCP (Model Context Protokoll)

![line](images/banner.png)

## Einführung
Chat-Anfragen an LLMs liefern je nach Fragestellung beeindruckende Ergebnisse. Die Qualität und die Schärfe der Antworten beruhen auf einem Trainingszustand des verwendeten Modells, der in der Vergangenheit liegt, der Kontext der Anfrage fehlt oft und muss abgeleitet werden. Um den Kontext herzustellen, können Anfragen angereichert werden. Es gibt verschiedene Kontexterweiterungsstrategien, die vom Provider bereitgestellt werden oder vom Nutzer bewusst eingesetzt werden. z. B.  RAG (Retrieval-Augmented Generation), Web Search, API Integration, Code-basierte Ansätze u.v.m.

Eine weitere Methode der Kontextualisieung bietet das Model Context Protocol, welches Sie hier kennenlernen werden.

## Lernziele 

- Grenzen einer Chat-Anfrage ohne Kontextbereitstellung austesten
- Kontextbereitstellung über bereitgestellte MCP-Tools an einem einfachen Beispiel erkunden
- Komponenten einer Toolbeschreibung und deren Aufgaben zuordnen
- Komponenten der MCP-Systemarchitektur benennen
- Kommunikationsvorgänge in der MCP-Systemarchitektur ordnen und trennen

## Szenario
Zur Vorbereitung eines Netzwerktechnikkurses möchten Sie sicherstellen, dass ausreichend Patchkabel im Labor vorhanden sind. Bei der Erfassung des aktuellen Lagerbestands möchten Sie ein LLM unterstütztes IT-System verwenden.
Der vereinfachte Lagerbestand umfasst blaue und rote Patchkabel mit einer Länge von jeweils 1 m.

Das IT-System kennt drei Werkzeuge (MCP-Tools) und muss je nach Frage das passende auswählen:

| Tool | Liefert |
|---|---|
| `patchkabel_bestand_abfragen` | Lagerbestand blauer und roter Patchkabel (oder gesamt) |
| `patchkabel_katalog_abfragen` | Preis und Lieferzeit beim Lieferanten (für Nachbestellungen), KEIN Lagerbestand |
| `laborraum_belegung_abfragen` | ob Laborraum 104 oder 105 an einem Wochentag belegt oder frei ist |

## Voraussetzungen

- Python 3.11 oder höher
- Ollama 0.13.3 (lokaler API-Provider), Modell qwen2.5-coder:3b

> **Hinweis:** Das gesamte Material arbeitet lokal mit Ollama. Es wird kein API-Schlüssel und kein Cloud-Konto benötigt, es entstehen keine Kosten.

## Vorbereitende Aufgaben

### Schritt 1: Python Installation überprüfen

1. Öffnen Sie die **Eingabeaufforderung** (cmd) oder **PowerShell**
2. Überprüfen Sie, ob Python installiert ist:

```cmd
python --version
```

**Erwartete Ausgabe:** `Python 3.11.x` oder höher

>  **Falls Python nicht installiert ist:**
> - Laden Sie Python von https://www.python.org/downloads/ herunter
> - Installieren Sie Python und aktivieren Sie "Add Python to PATH"

---

### Schritt 2: Projektordner erstellen

1. Erstellen Sie einen neuen Ordner für das Projekt:

```cmd
mkdir C:\akademietag_2026\mcp_basics\mcp-demo_ollama
cd C:\akademietag_2026\mcp_basics\mcp-demo_ollama
```

> **Hinweis:** Auf den bereitgestellten Notebooks ist dieser Ordner bereits vorhanden und befüllt.

2. Kopieren Sie die Dateien in den lokalen Ordner [siehe code in diesem Kapitel:](code/)

   | Datei | Aufgabe |
   |---|---|
   | `einfacher_api_call_ollama.py` | Lab 01: Chat mit dem LLM ohne MCP |
   | `mcp_client_ollama.py` | Lab 02: Client mit LLM, nutzt die MCP-Tools |
   | `mcp_server.py` | MCP-Server mit drei Tools |
   | `requirements.txt` | benötigte Bibliotheken (`mcp` 2.x, `ollama`) |

> **Wichtig:** Die Dateien gehören zusammen. Der Server ist für die Bibliothek `mcp` ab Version 2 geschrieben, die `requirements.txt` legt diese Version fest. Werden alte und neue Dateien gemischt, bricht der Server beim Start ab (der Client meldet dann `unhandled errors in a TaskGroup`).

---

### Schritt 3: Ollama und Modell prüfen
#### Ollama Version prüfen

```cmd
ollama --version
```

**Erwartete Ausgabe z. B.:** `ollama version is 0.13.3`

#### Modell überprüfen

```cmd
ollama list
```

**Erwartete Ausgabe:** Sie sollten `qwen2.5-coder:3b` in der Liste sehen

> **Falls das Modell nicht installiert ist:**
> ```cmd
> ollama pull qwen2.5-coder:3b
> ```

#### Ollama starten (falls nicht läuft)

**Option 1 - Hintergrund-Dienst (empfohlen):**
Ollama läuft normalerweise automatisch als Dienst. Prüfen Sie in der Taskleiste ob das Ollama-Icon vorhanden ist.

**Option 2 - Manuell starten:**
```cmd
ollama serve
```
**Hinweis:** Die Fehlermeldung, "Error: listen tcp 127.0.0.1:11434: bind: Normalerweise darf jede Socketadresse (Protokoll, Netzwerkadresse oder Anschluss) nur jeweils einmal verwendet werden, weißt darauf hin, das der Port 11434 bereits von einem anderen Ollama-Prozess belegt ist. Es läuft wahrscheinlich schon eine Instanz von Ollama im Hintergrund.

**Überprüfung mit:**
```cmd
tasklist | findstr ollama
```

> **Wichtig:** Lassen Sie dieses Fenster geöffnet, wenn Sie manuell starten!

#### Test: Ollama funktioniert

Öffnen Sie ein **neues** cmd-Fenster und testen Sie:

```cmd
ollama run qwen2.5-coder:3b
```

**Erwartete Ausgabe:** Das Modell sollte antworten (z.B. "Hallo! Wie kann ich helfen?")

Beenden Sie den Test mit `/bye`



### Schritt 4: Virtuelle Umgebung erstellen

1. Erstellen Sie eine virtuelle Umgebung:

```cmd
python -m venv venv
```

>**Tipp:** Wenn bestimmte Python-Versionen erforderlich sind, dann ist eine Anpassung erforderlich. (z. B. die Benennung der Version aus den vorhandenen python-Versionen mit py -3.11 -m venv venv )

2. Aktivieren Sie die virtuelle Umgebung:

**In cmd (Eingabeaufforderung):**
```cmd
.\venv\Scripts\activate.bat
```

**In PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Erfolg:** Ihr Prompt sollte nun mit `(venv)` beginnen:
```
(venv) C:\MCP-Demo>
```
---

### Schritt 5: Bibliotheken installieren

1. Installieren Sie alle benötigten Bibliotheken:

```cmd
pip install -r requirements.txt
```

**Erwartete Ausgabe:**
```
Successfully installed ... mcp-2.x ... ollama-0.6.x ...
```

2. Überprüfen Sie die Installation:

```cmd
pip list
```

Sie sollten unter anderem sehen:
- `ollama`
- `mcp` in Version **2.x**

> **Prüfen:** `pip show mcp` zeigt die installierte Version. Wird eine Version 1.x angezeigt, führen Sie `pip install -r requirements.txt` erneut aus.

---

# Lab 01: Einfacher API-Call an ein LLM (ohne MCP)

**Hinweis:** Das Sprachmodell läuft lokal in Ollama (qwen2.5-coder:3b).

Testen Sie zunächst die einfache Anfrage an ein LLM
- Rufen Sie das Skript "einfacher_api_call_ollama.py" auf
- Stellen Sie Ihre Frage zum Lagerbestand.
- Stellen Sie anschließend eine Rückfrage, die sich auf die vorherige Antwort bezieht.

```cmd
python einfacher_api_call_ollama.py
```

**Befehle im Chat:**
- `exit` beendet den Chat
- `neu` startet ein neues Gespräch (der bisherige Verlauf wird gelöscht)

> **Beobachtung:** Das Skript zeigt bei jeder Anfrage an, wie viele Nachrichten im Verlauf mitgeschickt werden. Ein Sprachmodell hat kein eigenes Gedächtnis. Der „Dialog“ entsteht nur dadurch, dass der Client bei jeder Frage den gesamten bisherigen Verlauf erneut an das Modell sendet.

# Lab 02: Abfrage des Lagerbestands an LLM mit MCP-Tool

Ohne Kontextbereitstellung wird ein LLM bei der Bestandsabfrage nach Patchkabel keine hilfreiche Antwort geben oder halluzinieren.
Ein MCP (Model Context Protocol) System zur Abfrage des Patchkabel-Lagerbestands mit natürlicher Sprache kann den benötigten Kontext liefern.


```cmd
python mcp_client_ollama.py
```

**Erwartete Ausgabe:**
```
Ollama MCP Netzwerklabor Client gestartet
Modell: qwen2.5-coder:3b
3 Tools verfügbar:
   - patchkabel_bestand_abfragen: Fragt den aktuellen Lagerbestand von Patchkabeln ab...
   - patchkabel_katalog_abfragen: Fragt im Katalog des Lieferanten Preis und Lieferzeit ...
   - laborraum_belegung_abfragen: Prüft, ob ein Laborraum (104 oder 105) an einem Wochentag belegt oder frei ist.

============================================================

Ihre Anfrage (oder 'exit' zum Beenden):
```

Stellen Sie Fragen, für die das LLM jeweils ein **anderes** Tool wählen muss, und achten Sie auf die Zeilen `Führe Tool aus:` und `Parameter:`:

| Testfrage | Erwartetes Tool | Erwartete Parameter |
|---|---|---|
| Wie viele rote Patchkabel haben wir? | `patchkabel_bestand_abfragen` | `{'farbe': 'rot'}` |
| Wie teuer ist eine Nachbestellung grüner Kabel und wie lange dauert die Lieferung? | `patchkabel_katalog_abfragen` | `{'farbe': 'gruen'}` |
| Ist Laborraum 105 am Dienstag belegt? | `laborraum_belegung_abfragen` | `{'raum': '105', 'tag': 'dienstag'}` |
| Was ist ein Patchkabel? | keines | – (das LLM antwortet selbst) |

**Beispiel:**
```
Ihre Anfrage (oder 'exit' zum Beenden): Was kostet ein gelbes Patchkabel beim Lieferanten?

Verarbeite Anfrage...
Führe Tool aus: patchkabel_katalog_abfragen
   Parameter: {'farbe': 'gelb'}
   Ergebnis: Katalog 1m Patchkabel gelb: 1.80 Euro pro Stück, Lieferzeit 5 Werktage

Antwort:
   ...
```

> **Hinweis:** Die Testfragen weichen absichtlich von den Beispielen im System-Prompt des Clients ab, damit das LLM wirklich auswählen muss und nicht nur ein Beispiel wiedererkennt.

> **Beobachtung:** Das LLM sieht nur Name, Beschreibung und Parameter der Tools. Ob es das richtige Tool wählt, hängt stark von diesen Beschreibungen ab. Ein kleines Modell wie qwen2.5-coder:3b kann dabei Bestand und Katalog verwechseln. Probieren Sie Formulierungen aus, bei denen die Wahl eindeutig bzw. mehrdeutig ist (z. B. „Haben wir gelbe Kabel?“).

> **Tipp zur Fehlerbehebung:** Meldet der Client `unhandled errors in a TaskGroup`, ist der MCP-Server beim Start abgebrochen. Der Client zeigt darunter die Ursache an. Starten Sie den Server zur Kontrolle einzeln mit `python mcp_server.py`: Läuft er ohne Meldung, ist er in Ordnung (Beenden mit Strg+C). Häufigste Ursache ist eine alte `mcp_server.py` zusammen mit `mcp` 2.x.

## Aufräumen

Wenn Sie fertig sind, deaktivieren Sie die virtuelle Umgebung:

```cmd
deactivate
```

Ihr Prompt sollte wieder normal aussehen (ohne `(venv)`).

---

## Weitere mögliche Lernaufgaben

- Experimentieren Sie mit verschiedenen Fragen an das System
- Erweitern Sie den Lagerbestand
- Fügen Sie ein weiteres MCP-Tool hinzu (z. B. Bestand an Switches) und prüfen Sie, ob das LLM es auswählt

---

## Zusätzliche Ressourcen

- **Model Context Protocol:** https://modelcontextprotocol.io/
- **Python Virtual Environments:** https://docs.python.org/3/library/venv.html
- **Ollama:** https://ollama.com/
---

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 12/2025, aktualisiert 11/2026 (mcp 2.x, Dialog im einfachen API-Call, drei Tools, nur Ollama)
- Version: v1.2

![line](images/banner.png)
<p align="center">
<a href="02_tool.md"><img src="images/next.png" width="150px"></a>
</p>