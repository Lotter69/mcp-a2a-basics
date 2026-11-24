# Änderungen (Merkliste umgesetzt, 24.11.2026)

Diese Datei dient nur zur Übersicht beim Einspielen und kann danach gelöscht werden.

## Einspielen

ZIP im Repo-Root entpacken und vorhandene Dateien überschreiben. Danach im Repo **löschen**:

- `code_a2a/planungs_agent.py` (Anthropic-Variante, entfällt)
- `code_a2a/.env.example` (entfällt)

## Geänderte Dateien aus Teil 1 (MCP-Basics)

| Datei | Änderung |
|---|---|
| `code/mcp_server.py` | zwei neue Tools: `patchkabel_katalog_abfragen` (Preis/Lieferzeit, Farben blau, rot, gelb, gruen, schwarz) und `laborraum_belegung_abfragen` (Raum 104/105, Wochentag). `list_tools()` liefert drei Tools, `call_tool()` mit if/elif. Tool 1 unverändert. |
| `code/mcp_client_ollama.py` | System-Prompt wird aus `tools/list` erzeugt (`system_prompt_erstellen()`), Beispiele für alle drei Tools, Parameter werden allgemein weitergereicht (auch zwei Parameter beim Raum-Tool). Startmeldung jetzt „Ollama MCP Netzwerklabor Client gestartet“, „3 Tools verfügbar“. |
| `01_lab.md` | Anthropic entfernt (Voraussetzungen, Projektordner, API-Key, .env, pip list, Lab-Hinweise, Ressourcen), Schritte neu nummeriert (1 bis 5), Szenario mit Tool-Tabelle, erwartete Ausgabe mit drei Tools, Testfragen zur Tool-Auswahl. |
| `02_tool.md` | Tabelle der drei Tools, neuer Abschnitt „Die beiden weiteren Tools“, `list_tools()` mit drei Tools, `call_tool()` mit if/elif aus dem echten Code, Datenfluss mit Ollama statt Claude-API. |
| `03_architecture.md` | Host im Diagramm = `mcp_client_ollama.py`, `tools/list` mit drei Tools, Hinweis: JSON-Beispiele zeigen natives Tool-Calling einer Provider-API, im Lab Ollama mit JSON im Prompt. „Claude API“ durch „LLM“ ersetzt, Modellname neutral. |
| `04_client_llm.md` | erwartete Ausgabe mit drei Tools, System-Prompt mit Tool-Liste im Mitschnitt, Experiment zur Tool-Auswahl, Reflexionsfrage ohne Claude. |
| `05_inspector.md` | `tools/list`-Antwort mit drei Tools, „Tools (3)“, Katalog- und Raum-Tool im Inspector ausprobieren, Hinweis zu mehreren `tools/call`-Einträgen, neue Reflexionsfrage. |

Unverändert: `code/einfacher_api_call_ollama.py`, `code/requirements.txt`.

## Teil 2 (A2A)

| Datei | Änderung |
|---|---|
| `code_a2a/bestell_agent.py` | **neu**, Port 9998, Skill `material_bestellen`, Tool `patchkabel_katalog_abfragen`, Freigabe ab 50 Euro (INPUT_REQUIRED), Budget 250 Euro (REJECTED), „nein“ → CANCELED |
| `code_a2a/raum_agent.py` | **neu**, Port 9997, Skill `laborraum_buchen`, Tool `laborraum_belegung_abfragen`, Gegenvorschlag (INPUT_REQUIRED), beide belegt → REJECTED |
| `code_a2a/fachagent_hilfen.py` | **neu**, gemeinsamer MCP-Aufruf und Serverstart der Fachagenten |
| `code_a2a/fachagenten_starten.py` | **neu**, startet alle drei Fachagenten in einem Fenster |
| `code_a2a/agenten.json` | **neu**, Basis-URLs der Fachagenten |
| `code_a2a/anfragen/05_bestellung.json`, `06_raum.json` | **neu** für Kapitel 10 |
| `code_a2a/lager_agent.py` | nutzt `fachagent_hilfen.py`, Skill-Beschreibung grenzt sich von Bestellung ab |
| `code_a2a/a2a_verbindung.py` | lädt alle Agent Cards (`agenten_laden()`), `an_agent_delegieren()` statt `an_lager_agent_delegieren()` |
| `code_a2a/a2a_client.py` | Sie sind der Orchestrator: `agent <name>` wechselt den Fachagenten, Erklärung `--stream` vs. `--roh` |
| `code_a2a/planungs_agent_ollama.py` | Orchestrator: System-Prompt aus drei Agent Cards, LLM wählt `{"agent": "lager" / "bestellung" / "raum", ...}` |
| `code_a2a/mcp_server.py` | identisch mit `code/mcp_server.py` (drei Tools) |
| `code_a2a/requirements.txt` | ohne `anthropic` und `python-dotenv` |
| `06_a2a_lab.md` | präzisierter Einstieg (LLM entscheidet Tool und Parameter, Client führt `tools/call` aus), Rollentabelle, Client/Server-Tabelle MCP vs. A2A, Kernerkenntnis-Kasten, Szenario mit drei Fachagenten, Lab 01 mit Start in zwei Fenstern und drei Agent Cards, Lab 02 mit Bestell- und Raum-Aufgaben, Tabelle `--stream` vs. `--roh`, Lab 03 mit Testfragen zur Agentenauswahl, Anthropic entfernt |
| `07_a2a_agent.md` | Teil B/D mit `fachagent_hilfen.py`, `cancel()`, neuer Teil E zu Bestell- und Raumbuchungs-Agent |
| `08_a2a_architecture.md` | Überblick mit drei Fachagenten und Rollen, **Sequenzdiagramm ohne LLM** und **mit LLM** (beide beginnen mit drei Agent Cards), Gegenüberstellung, Zustandstabelle für alle drei Agenten, Ports, Kernerkenntnis |
| `09_a2a_wireshark.md` | Ports 9997–9999, HTTP-Dekodierung für mehrere Ports, drei Discovery-Anfragen und drei TCP-Verbindungen, Freigabe-Rückfrage auf Port 9998, Orchestrator-Mitschnitt mit Auswahl des LLM als Ziel-Port |
| `10_a2a_protokoll.md` | alle drei Agent Cards per PowerShell-Schleife, neuer Schritt 9 (Bestell-Agent mit Freigabe, Raumbuchungs-Agent), Fehler jetzt Schritt 10 |
| `README.md`, `zusatz_fachagenten.md` | Rollen, Ports, Kapitelbeschreibungen, Anthropic entfernt |

## Getestet (Linux-Container, Python 3.13, a2a-sdk 1.3.1, mcp 2.3.0)

- frische venv mit beiden `requirements.txt`
- alle drei Fachagenten: jeder Zustand (COMPLETED, INPUT_REQUIRED, REJECTED, CANCELED), Text- und data-Parts, Streaming
- `a2a_client.py` mit und ohne `--stream`, mit nur einem bzw. keinem laufenden Fachagenten
- `curl` mit allen sechs Dateien in `anfragen/`
- Reihenfolge und Inhalt der HTTP-Anfragen auf dem Loopback mitgeschnitten (3× GET Agent Card, dann POST / an den gewählten Port, dazwischen POST /api/chat)
- `mcp_client_ollama.py` und `planungs_agent_ollama.py` gegen ein **nachgebautes** Ollama (feste Antworten): Toolaufruf mit Parametern, Agentenauswahl, Weitergabe von Rückfragen
- alle Mermaid-Diagramme, alle Links zwischen den Kapiteln

## Nicht getestet

- echtes Ollama mit `qwen2.5-coder:3b` (Tool- und Agentenauswahl des echten Modells)
- Windows, PowerShell-Befehle in Kapitel 10, Wireshark-Oberfläche (Einstellungen, Statistiken → Konversationen)
- MCP Inspector mit drei Tools (Formular mit zwei Pflichtfeldern beim Raum-Tool)
