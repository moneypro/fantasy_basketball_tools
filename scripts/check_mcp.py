#!/usr/bin/env python3
"""Exercise the real stdio protocol; optional live checks perform only reads."""
import argparse
import asyncio
from datetime import timedelta
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def check(live=False):
    params = StdioServerParameters(command="bash", args=[str(ROOT / "scripts/run_mcp.sh")], cwd="/tmp")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=180)) as session:
            initialized = await session.initialize()
            catalog = await session.list_tools()
            resources = await session.list_resources()
            result = await session.call_tool("health")
            if result.isError:
                raise RuntimeError("Health tool failed")
            summary = {"server": initialized.serverInfo.name, "tools": [t.name for t in catalog.tools],
                       "resources": [str(r.uri) for r in resources.resources], "health": result.structuredContent}
            if live:
                for tool in ("get_league", "get_roster"):
                    result = await session.call_tool(tool)
                    if result.isError:
                        raise RuntimeError(f"Live {tool} failed")
                    data = result.structuredContent
                    summary[tool] = ({k: data[k] for k in ("season", "leagueId", "teamId", "scoringPeriod")}
                                     if tool == "get_league" else {"period": data["period"], "players": len(data["players"])})
            print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    asyncio.run(check(parser.parse_args().live))
