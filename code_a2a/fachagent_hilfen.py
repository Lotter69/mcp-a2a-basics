#!/usr/bin/env python3
"""
Gemeinsame Bausteine der Fachagenten (Lager, Bestellung, Raumbuchung)

  1. mcp_tool_aufrufen() - ein Tool des MCP-Servers benutzen (Fachagent = MCP-Client)
  2. nachrichten_des_auftrags() - alle Nachrichten des Auftraggebers zu einer Aufgabe
  3. agent_starten()     - HTTP-Server mit Agent Card und JSON-RPC-Endpunkt starten

Jeder Fachagent ist für sich ein A2A-Server mit eigener Adresse (Port) und Agent Card.
"""

import sys
from pathlib import Path

import uvicorn
from starlette.applications import Starlette

from a2a.helpers import get_data_parts, get_text_parts
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import Role
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_SERVER = Path(__file__).with_name("mcp_server.py")


# --- 1. Werkzeug benutzen (MCP) ------------------------------------------------------

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


# --- 2. Nachrichten einer Aufgabe ----------------------------------------------------

def nachrichten_des_auftrags(context, task) -> list:
    """Alle Nachrichten des Auftraggebers (Verlauf der Aufgabe + neue Nachricht)."""
    nachrichten = [m for m in task.history if m.role == Role.ROLE_USER]
    if context.message.message_id not in [m.message_id for m in nachrichten]:
        nachrichten.append(context.message)
    return nachrichten


def text_und_daten(nachricht) -> tuple[str, list]:
    """Text (kleingeschrieben) und strukturierte Daten einer Nachricht."""
    text = " ".join(get_text_parts(nachricht.parts)).lower()
    return text, get_data_parts(nachricht.parts)


# --- 3. Server starten ---------------------------------------------------------------

def agent_starten(agent_card, executor, host: str, port: int) -> None:
    """Startet den A2A-Server: GET /.well-known/agent-card.json und POST / (JSON-RPC)."""
    request_handler = DefaultRequestHandler(
        agent_executor=executor,                 # die Agent-Logik
        task_store=InMemoryTaskStore(),          # merkt sich alle Tasks (nur im Arbeitsspeicher)
        agent_card=agent_card,
    )
    routes = []
    routes.extend(create_agent_card_routes(agent_card))         # Discovery
    routes.extend(create_jsonrpc_routes(request_handler, "/"))  # Aufträge
    print(f"{agent_card.name} (A2A-Server)")
    print(f"Agent Card: http://{host}:{port}/.well-known/agent-card.json")
    print(f"JSON-RPC:   http://{host}:{port}/")
    print("Beenden mit Strg+C\n")
    uvicorn.run(Starlette(routes=routes), host=host, port=port, log_level="warning")
