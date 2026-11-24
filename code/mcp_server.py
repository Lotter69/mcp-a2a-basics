#!/usr/bin/env python3
"""
MCP Server für das Netzwerklabor
Stellt 3 Tools bereit: Lagerbestand abfragen, Lieferantenkatalog abfragen, Raumbelegung abfragen
Benötigt: mcp 2.x (siehe requirements.txt)
"""
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent, ListToolsResult, CallToolResult
from mcp.server.stdio import stdio_server

# Hardcodierter Lagerbestand
LAGER_BESTAND = {
    "blau_1m": 45,
    "rot_1m": 32
}

# Hardcodierter Lieferantenkatalog (Preis pro Stück in Euro, Lieferzeit in Werktagen)
LIEFERANTEN_KATALOG = {
    "blau":    {"preis": 1.50, "lieferzeit": 3},
    "rot":     {"preis": 1.50, "lieferzeit": 3},
    "gelb":    {"preis": 1.80, "lieferzeit": 5},
    "gruen":   {"preis": 1.80, "lieferzeit": 5},
    "schwarz": {"preis": 1.60, "lieferzeit": 4},
}

# Hardcodierte Belegung der Laborräume (Raum -> Wochentag -> belegt durch)
RAUM_BELEGUNG = {
    "104": {"montag": "Klasse IT11", "donnerstag": "Klasse 10b"},
    "105": {"dienstag": "Klasse 11a"},
}


# =============================================================================
# TOOL 1: PATCHKABEL BESTAND ABFRAGEN
# =============================================================================

# MCP Tool-Beschreibung
TOOL_DESCRIPTION = Tool(
    name="patchkabel_bestand_abfragen",
    description="Fragt den aktuellen Lagerbestand von Patchkabeln ab. Zeigt Bestände von blauen und roten 1m Patchkabeln sowie den Gesamtbestand an.",
    inputSchema={
        "type": "object",
        "properties": {
            "farbe": {
                "type": "string",
                "description": "Die Farbe des Patchkabels (blau, rot, oder gesamt für alle)",
                "enum": ["blau", "rot", "gesamt"]
            }
        },
        "required": ["farbe"]
    }
)

# Beispiel-Argumente:
# {"farbe": "blau"}
# {"farbe": "rot"}
# {"farbe": "gesamt"}

def patchkabel_bestand_abfragen(farbe: str) -> str:
    """
    Tool-Funktion: Fragt Patchkabel-Bestand ab
    
    Args:
        farbe: Die Farbe des abzufragenden Patchkabels (blau/rot/gesamt)
    
    Returns:
        Formatierter String mit dem Bestandsinformationen
    """
    if farbe == "blau":
        bestand = LAGER_BESTAND["blau_1m"]
        return f"Bestand blaue 1m Patchkabel: {bestand} Stück"
    
    elif farbe == "rot":
        bestand = LAGER_BESTAND["rot_1m"]
        return f"Bestand rote 1m Patchkabel: {bestand} Stück"
    
    elif farbe == "gesamt":
        blau = LAGER_BESTAND["blau_1m"]
        rot = LAGER_BESTAND["rot_1m"]
        gesamt = blau + rot
        return (f"Lagerbestand 1m Patchkabel:\n"
                f"  - Blau: {blau} Stück\n"
                f"  - Rot: {rot} Stück\n"
                f"  - Gesamt: {gesamt} Stück")
    
    else:
        return f"Unbekannte Farbe: {farbe}"


# =============================================================================
# TOOL 2: LIEFERANTENKATALOG ABFRAGEN
# =============================================================================

TOOL_KATALOG = Tool(
    name="patchkabel_katalog_abfragen",
    description="Fragt im Katalog des Lieferanten Preis und Lieferzeit für 1m Patchkabel einer Farbe ab. Für Nachbestellungen. Liefert KEINEN Lagerbestand.",
    inputSchema={
        "type": "object",
        "properties": {
            "farbe": {
                "type": "string",
                "description": "Die Farbe des Patchkabels",
                "enum": ["blau", "rot", "gelb", "gruen", "schwarz"]
            }
        },
        "required": ["farbe"]
    }
)

# Beispiel-Argumente:
# {"farbe": "gelb"}

def patchkabel_katalog_abfragen(farbe: str) -> str:
    """Tool-Funktion: Preis und Lieferzeit beim Lieferanten"""
    eintrag = LIEFERANTEN_KATALOG.get(farbe)
    if eintrag is None:
        return f"Farbe {farbe} ist nicht im Katalog des Lieferanten"
    return (f"Katalog 1m Patchkabel {farbe}: "
            f"{eintrag['preis']:.2f} Euro pro Stück, Lieferzeit {eintrag['lieferzeit']} Werktage")


# =============================================================================
# TOOL 3: RAUMBELEGUNG ABFRAGEN
# =============================================================================

TOOL_RAUM = Tool(
    name="laborraum_belegung_abfragen",
    description="Prüft, ob ein Laborraum (104 oder 105) an einem Wochentag belegt oder frei ist.",
    inputSchema={
        "type": "object",
        "properties": {
            "raum": {
                "type": "string",
                "description": "Die Raumnummer des Laborraums",
                "enum": ["104", "105"]
            },
            "tag": {
                "type": "string",
                "description": "Der Wochentag",
                "enum": ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]
            }
        },
        "required": ["raum", "tag"]
    }
)

# Beispiel-Argumente:
# {"raum": "104", "tag": "donnerstag"}

def laborraum_belegung_abfragen(raum: str, tag: str) -> str:
    """Tool-Funktion: Belegung eines Laborraums an einem Wochentag"""
    if raum not in RAUM_BELEGUNG:
        return f"Unbekannter Raum: {raum}"
    belegt_durch = RAUM_BELEGUNG[raum].get(tag)
    if belegt_durch:
        return f"Raum {raum} ist am {tag.capitalize()} belegt ({belegt_durch})"
    return f"Raum {raum} ist am {tag.capitalize()} frei"


# =============================================================================
# MCP SERVER SETUP
# =============================================================================

async def list_tools(ctx, params) -> ListToolsResult:
    """
    Gibt die Liste aller verfügbaren Tools zurück.
    Diese Funktion wird vom MCP Client aufgerufen (tools/list).
    """
    return ListToolsResult(tools=[TOOL_DESCRIPTION, TOOL_KATALOG, TOOL_RAUM])


async def call_tool(ctx, params) -> CallToolResult:
    """
    Verarbeitet Tool-Aufrufe vom MCP Client (tools/call).
    Ruft die entsprechende Tool-Funktion basierend auf dem Namen auf.

    Args:
        params.name: Name des aufzurufenden Tools
        params.arguments: Dictionary mit den Tool-Argumenten

    Returns:
        CallToolResult mit TextContent (MCP Response)
    """
    name = params.name
    arguments = params.arguments or {}

    if name == "patchkabel_bestand_abfragen":
        result = patchkabel_bestand_abfragen(
            farbe=arguments["farbe"]
        )
        return CallToolResult(content=[TextContent(type="text", text=result)])

    elif name == "patchkabel_katalog_abfragen":
        result = patchkabel_katalog_abfragen(
            farbe=arguments["farbe"]
        )
        return CallToolResult(content=[TextContent(type="text", text=result)])

    elif name == "laborraum_belegung_abfragen":
        result = laborraum_belegung_abfragen(
            raum=arguments["raum"],
            tag=arguments["tag"]
        )
        return CallToolResult(content=[TextContent(type="text", text=result)])

    else:
        raise ValueError(f"Unbekanntes Tool: {name}")


# Server-Instanz erstellen und die beiden Funktionen als Handler registrieren
server = Server(
    "patchkabel-lager-server",
    version="1.0.0",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    """Server über stdio starten"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
