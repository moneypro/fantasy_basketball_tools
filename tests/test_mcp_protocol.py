"""Launch the actual server through MCP's stdio transport, with no ESPN writes."""
import asyncio
from pathlib import Path
import sys

import pytest

pytest.importorskip("mcp", reason="Install requirements-mcp.txt to test the optional MCP adapter")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def test_stdio_catalog_resources_calls_and_validation():
    async def check():
        params = StdioServerParameters(command=sys.executable, args=["-m", "fantasy_mcp.server"], cwd=str(ROOT))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.name == "fantasy-basketball"
                assert "Research never authorizes" in initialized.instructions
                catalog = {t.name:t for t in (await session.list_tools()).tools}
                assert set(catalog) == {"health", "list_workflows", "get_workflow", "get_league", "get_roster",
                    "get_players", "pickup_report", "matchup_report", "streaming_profile", "injury_inventory",
                    "read_report", "preview_add_drop", "preview_lineup", "execute_plan", "verify_plan"}
                assert catalog["get_roster"].annotations.readOnlyHint
                assert not catalog["execute_plan"].annotations.readOnlyHint
                assert catalog["execute_plan"].inputSchema["properties"]["authorized"]["default"] is False
                health = await session.call_tool("health")
                assert not health.isError
                assert health.structuredContent["transport"] == "stdio"
                assert "ESPN_S2" not in str(health.structuredContent)
                resource = await session.read_resource("fantasy://guidance")
                assert "Sheppard" in resource.contents[0].text
                workflow = await session.call_tool("get_workflow", {"name":"espn-add-drop"})
                assert not workflow.isError
                assert "Free-agent workflow" in workflow.structuredContent["instructions"]
                assert (await session.call_tool("get_players", {"player_ids":[]})).isError
                assert (await session.call_tool("get_players", {"player_ids":[True]})).isError
                assert (await session.call_tool("execute_plan", {"plan_id":"a"*32})).isError
                assert (await session.call_tool("read_report", {"report_id":"../.env", "filename":"packet.json"})).isError
    asyncio.run(check())
