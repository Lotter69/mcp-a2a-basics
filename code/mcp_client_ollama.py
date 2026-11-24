#!/usr/bin/env python3
"""
MCP Client mit Ollama - Natürliche Spracheingabe
Nutzt lokales Ollama Modell und verbindet sich mit dem MCP Server
"""
import asyncio
import sys
import json
import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# System-Prompt für das Modell
# Die Tool-Liste wird beim Start aus der Antwort von tools/list erzeugt.
# So steht im Prompt genau das, was der MCP-Server über seine Tools sagt.
def system_prompt_erstellen(tools) -> str:
    tool_zeilen = []
    for tool in tools:
        tool_zeilen.append(f"- {tool.name}: {tool.description}")
        for param, schema in tool.input_schema.get("properties", {}).items():
            werte = ", ".join(f'"{w}"' for w in schema.get("enum", []))
            tool_zeilen.append(f"  Parameter: {param} ({schema.get('type')}) - {werte}")
    tool_liste = "\n".join(tool_zeilen)

    return f"""Du bist ein hilfreicher Assistent mit Zugriff auf Tools. 

Verfügbare Tools:
{tool_liste}

Wenn du ein Tool verwenden möchtest, antworte NUR mit diesem JSON-Format:
{{"tool": "TOOLNAME", "PARAMETER": "WERT"}}

Wenn du keine Tools brauchst, antworte normal in natürlicher Sprache.

Beispiele:
Nutzer: "Wie viele blaue Kabel haben wir?"
Du: {{"tool": "patchkabel_bestand_abfragen", "farbe": "blau"}}

Nutzer: "Was kostet ein gelbes Kabel beim Lieferanten?"
Du: {{"tool": "patchkabel_katalog_abfragen", "farbe": "gelb"}}

Nutzer: "Ist Raum 104 am Donnerstag frei?"
Du: {{"tool": "laborraum_belegung_abfragen", "raum": "104", "tag": "donnerstag"}}

Nutzer: "Hallo"
Du: Hallo! Wie kann ich dir helfen?

Antworte auf Deutsch."""

async def main():
    print(" Ollama MCP Netzwerklabor Client gestartet")
    print(" Modell: qwen2.5-coder:3b")
    
    # Verbindung zum MCP Server aufbauen
    server_params = StdioServerParameters(
        command=sys.executable,  # Python der aktiven venv
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Server initialisieren
            await session.initialize()
            
            # Verfügbare Tools abrufen
            tools_result = await session.list_tools()
            available_tools = tools_result.tools
            
            tool_namen = [tool.name for tool in available_tools]
            SYSTEM_PROMPT = system_prompt_erstellen(available_tools)

            print(f" {len(available_tools)} Tools verfügbar:")
            for tool in available_tools:
                print(f"   - {tool.name}: {tool.description}")
            print("\n" + "="*60)
            
            # Konversationshistorie
            conversation_history = []
            
            # Hauptschleife für Benutzereingaben
            while True:
                user_input = input("\n Ihre Anfrage (oder 'exit' zum Beenden): ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'beenden']:
                    print(" Auf Wiedersehen!")
                    break
                
                if not user_input:
                    continue
                
                print("\n Verarbeite Anfrage...")
                
                # Nachricht zur Historie hinzufügen
                conversation_history.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # Erste Anfrage an Ollama
                try:
                    response = ollama.chat(
                        model='qwen2.5-coder:3b',
                        messages=[
                            {'role': 'system', 'content': SYSTEM_PROMPT}
                        ] + conversation_history
                    )
                    
                    response_text = response['message']['content'].strip()
                    
                    # Prüfen ob Tool-Aufruf (JSON-Format)
                    if response_text.startswith('{') and '"tool"' in response_text:
                        try:
                            # Tool-Aufruf parsen
                            tool_call = json.loads(response_text)
                            tool_name = tool_call.get('tool')
                            # Alle übrigen Felder sind die Argumente, z. B. {"farbe": "blau"}
                            arguments = {k: v for k, v in tool_call.items() if k != 'tool'}
                            
                            if tool_name in tool_namen and arguments:
                                print(f" Führe Tool aus: {tool_name}")
                                print(f"   Parameter: {arguments}")
                                
                                # Tool auf dem MCP Server aufrufen
                                result = await session.call_tool(
                                    tool_name, 
                                    arguments
                                )
                                
                                tool_result = result.content[0].text
                                print(f"   Ergebnis: {tool_result}")
                                
                                # Tool-Ergebnis zur Historie hinzufügen
                                conversation_history.append({
                                    'role': 'assistant',
                                    'content': response_text
                                })
                                conversation_history.append({
                                    'role': 'user',
                                    'content': f'Tool-Ergebnis: {tool_result}\n\nBitte formuliere eine natürliche Antwort basierend auf diesem Ergebnis.'
                                })
                                
                                # Zweite Anfrage für natürliche Antwort
                                response2 = ollama.chat(
                                    model='qwen2.5-coder:3b',
                                    messages=[
                                        {'role': 'system', 'content': SYSTEM_PROMPT}
                                    ] + conversation_history
                                )
                                
                                final_response = response2['message']['content']
                                
                                print("\n Antwort:")
                                print(f"   {final_response}")
                                
                                # Finale Antwort zur Historie
                                conversation_history.append({
                                    'role': 'assistant',
                                    'content': final_response
                                })
                            else:
                                print("\n Antwort:")
                                print(f"   {response_text}")
                                conversation_history.append({
                                    'role': 'assistant',
                                    'content': response_text
                                })
                        
                        except json.JSONDecodeError:
                            # Kein gültiges JSON, normale Antwort
                            print("\n Antwort:")
                            print(f"   {response_text}")
                            conversation_history.append({
                                'role': 'assistant',
                                'content': response_text
                            })
                    else:
                        # Normale Antwort ohne Tool
                        print("\n Antwort:")
                        print(f"   {response_text}")
                        conversation_history.append({
                            'role': 'assistant',
                            'content': response_text
                        })
                
                except Exception as e:
                    print(f"\n Fehler bei der Kommunikation mit Ollama: {e}")
                    print("\nStellen Sie sicher, dass:")
                    print("  1. Ollama läuft (ollama serve)")
                    print("  2. Das Modell qwen2.5-coder:3b installiert ist")
                    break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n Programm beendet.")
    except Exception as e:
        print(f"\n Fehler: {e}\n")
        # Bei Fehlern in der Verbindung zum MCP-Server (TaskGroup) die eigentliche Ursache anzeigen
        def ursachen(fehler, ebene=1):
            for teil in getattr(fehler, "exceptions", []):
                print(f"{'  ' * ebene}Ursache: {type(teil).__name__}: {teil}")
                ursachen(teil, ebene + 1)
        ursachen(e)
        print("\n Tipp: Starten Sie den Server einzeln mit 'python mcp_server.py',")
        print(" um die vollständige Fehlermeldung zu sehen (Beenden mit Strg+C).")
