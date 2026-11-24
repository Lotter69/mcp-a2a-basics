# MCP- und A2A-Basics

Lernmaterial zum Zusammenspiel von LLM, Werkzeugen und Agenten, am durchgehenden Beispiel eines Patchkabel-Lagerbestands im Netzwerklabor.

| Teil | Frage | Protokoll |
|---|---|---|
| [Teil 1: MCP-Basics](mcp/01_lab.md) | Wie benutzt ein LLM ein **Werkzeug**? | Model Context Protocol (MCP) |
| [Teil 2: A2A-Basics](a2a/01_lab.md) | Wie beauftragt ein Agent einen **anderen Agenten**? | Agent2Agent-Protokoll (A2A) |

```
Teil 1:  Benutzer ──> MCP-Client + LLM ──MCP──> MCP-Server ──> Tool patchkabel_bestand_abfragen

Teil 2:  Benutzer ──> Laborplanungs-Agent + LLM ══A2A══> Lager-Agent ──MCP──> MCP-Server ──> Tool
```

> **Merksatz:** MCP verbindet einen Agenten mit seinen Werkzeugen. A2A verbindet einen Agenten mit einem Kollegen.

## Aufbau

```
mcp-a2a-basics/
├─ README.md
├─ LICENSE
├─ images/              banner.png, next.png, previous.png (gemeinsam für beide Teile)
├─ mcp/                 Teil 1
│  ├─ 01_lab.md … 05_inspector.md
│  └─ code/
└─ a2a/                 Teil 2
   ├─ 01_lab.md … 05_protokoll.md
   └─ code/
      └─ anfragen/      rohe JSON-RPC-Anfragen für Laborübung 2
```

### Teil 1: MCP-Basics

| Kapitel | Art | Inhalt |
|---|---|---|
| [01_lab.md](mcp/01_lab.md) | Hinführung + Labs | Einrichtung, einfacher API-Call ohne MCP, Lagerabfrage mit MCP-Tool |
| [02_tool.md](mcp/02_tool.md) | Sachwissen | Werkzeugkasten des MCP-Servers: Tool-Beschreibung, Tool-Funktion, Handler |
| [03_architecture.md](mcp/03_architecture.md) | Sachwissen | Systemarchitektur mit MCP und LLM, Sequenzdiagramm, Datenfluss |
| [04_client_llm.md](mcp/04_client_llm.md) | Laborübung 1 | LLM-Kommunikation mit Wireshark analysieren |
| [05_inspector.md](mcp/05_inspector.md) | Laborübung 2 | MCP-Kommunikation mit dem MCP Inspector analysieren |

### Teil 2: A2A-Basics

| Kapitel | Art | Inhalt |
|---|---|---|
| [01_lab.md](a2a/01_lab.md) | Hinführung + Labs | Einrichtung, Agent Card (Discovery), Client ohne LLM (Tasks, Rückfrage, Ablehnung, Streaming), zwei Agenten mit LLM |
| [02_agent.md](a2a/02_agent.md) | Sachwissen | Bausteine eines A2A-Agenten: Agent Card, Skills, AgentExecutor, Parts, Artefakte, JSON-RPC-Methoden |
| [03_architecture.md](a2a/03_architecture.md) | Sachwissen | Sequenzdiagramm, Task-Lebenszyklus, Kommunikationsschichten, Werkzeug oder Kollege, Vertrauen |
| [04_wireshark.md](a2a/04_wireshark.md) | Laborübung 1 | A2A-Verkehr mit Wireshark mitschneiden |
| [05_protokoll.md](a2a/05_protokoll.md) | Laborübung 2 | A2A von Hand mit PowerShell und curl.exe (Gegenstück zum Inspector) |

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
| 0:15 | a2a/01_lab: Einrichtung und Lab 01 (Agent Card im Browser) |
| 0:35 | Lab 02 (Client ohne LLM): Zustände selbst auslösen |
| 1:05 | Sachwissen a2a/02_agent: Code des Lager-Agenten lesen |
| 1:25 | Lab 03: zwei Agenten mit LLM |
| 1:45 | Pause |
| 1:55 | a2a/03_architecture: Sequenzdiagramm gemeinsam nachzeichnen, Werkzeug oder Kollege |
| 2:15 | Laborübung 1 (Wireshark) oder Laborübung 2 (PowerShell), je nach Gruppe |
| 2:45 | Reflexion und Transfer, z. B. Klassenfahrt: Ein Planungs-Agent fragt den Buchungsagenten einer Jugendherberge an |

## Lizenz

MIT, siehe [LICENSE](LICENSE).
