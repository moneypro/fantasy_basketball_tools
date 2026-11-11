# Local fantasy basketball MCP

The server exposes the existing Python workflows over MCP's local stdio transport.
It starts on demand from Codex and does not open a network port, deploy a service,
use ngrok, or call a model API. ESPN requests still use the existing local `.env`.

## Setup and connection

From this checkout, with Python 3.10 or newer:

```sh
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r requirements-mcp.txt
.venv-mcp/bin/python scripts/install_mcp.py
.venv-mcp/bin/python scripts/check_mcp.py
```

The installer preserves other settings and writes only the `fantasy-basketball`
server entry in this project's ignored `.codex/config.toml`. Run it again after
moving the checkout. A differing existing entry is preserved for manual review.
The project must be trusted in Codex. Restart MCP servers in the desktop app, or
open a new task in this project, then check `/mcp`. Existing tasks may retain
their original tool catalog. `codex mcp get fantasy-basketball` checks registration;
the smoke script separately verifies initialization, discovery and a tool call.

For another stdio MCP client, configure command `bash`, argument
`/absolute/path/to/fantasy_basketball_tools/scripts/run_mcp.sh`, and a tool timeout
of at least 660 seconds. The launcher resolves its own checkout, so the client
can start from any working directory. No credentials belong in client config.

Add `--live` to `scripts/check_mcp.py` to verify authenticated league and roster
reads. Never test the integration by performing an actual acquisition.

Dependencies are isolated from the existing Flask service and dashboard. The
SDK is pinned to the supported 1.x maintenance line for this machine's Python
3.10; SDK 2.x requires Python 3.11+. Review and test dependency upgrades explicitly.

## Tool map

| Workflow | MCP tools |
| --- | --- |
| Startup and instructions | `health`, `list_workflows`, `get_workflow` |
| Live league and player state | `get_league`, `get_roster`, `get_players` |
| Pickup research and legal-game comparisons | `pickup_report` |
| Live matchup and remaining-point outlook | `matchup_report` |
| Five-game roles, teammate splits and opponent defense | `streaming_profile` |
| League-wide injury flags and player inventory | `injury_inventory` |
| Read saved report artifacts | `read_report` |
| Paired free-agent replacement | `preview_add_drop`, `execute_plan`, `verify_plan` |
| Explicit minimal lineup changes | `preview_lineup`, `execute_plan`, `verify_plan` |

`fantasy://guidance` provides repository preferences. Workflow instructions and
references are exposed through `fantasy://workflows/{name}` and `get_workflow`.
Generated report files are available through the URIs returned by report tools.
The original `.agents/skills` files remain the single source of workflow guidance.
No global skill copies are installed.

Optional identity inputs default to the current Pacific-date ESPN ending year,
`LEAGUE_ID` in `.env`, and `FANTASY_TEAM_ID` (default 2). Always check the live
league identity. Full player names and IDs remain in transaction audit records;
user-facing discussion follows `AGENTS.md` surname preferences.

Research tools call the existing collectors with fixed argument lists, without a
shell. They save reports under ignored `output/mcp/reports/`. Streaming profiles
can take several minutes. Reports use current ESPN reads; errors never substitute
old cache data. The pickup model's static projections still require human/agent
review of fresh injury news and rotation evidence. `get_players` takes verified
ESPN IDs; use the research/injury inventory to find IDs and candidates.

## Executing an already-authorized move

1. Read the applicable workflow, resolve exact IDs, and check live availability.
2. Call `preview_add_drop` or `preview_lineup`. No ESPN write occurs. The server
   saves a ten-minute plan and returns its ID, full names, payload and roster.
3. If the conversation authorizes that exact move, call `execute_plan` with its
   `plan_id` and `authorized=true`. Existing authorization is sufficient; a
   preview, research request or migration request alone is not authorization.
4. The server repeats preflight, refuses changed roster/period/payload, and creates
   an exclusive durable journal before a single POST. Repeating the same plan
   only reconciles the original attempt; it never submits again.
5. Report the returned status exactly. After an acquisition, inspect the intended
   scoring date and use the lineup preview/execution tools for minimal activation.
   Verified acquisition and verified activation are separate completion steps.

Plan state lives under `output/mcp/plans/`. Team-level file locks serialize MCP
writes across processes. Unresolved earlier MCP journals block another plan for
the same team. `verify_plan` performs readback only. Don't delete journals to
retry. The authorization flag records the calling agent's assertion; it is not
an authentication boundary or a substitute for the user's instruction.

## Existing workflows retained

Scheduled rollover pickups and overnight waiver watches stay in their existing
systemd runners and skill scripts. They must survive chat/server shutdown and
still require an explicitly authorized pair and bounded execution window. This
migration does not install, reschedule or cancel any timer. MCP team locks cover
MCP writes only; check for conflicts with existing runners before transacting.

Conditional waiver claims remain in the documented `espn-add-drop` waiver
workflow. The free-agent tool intentionally rejects waiver players. Existing
CLI journals are still reconciled with their original CLI helpers, not MCP plan
IDs. The legacy Flask API, dashboard and command-line tools remain usable.

This is a local MCP adapter for core workflows, not a rewrite of every legacy
Flask endpoint or a hosted ChatGPT plugin. ChatGPT web does not read local Codex
config; remote access would be a separate authenticated hosting project.

## Costs and maintenance

- Incremental MCP server hosting: **$0/month** on the existing machine; normal
  electricity and internet costs still apply. No domain or tunnel is required.
- Additional model API spend inside this server: **$0**. It makes no OpenAI API
  calls. The Codex/ChatGPT client continues using its existing plan/credits;
  tools and report text consume context, so AI usage is not free or unlimited.
- No paid data provider has been added. The existing ESPN access is reused.
- Main maintenance work: ESPN endpoint/schema changes, session expiration,
  season transitions, dependency updates and keeping the machine awake for jobs.
- Sharing through a hosted server would add hosting/authentication/operations
  work. It is outside this local migration and has no cost committed here.

Official references: [OpenAI MCP setup](https://learn.chatgpt.com/docs/extend/mcp),
[MCP Python SDK 1.x](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0),
[current SDK and Python requirement](https://github.com/modelcontextprotocol/python-sdk).

## Validation and rollback

```sh
.venv-mcp/bin/python -m pip install pytest
.venv-mcp/bin/python -m pytest tests/test_mcp.py tests/test_mcp_protocol.py -q
.venv-mcp/bin/python scripts/check_mcp.py --live
```

Unit tests simulate execution, rejection, timeouts and restarts. Protocol tests
launch the actual stdio server and validate schemas, resources, errors and
credential-free health output. Live validation performs GET requests only.

To disconnect, remove only `[mcp_servers.fantasy-basketball]` from the project's
`.codex/config.toml` and restart MCP servers. This leaves the original scripts,
skills, dashboard, scheduled jobs and all audit records intact.
