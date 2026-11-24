# Sachwissen - Bausteine eines A2A-Agenten

![line](../images/banner.png)

## Grundaufbau des Lager-Agenten

In [*MCP-Basics*](../mcp/02_tool.md) bestand ein Tool aus drei Komponenten: Tool-Beschreibung, Beispiel-Argumente und Tool-Funktion. Ein A2A-Agent ist ähnlich aufgebaut, nur eine Ebene höher:

| MCP-Server (Werkzeug) | A2A-Server (Agent) | Aufgabe |
|---|---|---|
| Tool-Beschreibung (`Tool`, `inputSchema`) | **Agent Card** mit **Skills** | Was wird angeboten? |
| Beispiel-Argumente (Kommentar) | `examples` im Skill | Wie könnte ein Auftrag aussehen? |
| Tool-Funktion | **AgentExecutor** | Die eigentliche Logik |
| Handler `list_tools()` / `call_tool()` | **Request Handler** + Routen | Welche Anfrage landet wo? |
| stdio | **HTTP** (Webserver) | Transport |

Die Datei `lager_agent.py` ist entsprechend in vier Abschnitte gegliedert:

1. **Agent Card** - die Visitenkarte
2. **Werkzeug** - der Zugriff auf das MCP-Tool
3. **Agent-Logik** - der AgentExecutor
4. **Server-Setup** - HTTP-Server mit den A2A-Routen

---

## Teil A - Die Agent Card

### 1. Skill-Beschreibung

```python
SKILL_BESTAND = AgentSkill(
    id="bestand_pruefen",
    name="Patchkabel-Bestand prüfen",
    description=(
        "Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager "
        "vorhanden ist, und meldet Bestand und Fehlmenge."
    ),
    tags=["lager", "patchkabel", "netzwerklabor"],
    examples=[
        "Haben wir 30 blaue Patchkabel?",
        "Wie viele rote Patchkabel sind auf Lager?",
        '{"farbe": "blau", "menge": 30}',
    ],
    input_modes=["text/plain", "application/json"],
    output_modes=["text/plain", "application/json"],
)
```

#### Wichtige Elemente:

**`id` und `name`**: Eindeutige Kennung und lesbarer Name des Skills.

**`description`**: Beschreibung für Menschen **und** für LLMs. Der Planungs-Agent baut daraus seinen System-Prompt bzw. seine Tool-Beschreibung. Die Beschreibung entscheidet also mit, ob ein anderes LLM den Agenten sinnvoll beauftragt, genau wie die `description` eines MCP-Tools.

**`examples`**: Beispielaufträge. Sie ersetzen das `inputSchema` von MCP. Ein Skill legt **keine** Parameter fest, sondern zeigt, wie ein Auftrag aussehen kann.

**`input_modes` / `output_modes`**: Welche Inhaltsarten (MIME-Typen) der Skill annimmt und liefert. Hier: Text und JSON.

> **Achtung, Begriff doppelt belegt:** Ein *A2A-Skill* ist eine Fähigkeit, die ein Agent anderen anbietet. Er hat nichts mit den *Agent Skills* (nachladbares Wissen für einen Agenten) zu tun.

### 2. Agent Card

```python
AGENT_CARD = AgentCard(
    name="Lager-Agent Netzwerklabor",
    description="Verwaltet das Materiallager des Netzwerklabors und beantwortet Bestandsanfragen.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",          # Transport: JSON-RPC 2.0 über HTTP
            url=f"http://{HOST}:{PORT}",         # Hierhin schickt der Client seine Anfragen
            protocol_version="1.0",              # A2A-Protokollversion
        )
    ],
    skills=[SKILL_BESTAND],
)
```

| Feld | Bedeutung |
|---|---|
| `name`, `description`, `version` | Wer bin ich? |
| `supported_interfaces` | **Wie** erreicht man mich? Adresse, Transport (`JSONRPC`, `GRPC` oder `HTTP+JSON`) und Protokollversion. Ein Agent kann mehrere Zugänge anbieten. |
| `capabilities` | Welche Protokollfunktionen unterstütze ich? Hier `streaming`. Weitere: `push_notifications` (Rückmeldung an eine hinterlegte Adresse), `extended_agent_card` (ausführlichere Karte nach Anmeldung). |
| `skills` | **Was** kann ich? |
| *(nicht im Beispiel)* `security_schemes`, `security_requirements` | Wie muss man sich anmelden (z. B. API-Key, OAuth 2.0)? |
| *(nicht im Beispiel)* `signatures` | Digitale Signatur der Karte: Stammt sie wirklich vom Betreiber? |

> **Hinweis:** In Python heißen die Felder `supported_interfaces`, im JSON auf der Leitung `supportedInterfaces`. Das SDK übersetzt automatisch zwischen beiden Schreibweisen.

---

## Teil B - Das Werkzeug (MCP im Inneren)

```python
async def mcp_bestand_abfragen(farbe: str) -> str:
    """Startet mcp_server.py über stdio und ruft das Tool patchkabel_bestand_abfragen auf."""
    params = StdioServerParameters(command=sys.executable, args=[str(MCP_SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("patchkabel_bestand_abfragen", {"farbe": farbe})
            return result.content[0].text
```

**Beobachten Sie:** Der Lager-Agent ist hier **MCP-Client**. Er tut genau das, was in [*MCP-Basics*](../mcp/03_architecture.md) `mcp_client_ollama.py` getan hat: Server starten, `initialize`, `tools/call`. Der `mcp_server.py` ist unverändert.

Der entscheidende Unterschied: Diese Funktion ist **privat**. Sie steht in keiner Agent Card, und der Planungs-Agent erfährt nicht, dass es sie gibt. Der Lager-Agent könnte sie morgen durch eine Datenbankabfrage ersetzen, ohne dass sich für seine Auftraggeber etwas ändert.

---

## Teil C - Die Agent-Logik (AgentExecutor)

**Definition:** Der *AgentExecutor* ist die Klasse, in der die Logik des Agenten steht. Das SDK ruft seine Methode `execute()` für **jede** eingehende Nachricht auf. Der Executor antwortet nicht mit einem Rückgabewert, sondern legt **Ereignisse** in eine Warteschlange (`event_queue`): neue Aufgabe, Zustandswechsel, Artefakt. Das SDK macht daraus die Antwort an den Client (bei Streaming: viele einzelne Ereignisse).

### 1. Aufgabe holen oder anlegen

```python
if context.current_task:                       # Folgenachricht zu einer bestehenden Aufgabe
    task = context.current_task
else:                                          # Neue Aufgabe -> Zustand SUBMITTED
    task = new_task_from_user_message(context.message)
    await event_queue.enqueue_event(task)

updater = TaskUpdater(event_queue, task.id, task.context_id)
```

- Schickt der Client eine Nachricht **ohne** Task-ID, entsteht eine neue Aufgabe.
- Schickt er eine Nachricht **mit** Task-ID (Antwort auf eine Rückfrage), liefert das SDK die bestehende Aufgabe samt Verlauf in `context.current_task`.
- Der `TaskUpdater` ist ein Helfer, der Zustandswechsel und Artefakte als Ereignisse in die Warteschlange legt.

### 2. Zustände melden

```python
await updater.start_work(...)       # -> TASK_STATE_WORKING
await updater.requires_input(...)   # -> TASK_STATE_INPUT_REQUIRED  (Rückfrage, Aufgabe pausiert)
await updater.reject(...)           # -> TASK_STATE_REJECTED        (Auftrag wird nicht angenommen)
await updater.complete(...)         # -> TASK_STATE_COMPLETED       (erledigt)
```

Jeder Aufruf erhält optional eine **Nachricht** (z. B. die Rückfrage „Welche Farbe wird benötigt?“). Nach `requires_input` kehrt `execute()` zurück. Die Aufgabe wartet, bis der Client mit derselben Task-ID antwortet. Dann ruft das SDK `execute()` erneut auf.

### 3. Den Auftrag verstehen

```python
for nachricht in nachrichten:
    for daten in get_data_parts(nachricht.parts):     # a) strukturierte Daten
        ...
    text = " ".join(get_text_parts(nachricht.parts))  # b) freier Text
    ...
```

Eine Nachricht besteht aus **Parts**. Der Lager-Agent wertet zwei Arten aus:

| Part | JSON auf der Leitung | Beispiel |
|---|---|---|
| Text | `{"text": "..."}` | `{"text": "Haben wir 30 blaue Patchkabel?"}` |
| Daten | `{"data": {...}}` | `{"data": {"farbe": "rot", "menge": 40}}` |
| Datei (Inhalt) | `{"raw": "<base64>", "filename": "..."}` | z. B. eine Bestellliste als PDF |
| Datei (Verweis) | `{"url": "https://..."}` | Link auf ein Dokument |

Der Lager-Agent benutzt hier **einfache Regeln** (Schlüsselwörter, erste Zahl) statt eines LLM. Das reicht für das Beispiel und macht das Verhalten vorhersagbar. Für den Planungs-Agenten ist das nicht erkennbar: Ob hinter einer Agent Card ein großes Sprachmodell, ein kleines oder ein einfaches Programm steckt, bleibt verborgen.

### 4. Ergebnis als Artefakt liefern

```python
await updater.add_artifact(
    name="bestandsauskunft",
    parts=[
        new_text_part(zusammenfassung, media_type="text/plain"),
        new_data_part(ergebnis, media_type="application/json"),
    ],
)
await updater.complete(new_text_message("Bestandsprüfung abgeschlossen.", ...))
```

**Artefakte** sind die **Ergebnisse** einer Aufgabe. Sie sind getrennt vom Gesprächsverlauf: Die Statusnachricht „Bestandsprüfung abgeschlossen.“ ist Kommunikation, die Bestandsauskunft ist das Arbeitsergebnis. Ein Artefakt kann mehrere Parts haben, hier einen Text für Menschen und strukturierte Daten für Programme.

> **Hinweis:** Zahlen in einem data-Part kommen beim Empfänger als Kommazahl an (`45.0`). Das liegt am internen Datenformat des SDK (Protocol Buffers). `a2a_verbindung.py` glättet das für die Anzeige.

---

## Teil D - Das Server-Setup

```python
request_handler = DefaultRequestHandler(
    agent_executor=LagerAgentExecutor(),     # unsere Agent-Logik
    task_store=InMemoryTaskStore(),          # merkt sich alle Tasks (nur im Arbeitsspeicher)
    agent_card=AGENT_CARD,
)
routes = []
routes.extend(create_agent_card_routes(AGENT_CARD))         # GET  /.well-known/agent-card.json
routes.extend(create_jsonrpc_routes(request_handler, "/"))  # POST /  (JSON-RPC)
app = Starlette(routes=routes)
uvicorn.run(app, host="127.0.0.1", port=9999)
```

### Genutzte A2A-Methoden (JSON-RPC)

Ähnlich wie die MCP-Handler gibt es für jede Anfrage des Clients eine Methode. Der `DefaultRequestHandler` des SDK übernimmt sie, ruft bei Bedarf den AgentExecutor auf und verwaltet die Tasks im `task_store`.

| Anfrage des Clients | HTTP | Was passiert |
|---|---|---|
| Agent Card abrufen | `GET /.well-known/agent-card.json` | Discovery, liefert die Agent Card |
| `SendMessage` | `POST /` | Nachricht senden, Antwort: Task (oder direkte Message) |
| `SendStreamingMessage` | `POST /` | wie oben, Antwort als Ereignisstrom (Server-Sent Events) |
| `GetTask` | `POST /` | aktuellen Stand einer Aufgabe abfragen (Polling) |
| `ListTasks` | `POST /` | alle Aufgaben auflisten |
| `CancelTask` | `POST /` | Aufgabe abbrechen (hier nicht unterstützt) |
| `SubscribeToTask` | `POST /` | sich erneut an den Ereignisstrom einer Aufgabe hängen |
| `CreateTaskPushNotificationConfig` u. a. | `POST /` | Rückmeldeadresse für Push-Benachrichtigungen hinterlegen |

Alle JSON-RPC-Anfragen gehen an **dieselbe** Adresse. Welche Methode gemeint ist, steht im Feld `method` des JSON. Zusätzlich muss der Client im HTTP-Header `A2A-Version: 1.0` mitschicken.

---

## Zusammenfassung

Ein A2A-Agent besteht aus:

1. **Agent Card** (JSON) - Wer bin ich, was kann ich, wie erreicht man mich?
2. **AgentExecutor** (Python) - Wie bearbeite ich Aufträge? Welche Zustände melde ich?
3. **Server** (HTTP) - Discovery-Adresse und JSON-RPC-Endpunkt

Was er intern benutzt (hier ein MCP-Tool), gehört **nicht** zur Schnittstelle.

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.0

![line](../images/banner.png)
<p align="center">
<a href="01_lab.md"><img src="../images/previous.png" width="150px"></a>
<a href="03_architecture.md"><img src="../images/next.png" width="150px"></a>
</p>
