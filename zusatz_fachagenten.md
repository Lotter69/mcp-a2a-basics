# Fachagenten für den Orchestrator: Vorschläge

Stand: 24.11.2026. Ausgangslage: Planungs-Agent (Orchestrator, Ollama `qwen2.5-coder:3b`) beauftragt per A2A den Lager-Agenten (Fachagent, regelbasiert), der per MCP das Tool `patchkabel_bestand_abfragen` nutzt. `a2a-sdk` 1.3.x.

**Kurzfassung:** Fertige, öffentlich und kostenlos aufrufbare A2A-Agenten gibt es kaum, und die vorhandenen taugen nicht verlässlich für den Unterricht. Lohnender sind 2 bis 4 **eigene, lokale Fachagenten**, deren Agent Cards sich so unterscheiden, dass das LLM wirklich wählen muss.

---

## Teil 1: Was es öffentlich gibt

### Verzeichnisse (Registries)

| Verzeichnis | Was es ist | Ohne Konto/Kosten? | Für den Unterricht |
|---|---|---|---|
| [a2aregistry.org](https://a2aregistry.org/) | Register unabhängig betriebener A2A-Agenten mit Erreichbarkeitsprüfung (ca. 750 Einträge, Sweep 23.11.2026) | Stöbern ja; einzelne Agenten teils kostenpflichtig (x402) | Gut zum **Zeigen**, dass es ein „Telefonbuch“ für Agenten gibt. Zum Anbinden nicht geeignet: Qualität und Betreiber unklar. |
| [a2a-registry.org](https://www.a2a-registry.org/) ([Doku auf GitHub](https://github.com/A2ARegistry/GlobalA2ARegistry)) | Community-Registry mit Suche per Agent („Meta Agent“) | Eintragen kostenlos; Such-API nur mit Token | Interessant als Idee: Die Registry ist selbst ein A2A-Agent mit Agent Card. Für Schüler-Accounts eher nicht. |
| [a2alist.ai](https://a2alist.ai/) | Verzeichnis mit ca. 120 geprüften Einträgen | Stöbern frei; Discovery-API kostenpflichtig, viele Agenten pro Aufruf bezahlt | Nein, kommerziell ausgerichtet. |
| [sing1ee/a2a-directory](https://github.com/sing1ee/a2a-directory), [awesome-a2a](https://github.com/ai-boost/awesome-a2a) | Handgepflegte Linklisten (Agenten, SDKs, Tools) | ja (nur Liste) | Gut als Lesestoff. Einige Einträge versprechen „ohne Konto/Key“, sind aber Selbstauskünfte. |

Ehrliche Einordnung: Es gibt **kein offizielles, zentrales Verzeichnis** (die A2A-Spezifikation lässt Discovery offen: bekannte URL, `/.well-known/agent-card.json`, oder eine Registry). Die vorhandenen Registries sind Community- oder kommerzielle Projekte. Einzelne öffentliche Agenten, die laut Liste ohne Key funktionieren sollen (z. B. aamio, Open Task Relay, Kinocut), konnte ich aus meiner Umgebung nicht aufrufen und daher **nicht prüfen**. Für eine Unterrichtsstunde würde ich mich nicht auf fremde, jederzeit abschaltbare Endpunkte verlassen; dazu kommt die Frage, welche Daten Schüler an Unbekannte schicken.

### Offizielle Beispielsammlung: a2a-samples

[github.com/a2aproject/a2a-samples](https://github.com/a2aproject/a2a-samples) (Apache-2.0) enthält rund 30 Python-Agenten. Die meisten brauchen einen Gemini- oder OpenAI-Key. Ohne Key oder mit Ollama nutzbar:

| Beispiel | LLM nötig? | Passt zu eurem Lab? |
|---|---|---|
| `helloworld` | nein | Ja, als zweiter Mini-Fachagent. Nutzt `a2a-sdk` 1.1.0, also nah an eurer 1.3.x. |
| `number_guessing_game` (Alice, Bob, Carol) | nein | Inhaltlich schön: drei Agenten kooperieren ohne LLM. Aber `a2a-sdk` 0.3.0 (alte API), nicht direkt mit eurem Code kombinierbar. |
| `travel_planner_agent` | ja, OpenAI-kompatibel | `base_url` ist konfigurierbar, also auf Ollama umstellbar (`http://localhost:11434/v1`). Passt thematisch zur Klassenfahrt. Nicht getestet. |
| `adk_expense_reimbursement` | ja (ADK, LiteLLM möglich) | Didaktisch stark: Fehlen Angaben, schickt der Agent ein **Formular zurück** (Rückfrage). Läuft nur mit Aufwand lokal. |
| `adk_currency_agent`, `dice_agent_rest`, `content_planner`, `adk_facts` | ja (Gemini-Key) | Nur mit Google-Key; für Schüler eher nicht. |

**Fazit Teil 1:** Zeigen ja (Registry im Browser, eine fremde Agent Card lesen), anbinden besser nicht. Die a2a-samples sind gute Code-Vorlagen, aber Versionsstand und API-Keys passen selten.

---

## Teil 2: Fachagenten zum Selbstbauen

Alle laufen lokal, jeder auf eigenem Port mit eigener Agent Card, nach dem Muster des Lager-Agenten. LLM ist nur dort vorgesehen, wo es didaktisch etwas zeigt; sonst bleibt das LLM allein im Orchestrator.

### Szenario Netzwerklabor

| Fachagent | Skills (Agent Card) | LLM? | MCP-Tools (Werkzeug) | Was er didaktisch zeigt |
|---|---|---|---|---|
| **Lager-Agent** (vorhanden, Port 9999) | Patchkabel-Bestand prüfen | nein | `patchkabel_bestand_abfragen` | Rückfrage (Farbe fehlt), fertig, Ablehnung |
| **Bestell-Agent** | Material nachbestellen, Bestellstatus abfragen | nein | `artikel_suchen`, `bestellung_anlegen`, `budget_abfragen` | **Ablehnung** bei Budgetüberschreitung, **Rückfrage** „Bestellung über 50 € freigeben?“ (input-required mit Ja/Nein). Zeigt Kette: Orchestrator fragt erst Lager, dann Bestellung. |
| **Raumbuchungs-Agent** | Laborraum buchen, Belegung anzeigen | nein | `belegung_abfragen`, `raum_reservieren` (SQLite) | Rückfrage mit **Gegenvorschlag** („Raum 104 belegt, 105 ist frei. Nehmen?“). Gut für mehrstufige Tasks mit `contextId`. |
| **Subnetz-Agent** | Adressplan für n Gruppen erstellen, IP prüfen | nein | `subnetz_berechnen` (Python `ipaddress`) | Zeigt **warum** man delegiert: Das 3b-Modell rechnet Subnetze unzuverlässig, der Fachagent exakt. Liefert Ergebnis als **DataPart/Artefakt** (Tabelle als JSON). |
| **Diagnose-Agent** | Erreichbarkeit der Laborgeräte prüfen | nein | `ping_host`, `port_pruefen` (nur auf eine Whitelist des Labornetzes beschränkt) | **Streaming**: meldet Gerät für Gerät Fortschritt (`working` mit Zwischenständen), Artefakt am Ende. Auch Abbruch (`cancel`) zeigbar. |

### Szenario Klassenfahrt

| Fachagent | Skills | LLM? | MCP-Tools | Was er didaktisch zeigt |
|---|---|---|---|---|
| **Wetter-Agent** | Wettervorhersage für Ort und Datum | nein | `wetter_abfragen` über [Open-Meteo](https://open-meteo.com/) (frei, ohne Key) | Ein echter **externer Dienst** hinter einem Fachagenten. Ablehnung, wenn das Datum mehr als 16 Tage entfernt ist. |
| **Ferien-/Kalender-Agent** | Ferien und Feiertage im Zeitraum prüfen | nein | `ferien_abfragen` über [OpenHolidays API](https://www.openholidaysapi.org/) (frei, ohne Key) oder eine lokale Liste | Klar abgegrenzter Skill; Datenquelle frei austauschbar, ohne dass sich die Agent Card ändert. |
| **Unterkunfts-Agent** (simulierte Jugendherberge) | Verfügbarkeit prüfen, Zimmer anfragen | optional | `zimmer_verfuegbar`, `anfrage_stellen` (SQLite) | **Rückfrage** (Anzahl Lehrkräfte? Geschlechterverteilung?), **Ablehnung** (ausgebucht). Passt zur Transferfrage am Workshop-Ende. |
| **Budget-Agent** | Kosten pro Person berechnen, Zuschuss prüfen | nein | `kosten_summieren`, `zuschussregel_pruefen` | Orchestrator muss **Ergebnisse mehrerer Agenten kombinieren** (Unterkunftspreis + Fahrt → Budget). |
| **Programm-Agent** | Ausflugsprogramm vorschlagen | **ja** (eigenes Ollama-Modell) | `ausflugsziele_suchen` | Zeigt: Auch ein **Fachagent kann ein LLM haben**, der Orchestrator sieht das nicht (Black Box hinter der Agent Card). Vergleich mit regelbasiertem Lager-Agent. |

---

## Damit das LLM wirklich wählen muss

> **Stand:** Punkte 1 bis 3 sind umgesetzt. Lager-Agent (9999), Bestell-Agent (9998) und Raumbuchungs-Agent (9997) sind fest in die Kapitel 06 bis 10 eingebaut, der Orchestrator lädt alle Agent Cards aus `agenten.json`. Die Tabellen oben bleiben als Ideen für weitere Fachagenten.

1. **Mehrere Agent Cards laden.** Der Orchestrator liest eine kleine Liste von Basis-URLs (z. B. `agenten.json`), holt jede Agent Card und schreibt Name, Skills und Beschreibung in den System-Prompt. Antwortformat bleibt `{"agent": "<id>", "auftrag": "..."}`. Das ist nebenbei eine **Mini-Registry**, also die selbstgebaute Antwort auf die Frage nach dem Verzeichnis.
2. **Startset empfehlen: Lager, Bestellung, Raumbuchung** (alle Netzwerklabor, alle ohne LLM). Drei klar verschiedene Zuständigkeiten, aber mit einer Verwechslungsgefahr zwischen Lager („haben wir?“) und Bestellung („besorg mir“). Daran lässt sich zeigen, wie wichtig gute Skill-Beschreibungen sind.
3. **Testfragen mit eindeutiger Erwartung**, z. B.:
   - „Reichen 20 blaue Kabel für den Kurs?“ → Lager
   - „Bestell 30 gelbe Kabel nach.“ → Bestellung (ggf. Rückfrage zur Freigabe)
   - „Ist Raum 104 am Donnerstag frei?“ → Raumbuchung
   - „Was ist ein Patchkabel?“ → kein Agent, Orchestrator antwortet selbst
   - „Haben wir genug rote Kabel, und wenn nicht, bestell nach.“ → zwei Agenten nacheinander (Erweiterung für Fortgeschrittene)
4. **Realistische Erwartung an `qwen2.5-coder:3b`:** Die Auswahl unter 3 Agenten mit klaren Beschreibungen klappt erfahrungsgemäß meist; Ketten über zwei Agenten sind bei 3b-Modellen wackelig. Das ist didaktisch nützlich (Fehler beobachten), sollte aber vorher getestet werden.
5. **Erweiterung zur Klassenfahrt:** Gleicher Orchestrator-Code, andere `agenten.json` (Wetter, Unterkunft, Budget). Zeigt, dass die **Rollen** (Orchestrator, Fachagent, Werkzeug) szenariounabhängig sind.

Umgesetzt wurden beide Auswahlebenen: In Teil 1 wählt das LLM zwischen **drei MCP-Tools** (`mcp_server.py`), in Teil 2 wählt der Orchestrator zwischen **drei Fachagenten**, von denen jeder genau eines dieser Tools benutzt.
