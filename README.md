# MCP- und A2A-Basics

Lernmaterial zum Zusammenspiel von LLM, Werkzeugen und Agenten, am durchgehenden Beispiel eines Patchkabel-Lagerbestands im Netzwerklabor.

| Teil | Frage | Protokoll | Start |
|---|---|---|---|
| Teil 1: MCP-Basics | Wie benutzt ein LLM ein **Werkzeug**? | Model Context Protocol (MCP) | [01_lab.md](01_lab.md) |
| Teil 2: A2A-Basics | Wie beauftragt ein Agent einen **anderen Agenten**? | Agent2Agent-Protokoll (A2A) | [06_a2a_lab.md](06_a2a_lab.md) |

```
Teil 1:  Benutzer ──> MCP-Client + LLM ──MCP──> MCP-Server ──> Tool patchkabel_bestand_abfragen

Teil 2:  Benutzer ──> Laborplanungs-Agent + LLM ══A2A══> Lager-Agent ──MCP──> MCP-Server ──> Tool
```

> **Merksatz:** MCP verbindet einen Agenten mit seinen Werkzeugen. A2A verbindet einen Agenten mit einem Kollegen.

## Kapitel

| Nr. | Kapitel | Art | Inhalt |
|---|---|---|---|
| 01 | [Hinführung zu MCP](01_lab.md) | Hinführung + Labs | Einrichtung, einfacher API-Call ohne MCP, Lagerabfrage mit MCP-Tool |
| 02 | [Werkzeugkasten des MCP-Servers](02_tool.md) | Sachwissen | Tool-Beschreibung, Tool-Funktion, Handler |
| 03 | [Systemarchitektur mit MCP und LLM](03_architecture.md) | Sachwissen | Sequenzdiagramm, Datenfluss |
| 04 | [LLM-Kommunikation mit Wireshark](04_client_llm.md) | Laborübung | Mitschnitt Client ↔ Ollama |
| 05 | [MCP-Kommunikation mit dem Inspector](05_inspector.md) | Laborübung | initialize, tools/list, tools/call |
| 06 | [Hinführung zu A2A](06_a2a_lab.md) | Hinführung + Labs | Agent Card (Discovery), Client ohne LLM (Tasks, Rückfrage, Ablehnung, Streaming), zwei Agenten mit LLM |
| 07 | [Bausteine eines A2A-Agenten](07_a2a_agent.md) | Sachwissen | Agent Card, Skills, AgentExecutor, Parts, Artefakte, JSON-RPC-Methoden |
| 08 | [Systemarchitektur mit A2A, MCP und LLM](08_a2a_architecture.md) | Sachwissen | Sequenzdiagramm, Task-Lebenszyklus, Werkzeug oder Kollege, Vertrauen |
| 09 | [A2A-Kommunikation mit Wireshark](09_a2a_wireshark.md) | Laborübung | Discovery, SendMessage, Rückfrage, Streaming, LLM + A2A |
| 10 | [Das A2A-Protokoll von Hand](10_a2a_protokoll.md) | Laborübung | PowerShell und curl.exe als Gegenstück zum Inspector |

## Ordner

| Ordner | Inhalt |
|---|---|
| `code/` | Code zu Teil 1 (MCP) |
| `code_a2a/` | Code zu Teil 2 (A2A), mit eigener `requirements.txt`; `anfragen/` enthält rohe JSON-RPC-Anfragen für Kapitel 10 |
| `images/` | banner.png, next.png, previous.png (für beide Teile) |

## Voraussetzungen und Versionen

- Windows mit PowerShell, Python 3.11 oder höher
- Ollama mit `qwen2.5-coder:3b` (lokal) oder ein Anthropic API Key
- Für die Laborübungen: Wireshark mit Npcap (Loopback), Node.js (MCP Inspector)
- Jeder Teil hat eine eigene `requirements.txt` und eine eigene virtuelle Umgebung
  - Teil 1: `mcp` 2.x, `ollama` 0.6.x
  - Teil 2: `a2a-sdk` 1.3.x (A2A-Spezifikation 1.0), `mcp` 2.x, `uvicorn`, `ollama` 0.6.x

Getestet 11/2026.

## Vorschlag für einen Workshop-Ablauf (Teil 2, ca. 3 Stunden)

| Zeit | Inhalt |
|---|---|
| 0:00 | Rückblick Teil 1: das Werkzeug. Frage: Was ändert sich, wenn das Gegenüber selbst entscheidet? |
| 0:15 | Kapitel 06: Einrichtung und Lab 01 (Agent Card im Browser) |
| 0:35 | Lab 02 (Client ohne LLM): Zustände selbst auslösen |
| 1:05 | Kapitel 07: Code des Lager-Agenten lesen |
| 1:25 | Lab 03: zwei Agenten mit LLM |
| 1:45 | Pause |
| 1:55 | Kapitel 08: Sequenzdiagramm gemeinsam nachzeichnen, Werkzeug oder Kollege |
| 2:15 | Kapitel 09 (Wireshark) oder Kapitel 10 (PowerShell), je nach Gruppe |
| 2:45 | Reflexion und Transfer, z. B. Klassenfahrt: Ein Planungs-Agent fragt den Buchungsagenten einer Jugendherberge an |

## Lizenz

MIT, siehe [LICENSE](LICENSE).
