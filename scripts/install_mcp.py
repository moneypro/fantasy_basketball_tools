#!/usr/bin/env python3
"""Register this checkout's MCP server in project-scoped Codex configuration."""
import json
from pathlib import Path
import shutil
try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def install(root=ROOT):
    path = root / ".codex/config.toml"
    original = path.read_text() if path.exists() else ""
    config = tomllib.loads(original)
    expected = {"command": "bash", "args": [str(root / "scripts/run_mcp.sh")],
                "cwd": str(root), "startup_timeout_sec": 15, "tool_timeout_sec": 660}
    current = config.get("mcp_servers", {}).get("fantasy-basketball")
    if current is not None:
        if current != expected:
            raise SystemExit("An existing fantasy-basketball configuration differs; left it unchanged.")
        return path
    addition = "\n[mcp_servers.fantasy-basketball]\n" + "".join(
        f"{k} = {json.dumps(v)}\n" for k, v in expected.items())
    tomllib.loads(original + addition)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(".toml.before-fantasy-mcp"))
    temp = path.with_suffix(".toml.tmp")
    temp.write_text(original + addition)
    temp.replace(path)
    return path


if __name__ == "__main__":
    print(f"Registered fantasy-basketball in {install()}")
    print("Restart MCP servers or open a new Codex task in this trusted project.")
