# Sachwissen - Bausteine eines A2A-Agenten

![line](images/banner.png)

## Grundaufbau eines Fachagenten

Dieses Kapitel zeigt den Aufbau eines **Fachagenten** am Beispiel des Lager-Agenten. Bestell-Agent und Raumbuchungs-Agent sind nach demselben Muster gebaut (siehe Teil E).

In [*MCP-Basics*](02_tool.md) bestand ein Tool aus drei Komponenten: Tool-Beschreibung, Beispiel-Argumente und Tool-Funktion. Ein A2A-Agent ist ähnlich aufgebaut, nur eine Ebene höher:

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

Was alle drei Fachagenten gleich machen (MCP-Tool aufrufen, Server starten), steht in der gemeinsamen Datei `fachagent_hilfen.py`. In den Agenten-Dateien bleibt nur, was den jeweiligen Fachagenten ausmacht: Agent Card, Regeln, Zustände.

---

## Teil A - Die Agent Card

### 1. Skill-Beschreibung

```python
SKILL_BESTAND = AgentSkill(
    id="bestand_pruefen",
    name="Patchkabel-Bestand prüfen",
    description=(
        "Prüft, ob eine gewünschte Anzahl Patchkabel (1 m, blau oder rot) im Lager "
        "VORHANDEN ist, und meldet Bestand und Fehlmenge. Bestellt nichts."
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

**`description`**: Beschreibung für Menschen **und** für LLMs. Der Orchestrator baut daraus seinen System-Prompt. Die Beschreibung entscheidet also mit, ob ein LLM den **richtigen** Fachagenten beauftragt, genau wie die `description` eines MCP-Tools über die Tool-Auswahl entscheidet. Deshalb grenzen sich die Skills ausdrücklich voneinander ab: Der Lager-Agent prüft, was **VORHANDEN** ist, und „bestellt nichts“. Der Bestell-Agent bestellt **NACH** und „prüft KEINEN Lagerbestand“.

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

Der Lager-Agent ruft sein Werkzeug über eine kurze Funktion auf:

```python
async def mcp_bestand_abfragen(farbe: str) -> str:
    """Ruft das Tool patchkabel_bestand_abfragen des MCP-Servers auf."""
    return await mcp_tool_aufrufen("patchkabel_bestand_abfragen", {"farbe": farbe})
```

Die eigentliche MCP-Arbeit steckt in `fachagent_hilfen.py` und wird von allen drei Fachagenten benutzt:

```python
async def mcp_tool_aufrufen(tool_name: str, argumente: dict) -> str:
    """Startet mcp_server.py über stdio, ruft ein Tool auf und gibt dessen Text zurück."""
    params = StdioServerParameters(command=sys.executable, args=[str(MCP_SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"   [MCP]  tools/call {tool_name} {argumente}")
            result = await session.call_tool(tool_name, argumente)
            text = result.content[0].text
            print(f"   [MCP]  Ergebnis: {text.splitlines()[0]}")
            return text
```

**Beobachten Sie:** Der Fachagent ist hier **MCP-Client**. Er tut genau das, was in [*MCP-Basics*](03_architecture.md) `mcp_client_ollama.py` getan hat: Server starten, `initialize`, `tools/call`. Der `mcp_server.py` ist derselbe wie in Teil 1.

Ein Unterschied zu Teil 1: Dort hat das **LLM** entschieden, welches der drei Tools aufgerufen wird. Hier steht das Tool **fest im Programm** des Fachagenten. Jeder Fachagent benutzt genau das Werkzeug, das zu seinem Fachgebiet gehört.

Der entscheidende Unterschied zu A2A: Diese Funktion ist **privat**. Sie steht in keiner Agent Card, und der Orchestrator erfährt nicht, dass es sie gibt. Der Lager-Agent könnte sie morgen durch eine Datenbankabfrage ersetzen, ohne dass sich für seine Auftraggeber etwas ändert.

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
await updater.cancel(...)           # -> TASK_STATE_CANCELED        (abgebrochen, z. B. Freigabe verweigert)
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

Der Lager-Agent benutzt hier **einfache Regeln** (Schlüsselwörter, erste Zahl) statt eines LLM. Das reicht für das Beispiel und macht das Verhalten vorhersagbar. Für den Orchestrator ist das nicht erkennbar: Ob hinter einer Agent Card ein großes Sprachmodell, ein kleines oder ein einfaches Programm steckt, bleibt verborgen.

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

Gestartet wird jeder Fachagent mit einer Zeile:

```python
if __name__ == "__main__":
    agent_starten(AGENT_CARD, LagerAgentExecutor(), HOST, PORT)   # PORT = 9999
```

Die Funktion `agent_starten()` in `fachagent_hilfen.py` baut den Webserver:

```python
request_handler = DefaultRequestHandler(
    agent_executor=executor,                 # die Agent-Logik, z. B. LagerAgentExecutor()
    task_store=InMemoryTaskStore(),          # merkt sich alle Tasks (nur im Arbeitsspeicher)
    agent_card=agent_card,
)
routes = []
routes.extend(create_agent_card_routes(agent_card))         # GET  /.well-known/agent-card.json
routes.extend(create_jsonrpc_routes(request_handler, "/"))  # POST /  (JSON-RPC)
uvicorn.run(Starlette(routes=routes), host=host, port=port, log_level="warning")
```

Jeder Fachagent ist ein **eigener Webserver** mit eigenem Port. Deshalb kann jeder für sich gestartet, beendet oder auf einen anderen Rechner verlegt werden. `fachagenten_starten.py` startet die drei Programme nur bequem in einem Fenster.

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

## Teil E - Die beiden weiteren Fachagenten

Bestell-Agent und Raumbuchungs-Agent sind genauso aufgebaut wie der Lager-Agent. Sie unterscheiden sich in Agent Card, Werkzeug und **Regeln**:

| | Lager-Agent | Bestell-Agent | Raumbuchungs-Agent |
|---|---|---|---|
| Datei, Port | `lager_agent.py`, 9999 | `bestell_agent.py`, 9998 | `raum_agent.py`, 9997 |
| Skill (`id`) | `bestand_pruefen` | `material_bestellen` | `laborraum_buchen` |
| Werkzeug (MCP-Tool) | `patchkabel_bestand_abfragen` | `patchkabel_katalog_abfragen` | `laborraum_belegung_abfragen` (für beide Räume) |
| Artefakt | `bestandsauskunft` | `bestellbestaetigung` | `reservierung` |
| `INPUT_REQUIRED` | Farbe fehlt, Menge fehlt | Farbe oder Menge fehlt; **Freigabe** ab 50 Euro | Wochentag fehlt; **Gegenvorschlag**, wenn der Wunschraum belegt ist |
| `REJECTED` | Farbe nicht im Lager | Farbe nicht beim Lieferanten; über **Budget** von 250 Euro | beide Räume belegt |
| `CANCELED` | – | Freigabe mit „nein“ verweigert | Gegenvorschlag mit „nein“ abgelehnt |

Ausschnitt aus der Logik des Bestell-Agenten (eigene Regeln nach dem Werkzeugaufruf):

```python
# Werkzeug: Preis und Lieferzeit beim Lieferanten
katalog = katalog_lesen(await mcp_tool_aufrufen("patchkabel_katalog_abfragen",
                                                {"farbe": auftrag["farbe"]}))
preis, lieferzeit = katalog
summe = round(preis * auftrag["menge"], 2)

# Eigene Regeln: Budget und Freigabe
if summe > BUDGET_EURO:                                      # 250 Euro
    await updater.reject(nachricht("... überschreitet das Budget von 250 Euro."))
    return
if summe > FREIGABE_AB_EURO and auftrag["freigabe"] is None: # 50 Euro
    await updater.requires_input(nachricht("... Freigeben? (ja/nein)"))
    return
if auftrag["freigabe"] is False:
    await updater.cancel(nachricht("Bestellung nicht freigegeben, Vorgang abgebrochen."))
    return
```

**Beobachten Sie:**
- Die Regeln (Budget, Freigabe) gehören dem **Fachagenten**. Der Orchestrator kennt sie nicht und muss sie nicht kennen. Er erfährt nur das Ergebnis: erledigt, Rückfrage, abgelehnt oder abgebrochen.
- Der Raumbuchungs-Agent ruft sein Werkzeug bei Bedarf **zweimal** auf (Wunschraum und anderer Raum), bevor er antwortet. Auch das bleibt für den Auftraggeber unsichtbar.
- Der Raumbuchungs-Agent merkt sich seine Reservierungen im Arbeitsspeicher. Nach einem Neustart sind sie weg.

---

## Zusammenfassung

Ein A2A-Agent besteht aus:

1. **Agent Card** (JSON) - Wer bin ich, was kann ich, wie erreicht man mich?
2. **AgentExecutor** (Python) - Wie bearbeite ich Aufträge? Welche Zustände melde ich?
3. **Server** (HTTP) - Discovery-Adresse und JSON-RPC-Endpunkt

Was er intern benutzt (hier ein MCP-Tool) und nach welchen Regeln er entscheidet, gehört **nicht** zur Schnittstelle.

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.1 (drei Fachagenten, gemeinsame Hilfen)

![line](images/banner.png)
<p align="center">
<a href="06_a2a_lab.md"><img src="images/previous.png" width="150px"></a>
<a href="08_a2a_architecture.md"><img src="images/next.png" width="150px"></a>
</p>
