"""Run with python -m fantasy_mcp.server; stdout is exclusively MCP protocol."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .backend import Backend, ROOT, WORKFLOWS, add_drop, workflow

Positive = Annotated[int, Field(gt=0, strict=True)]
Season = Annotated[int, Field(ge=2000, le=2100, strict=True)]
Players = Annotated[list[Positive], Field(min_length=1, max_length=20)]
PlanId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class LineupMove(BaseModel):
    player_id: Positive
    slot_id: Annotated[int, Field(ge=0, le=14, strict=True)]


READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
PREVIEW = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)

mcp = FastMCP(
    "fantasy-basketball",
    instructions=(
        "Use live ESPN reads and get_workflow before fantasy actions. Research never authorizes a transaction. "
        "Execute only the user's exact authorized pair or lineup, using a fresh preview plan ID; authorization "
        "already given in the conversation is sufficient. After uncertainty call verify_plan, never resubmit. "
        "A pickup is complete only after target-date activation is also verified. Use surnames, Pacific times, "
        "and last-five-team-game context. Skills and existing persistent schedulers remain in this repository."
    ),
    log_level="WARNING",
)
backend = Backend()


async def call(fn, *args, **kwargs):
    """Keep blocking ESPN/report work off the event loop; never expose raw exceptions."""
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except add_drop.Refused as exc:
        raise ToolError(str(exc)) from None
    except Exception as exc:
        raise ToolError(f"Operation failed ({type(exc).__name__}); credentials and raw responses withheld. "
                        "For an attempted write use verify_plan before any new action.") from None


@mcp.tool(annotations=LOCAL)
async def health() -> dict[str, Any]:
    """Check local startup and credential presence without contacting ESPN or exposing secrets."""
    return await call(backend.health)


@mcp.tool(annotations=LOCAL)
def list_workflows() -> dict[str, Any]:
    """List the repository's research, acquisition, rollover and waiver-watch skills."""
    return {"workflows": [{"name": k, "description": v} for k, v in WORKFLOWS.items()]}


@mcp.tool(annotations=LOCAL)
async def get_workflow(name: str) -> dict[str, Any]:
    """Read a named skill, its references, and MCP usage guidance before applying the workflow."""
    return await call(workflow, name)


@mcp.tool(annotations=READ)
async def get_league(season: Season | None = None, league: Positive | None = None,
                     team: Positive | None = None) -> dict[str, Any]:
    """Read live identity, scoring, roster locks, acquisition counters and matchup settings."""
    return await call(backend.league_context, season, league, team)


@mcp.tool(annotations=READ)
async def get_roster(period: Positive | None = None, season: Season | None = None,
                     league: Positive | None = None, team: Positive | None = None) -> dict[str, Any]:
    """Read a dated live roster, slots, ownership, eligibility and injury flags. Default: today's period."""
    return await call(backend.roster, period, season, league, team)


@mcp.tool(annotations=READ)
async def get_players(player_ids: Players, season: Season | None = None,
                      league: Positive | None = None) -> dict[str, Any]:
    """Resolve exact ESPN player IDs, ownership, FA/waiver status, locks and eligibility."""
    return await call(backend.players, player_ids, season, league)


@mcp.tool(annotations=PREVIEW)
async def pickup_report(season: Season | None = None, league: Positive | None = None,
                        team: Positive | None = None,
                        days: Annotated[int, Field(ge=7, le=28)] = 14,
                        limit: Annotated[int, Field(ge=1, le=100)] = 35,
                        watch: Players | None = None, compare_drop: Positive | None = None) -> dict[str, Any]:
    """Build a fresh pickup report with live roster, candidates and usable-game comparisons.

    Saves local artifacts; ESPN reads only. Static projections require news/rotation review.
    """
    return await call(backend.report, "pickup", season=season, league=league, team=team,
                      days=days, limit=limit, player_ids=watch, compare_drop=compare_drop)


@mcp.tool(annotations=PREVIEW)
async def matchup_report(season: Season | None = None, league: Positive | None = None,
                         team: Positive | None = None) -> dict[str, Any]:
    """Build live scores and remaining-point outlook using verified matchup boundaries."""
    return await call(backend.report, "matchup", season=season, league=league, team=team)


@mcp.tool(annotations=PREVIEW)
async def streaming_profile(player_ids: Players, season: Season | None = None,
                            league: Positive | None = None,
                            days: Annotated[int, Field(ge=1, le=28)] = 7) -> dict[str, Any]:
    """Compare last-five-game minutes/FP, teammate splits, opponent defense and Pacific schedules.

    Can take several minutes while collecting league-wide box scores. Estimates are labeled.
    """
    return await call(backend.report, "streaming", season=season, league=league,
                      days=days, player_ids=player_ids)


@mcp.tool(annotations=PREVIEW)
async def injury_inventory(season: Season | None = None, league: Positive | None = None) -> dict[str, Any]:
    """Read league-wide injury flags and availability; future game status still needs dated news."""
    return await call(backend.report, "injuries", season=season, league=league)


@mcp.tool(annotations=LOCAL)
async def read_report(report_id: PlanId, filename: str) -> str:
    """Read an artifact returned by a report tool. Only MCP-generated report files are accessible."""
    return await call(backend.read_report, report_id, filename)


@mcp.tool(annotations=PREVIEW)
async def preview_add_drop(add_id: Positive, drop_id: Positive, season: Season | None = None,
                           league: Positive | None = None, team: Positive | None = None) -> dict[str, Any]:
    """Validate one paired free-agent replacement; save a ten-minute plan without submitting it.

    Rejects waiver players. Claims and persistent watches follow their skill-specific workflows.
    """
    return await call(backend.preview_add_drop, add_id, drop_id, season, league, team)


@mcp.tool(annotations=PREVIEW)
async def preview_lineup(moves: Annotated[list[LineupMove], Field(min_length=1, max_length=30)],
                         period: Positive, season: Season | None = None,
                         league: Positive | None = None, team: Positive | None = None) -> dict[str, Any]:
    """Validate explicit player/slot moves for a scoring period, preserving unrelated slots and IR."""
    return await call(backend.preview_lineup, [m.model_dump() for m in moves], period, season, league, team)


@mcp.tool(annotations=WRITE)
async def execute_plan(plan_id: PlanId, authorized: bool = False) -> dict[str, Any]:
    """Execute the exact preview only when the user has authorized that move in this conversation.

    Set authorized=true only from that instruction. Rechecks live state, journals one POST,
    verifies independently. Repeated calls only reconcile. Acquisitions still require activation.
    """
    return await call(backend.execute_plan, plan_id, authorized)


@mcp.tool(annotations=READ)
async def verify_plan(plan_id: PlanId) -> dict[str, Any]:
    """Reconcile an attempted plan using only ESPN GET requests. Never retries a write."""
    return await call(backend.verify_plan, plan_id)


@mcp.resource("fantasy://guidance", mime_type="text/markdown")
def guidance() -> str:
    return (ROOT / "AGENTS.md").read_text() + "\n\n" + (ROOT / "docs/MCP.md").read_text()


@mcp.resource("fantasy://workflows/{name}", mime_type="application/json")
async def workflow_resource(name: str) -> str:
    return json.dumps(await call(workflow, name))


@mcp.resource("fantasy://reports/{report_id}/{filename}", mime_type="text/plain")
async def report_resource(report_id: str, filename: str) -> str:
    return await call(backend.read_report, report_id, filename)


if __name__ == "__main__":
    mcp.run(transport="stdio")
