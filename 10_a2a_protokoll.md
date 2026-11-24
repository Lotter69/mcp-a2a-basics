# Laborübung 2: Das A2A-Protokoll von Hand (PowerShell)

![line](images/banner.png)

## Lernziele

Nach Abschluss dieser Laborübung können Sie:

- Die Agent Cards mehrerer A2A-Server (Fachagenten) ohne SDK abrufen und auswerten
- JSON-RPC-Anfragen an einen A2A-Agenten selbst formulieren und senden (`SendMessage`, `GetTask`, `ListTasks`, `SendStreamingMessage`)
- Eine Rückfrage (`INPUT_REQUIRED`) durch eine Folgenachricht mit `taskId` beantworten
- Text-Parts und data-Parts gezielt einsetzen
- Verschiedene Fachagenten nur über ihre Adresse (Port) ansprechen
- Fehlermeldungen des Protokolls lesen und ihre Ursache zuordnen

In [*MCP-Basics*](05_inspector.md) hat der MCP Inspector die Rolle des Clients übernommen. Hier sind **Sie** der A2A-Client und damit der Orchestrator: Sie schreiben die Nachrichten, die sonst `a2a_client.py` oder der Laborplanungs-Agent erzeugen. So wird sichtbar, dass hinter A2A nur HTTP und JSON stecken.

---

## Voraussetzungen

### Software
- PowerShell (Windows PowerShell 5.1 oder PowerShell 7)
- `curl.exe` (in Windows 10/11 enthalten)
- Projektordner mit dem Unterordner `anfragen\` [siehe Hinführung zu A2A](06_a2a_lab.md)

### Vorbereitung

**Fenster 1:** Alle drei Fachagenten starten
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
.\venv\Scripts\Activate.ps1
python fachagenten_starten.py
```

| Fachagent | Adresse |
|---|---|
| Lager-Agent | `http://127.0.0.1:9999` |
| Bestell-Agent | `http://127.0.0.1:9998` |
| Raumbuchungs-Agent | `http://127.0.0.1:9997` |

Die Schritte 1 bis 8 arbeiten mit dem Lager-Agenten, Schritt 9 mit den beiden anderen.

**Fenster 2:** In den Projektordner wechseln (venv nicht nötig, Sie benutzen nur PowerShell)
```powershell
cd C:\akademietag_2026\a2a_basics\a2a-demo
Get-ChildItem .\anfragen
# 01_send_message.json, 02_rueckfrage_ausloesen.json, 03_data_part.json, 04_streaming.json  (Lager-Agent)
# 05_bestellung.json  (Bestell-Agent), 06_raum.json  (Raumbuchungs-Agent)
```

> **Hinweis zu Umlauten:** Windows PowerShell 5.1 liest Antworten ohne Zeichensatzangabe als ISO-8859-1. Aus „prüft“ wird dann „prÃ¼ft“. Übertragen wird korrekt in UTF-8, nur die Anzeige ist falsch. Mit PowerShell 7 (`pwsh`) erscheinen die Umlaute richtig.

---

## Aufgaben

### Schritt 1: Agent Card abrufen (Discovery)

**Aktion:**
```powershell
$card = Invoke-RestMethod http://127.0.0.1:9999/.well-known/agent-card.json
$card.name
$card.supportedInterfaces
$card.skills | Format-List id, name, description, examples
```

**Erwartetes Ergebnis:**
```
Lager-Agent Netzwerklabor

url                   protocolBinding protocolVersion
---                   --------------- ---------------
http://127.0.0.1:9999 JSONRPC         1.0
...
```

**Beobachten Sie:** Aus `supportedInterfaces` lesen Sie ab, **wohin** (`url`), **wie** (`JSONRPC`) und **in welcher Version** (`1.0`) Sie Aufträge senden. Genau das macht das SDK automatisch.

**Alle drei Agent Cards auf einmal** (so wie es `a2a_client.py` und der Orchestrator beim Start tun):
```powershell
$agenten = Get-Content .\agenten.json -Raw | ConvertFrom-Json
foreach ($a in $agenten.PSObject.Properties) {
    $c = Invoke-RestMethod "$($a.Value)/.well-known/agent-card.json"
    "{0,-11} {1,-34} {2}" -f $a.Name, $c.name, $c.skills[0].id
}
```

**Erwartetes Ergebnis:**
```
lager       Lager-Agent Netzwerklabor          bestand_pruefen
bestellung  Bestell-Agent Netzwerklabor        material_bestellen
raum        Raumbuchungs-Agent Netzwerklabor   laborraum_buchen
```

`agenten.json` enthält nur die **Basis-URL** jedes Fachagenten. Alles andere steht in der Agent Card.

---

### Schritt 2: Erster Auftrag (SendMessage)

Sehen Sie sich zuerst die Anfrage an:
```powershell
Get-Content .\anfragen\01_send_message.json
```
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "messageId": "msg-001",
      "parts": [
        { "text": "Haben wir 30 blaue Patchkabel?" }
      ]
    }
  }
}
```

**Aktion:**
```powershell
$h = @{ "A2A-Version" = "1.0" }
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\01_send_message.json

$r.result.task.status.state
$r.result.task.artifacts[0].parts
```

**Erwartetes Ergebnis:**
```
TASK_STATE_COMPLETED

text                                                 mediaType        data
----                                                 ---------        ----
30 Stück angefragt, 45 Stück auf Lager: ausreichend. text/plain
                                                     application/json @{farbe=blau; bestand=45.0; ...}
```

Die vollständige Antwort zeigt:
```powershell
$r | ConvertTo-Json -Depth 20
```

**Beobachten Sie:**
- `messageId` vergibt der **Absender**. Jede Nachricht hat eine eigene ID.
- Die Task-ID (`$r.result.task.id`) vergibt der **Lager-Agent**.
- Fenster 1 zeigt den MCP-Aufruf. In der Antwort taucht er nicht auf.

---

### Schritt 3: Was passiert ohne Versionsangabe?

**Aktion:** dieselbe Anfrage ohne `-Headers $h`
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\01_send_message.json
$r.error
```

**Erwartetes Ergebnis:**
```
code    message
----    -------
-32009  A2A version '0.3' is not supported by this handler. Expected version '1.0'.
```

**Beobachten Sie:**
- Fehlt der Header, nimmt der Server die ältere Version 0.3 an und lehnt ab.
- Fehler kommen bei JSON-RPC **nicht** als HTTP-Fehlercode, sondern als Feld `error` in einer Antwort mit HTTP-Status 200. Das kennen Sie von MCP.

---

### Schritt 4: Rückfrage auslösen

**Aktion:**
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\02_rueckfrage_ausloesen.json
$task = $r.result.task
$task.status.state
$task.status.message.parts.text
$task.id
```

**Erwartetes Ergebnis:**
```
TASK_STATE_INPUT_REQUIRED
Welche Farbe wird benötigt? Im Sortiment sind blau und rot (oder 'gesamt').
449e9372-...
```

Die Aufgabe ist **pausiert**. Der Lager-Agent wartet auf eine Antwort, die zu **dieser** Task-ID gehört.

---

### Schritt 5: Rückfrage beantworten (Folgenachricht mit taskId)

Diesmal bauen Sie die Nachricht direkt in PowerShell, weil `taskId` und `contextId` aus der vorigen Antwort stammen.

**Aktion:**
```powershell
$body = @{
  jsonrpc = "2.0"
  id      = 5
  method  = "SendMessage"
  params  = @{
    message = @{
      role      = "ROLE_USER"
      messageId = [guid]::NewGuid().ToString()
      taskId    = $task.id
      contextId = $task.contextId
      parts     = @( @{ text = "rot" } )
    }
  }
} | ConvertTo-Json -Depth 10

$body      # zur Kontrolle anzeigen

$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -Body $body
$r.result.task.status.state
$r.result.task.artifacts[0].parts[0].text
```

**Erwartetes Ergebnis:**
```
TASK_STATE_COMPLETED
50 Stück angefragt, 32 Stück auf Lager: es fehlen 18 Stück.
```

**Beobachten Sie:**
- Ohne `taskId` wäre „rot“ eine **neue** Aufgabe: Der Lager-Agent meldet dann nur den Bestand roter Kabel, ohne Bezug zu den 50 Stück, und die erste Aufgabe bleibt im Zustand `INPUT_REQUIRED` liegen (probieren Sie es aus).
- Der Lager-Agent hat die Menge 50 aus der **ersten** Nachricht und die Farbe aus der **zweiten** kombiniert. Den Verlauf hat er selbst gespeichert.

---

### Schritt 6: Aufgabe nachträglich abfragen (GetTask)

**Aktion:**
```powershell
$body = @{ jsonrpc = "2.0"; id = 6; method = "GetTask"; params = @{ id = $task.id } } | ConvertTo-Json -Depth 10
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -Body $body

$r.result.status.state
$r.result.history | ForEach-Object { "{0,-11} {1}" -f $_.role, $_.parts[0].text }
```

**Erwartetes Ergebnis:**
```
TASK_STATE_COMPLETED
ROLE_USER   Ich brauche 50 Patchkabel
ROLE_AGENT  Lager-Agent prüft die Anfrage ...
ROLE_AGENT  Welche Farbe wird benötigt? Im Sortiment sind blau und rot (oder 'gesamt').
ROLE_USER   rot
ROLE_AGENT  Lager-Agent prüft die Anfrage ...
```

**Beobachten Sie:**
- Mit `GetTask` kann ein Client den Stand einer Aufgabe **jederzeit** abfragen. Bei langen Aufgaben ist das die einfachste Form des Wartens (**Polling**).
- `history` enthält den gesamten Dialog zur Aufgabe, `artifacts` die Ergebnisse.

**Zusatz:** Alle Aufgaben des Lager-Agenten auflisten:
```powershell
$body = @{ jsonrpc = "2.0"; id = 7; method = "ListTasks"; params = @{} } | ConvertTo-Json
(Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
   -ContentType "application/json; charset=utf-8" -Body $body).result.tasks |
   ForEach-Object { "{0}  {1}" -f $_.id.Substring(0,8), $_.status.state }
```

---

### Schritt 7: Strukturierte Daten senden (data-Part)

```powershell
Get-Content .\anfragen\03_data_part.json
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\03_data_part.json
$r.result.task.artifacts[0].parts[1].data
```

**Anfrage (Ausschnitt):**
```json
"parts": [
  { "data": { "farbe": "rot", "menge": 40 }, "mediaType": "application/json" }
]
```

**Erwartetes Ergebnis:**
```
farbe       : rot
bestand     : 32.0
angefragt   : 40.0
ausreichend : False
fehlmenge   : 8.0
laenge_m    : 1.0
```

**Beobachten Sie:** Ein Part ist entweder `text`, `data`, `raw` (Dateiinhalt) oder `url` (Verweis). Strukturierte Daten machen den Auftrag eindeutig, weil der Empfänger nichts interpretieren muss. Die Zahlen kommen als Kommazahl zurück (`32.0`), weil das SDK alle Zahlen in data-Parts so speichert.

---

### Schritt 8: Streaming beobachten (SendStreamingMessage)

`Invoke-RestMethod` wartet, bis die Antwort vollständig ist. Für einen Ereignisstrom eignet sich `curl.exe` besser.

> **Wichtig:** In Windows PowerShell 5.1 ist `curl` ein Alias für `Invoke-WebRequest`. Schreiben Sie deshalb ausdrücklich **`curl.exe`**.

**Aktion:**
```powershell
curl.exe -N -H "Content-Type: application/json" -H "A2A-Version: 1.0" `
         --data-binary "@anfragen\04_streaming.json" http://127.0.0.1:9999/
```

**Erwartetes Ergebnis:** vier Zeilen, die nacheinander erscheinen (zwischen der zweiten und dritten liegt etwa eine Sekunde):
```
data: {"result": {"task": {... "status": {"state": "TASK_STATE_SUBMITTED"} ...}}, "id": 4, "jsonrpc": "2.0"}

data: {"result": {"statusUpdate": {... "state": "TASK_STATE_WORKING" ...}}, "id": 4, "jsonrpc": "2.0"}

data: {"result": {"artifactUpdate": {... "name": "bestandsauskunft" ...}}, "id": 4, "jsonrpc": "2.0"}

data: {"result": {"statusUpdate": {... "state": "TASK_STATE_COMPLETED" ...}}, "id": 4, "jsonrpc": "2.0"}
```

**Beobachten Sie:**
- `-N` schaltet die Pufferung ab, damit Sie jedes Ereignis sofort sehen.
- Alle Ereignisse tragen dieselbe JSON-RPC-`id` 4: Sie gehören zu **einer** Anfrage.
- Ohne Streaming hätten Sie nur den Endzustand gesehen.

---

### Schritt 9: Die beiden anderen Fachagenten beauftragen

Die Anfragen an die anderen Fachagenten sehen genauso aus. Es ändert sich nur die **Adresse**.

**a) Bestell-Agent (Port 9998) mit Freigabe:**
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9998/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\05_bestellung.json
$task = $r.result.task
$task.status.state
$task.status.message.parts.text
```

**Erwartetes Ergebnis:**
```
TASK_STATE_INPUT_REQUIRED
Die Bestellung über 50 gelbe Patchkabel kostet 90.00 Euro. Bestellungen über 50 Euro brauchen eine Freigabe. Freigeben? (ja/nein)
```

Freigabe erteilen, mit demselben Aufbau wie in Schritt 5, aber an Port **9998**:
```powershell
$body = @{
  jsonrpc = "2.0"; id = 8; method = "SendMessage"
  params  = @{ message = @{
      role = "ROLE_USER"; messageId = [guid]::NewGuid().ToString()
      taskId = $task.id; contextId = $task.contextId
      parts = @( @{ text = "ja" } ) } }
} | ConvertTo-Json -Depth 10
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9998/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -Body $body
$r.result.task.status.state
$r.result.task.artifacts[0].parts[0].text
```

**Erwartetes Ergebnis:**
```
TASK_STATE_COMPLETED
Bestellt: 50 x gelb für 90.00 Euro, Lieferung in 5 Werktagen.
```

Wiederholen Sie die Anfrage `05_bestellung.json` und antworten Sie mit `nein`. Erwartet: `TASK_STATE_CANCELED`.

**b) Raumbuchungs-Agent (Port 9997) mit Gegenvorschlag:**
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9997/ -Headers $h `
       -ContentType "application/json; charset=utf-8" -InFile .\anfragen\06_raum.json
$r.result.task.status.state
$r.result.task.status.message.parts.text
```

**Erwartetes Ergebnis** (frisch gestarteter Raumbuchungs-Agent):
```
TASK_STATE_INPUT_REQUIRED
Raum 104 ist am Donnerstag belegt. Raum 105 ist frei. Soll ich Raum 105 reservieren? (ja/nein)
```

> **Hinweis:** Der Raumbuchungs-Agent merkt sich Reservierungen, solange er läuft. Haben Sie Raum 105 für Donnerstag schon in einer früheren Übung reserviert, lautet die Antwort `TASK_STATE_REJECTED` („Am Donnerstag sind beide Laborräume belegt.“). Ein Neustart von `fachagenten_starten.py` setzt die Reservierungen zurück.

**Beobachten Sie:**
- Methode, Header und Aufbau der Nachricht sind bei allen drei Fachagenten **gleich**. Welcher Fachagent den Auftrag bekommt, entscheidet allein die **Adresse**.
- Welche Regeln gelten (Freigabe ab 50 Euro, Gegenvorschlag), steht in keiner Anfrage. Das entscheidet jeder Fachagent selbst.

---

### Schritt 10: Fehler lesen

Probieren Sie die folgenden fehlerhaften Anfragen aus und ordnen Sie die Fehlercodes zu.

**a) Unbekannte Task-ID:**
```powershell
$body = @{ jsonrpc = "2.0"; id = 9; method = "GetTask"; params = @{ id = "gibt-es-nicht" } } | ConvertTo-Json
(Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h -ContentType "application/json" -Body $body).error
```

**b) Methodenname aus A2A 0.3:**
```powershell
$body = @{ jsonrpc = "2.0"; id = 10; method = "message/send"; params = @{} } | ConvertTo-Json
(Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9999/ -Headers $h -ContentType "application/json" -Body $body).error
```

| Fehler | Code | Ursache |
|---|---|---|
| Version fehlt (Schritt 3) | `-32009` | Header `A2A-Version` fehlt oder passt nicht |
| Task not found | `-32001` | Die Task-ID ist dem Agenten unbekannt (z. B. nach Neustart, da die Tasks nur im Arbeitsspeicher liegen) |
| Method not found | `-32601` | Methodenname unbekannt. `message/send` war der Name in A2A 0.3, seit 1.0 heißt es `SendMessage` |

---

## Reflexionsfragen

- Welche Informationen muss ein Client mindestens kennen, um einen A2A-Agenten zu beauftragen?

- Woran erkennt ein Fachagent, dass eine Anfrage für ihn bestimmt ist? Was müsste ein Orchestrator tun, um einen vierten Fachagenten zu nutzen?

- Was ist der Unterschied zwischen `messageId`, `taskId` und `contextId`? Wer vergibt welche ID?

- Warum liefert der Lager-Agent sein Ergebnis als Artefakt und nicht einfach als Antworttext?

- Starten Sie den Lager-Agenten neu und fragen Sie eine alte Task-ID mit `GetTask` ab. Was passiert, und was bedeutet das für einen echten Einsatz?

- Was ist der Unterschied zwischen `tools/call` (MCP) und `SendMessage` (A2A)? Vergleichen Sie Anfrage und Antwort.

- Die Fachagenten prüfen nicht, **wer** ihnen schreibt. Jeder, der Port 9998 erreicht, kann Bestellungen freigeben. Welche Felder der Agent Card würden das ändern?

---

## Ausblick: A2A Inspector

Für A2A gibt es ein Gegenstück zum MCP Inspector: den **A2A Inspector** (https://github.com/a2aproject/a2a-inspector). Er lädt die Agent Card, prüft sie auf Fehler und bietet eine Chat-Oberfläche, in der die rohen JSON-RPC-Nachrichten mitgeschrieben werden. Er wird aus dem Quellcode gestartet (Python und Node.js), ist also aufwendiger einzurichten als `npx @modelcontextprotocol/inspector`. Für den Unterricht reichen die PowerShell-Befehle dieser Übung, weil sie dieselben Nachrichten zeigen.

---

## Fehlerbehebung

- *„Die Verbindung mit dem Remoteserver kann nicht hergestellt werden“:* Laufen die Fachagenten in Fenster 1 (`python fachagenten_starten.py`)? Adresse und Port prüfen (9999, 9998, 9997).
- *Antwort enthält `error` statt `result`:* Header `$h` mitgeschickt? Methodenname korrekt geschrieben (Groß-/Kleinschreibung)?
- *Umlaute falsch dargestellt:* siehe Hinweis oben (PowerShell 7 verwenden).
- *`curl.exe` meldet „Failed to open/read local data“:* Den Befehl im Projektordner ausführen, damit der Pfad `anfragen\04_streaming.json` stimmt.

---

## Autoren und Urheberrecht
- Created by: Michael Lotter
- Date: 11/2026
- Version: v1.1 (drei Fachagenten)

![line](images/banner.png)
<p align="center">
<a href="09_a2a_wireshark.md"><img src="images/previous.png" width="150px"></a>
</p>
