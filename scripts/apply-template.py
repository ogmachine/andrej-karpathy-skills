#!/usr/bin/env python3
"""Apply the claude-stack project template to a repository, merging instead of clobbering.

  python3 scripts/apply-template.py /path/to/repo [--refresh-denylist] [--hookify]

- .claude/settings.json: permission lists are unioned, hooks appended (deduped by command),
  enabledPlugins merged with the repo's own entries winning.
- .claude/hooks/session-start.sh: copied if missing.
- AGENTS.md + CLAUDE.md: AGENTS.md is the shared source (Claude, Codex, Cursor, Gemini) and
  CLAUDE.md imports it with `@AGENTS.md`. Existing files are never overwritten; a repo with
  only AGENTS.md gets the one-line CLAUDE.md.
- --refresh-denylist: rebuild the "<plugin>@synced": false list from `claude plugin list`
  (use after enabling new plugins on claude.ai) — keeps KEEP below enabled.
- --hookify: turn on the hookify plugin for this repo and add the starter warning rules
  (debug leftovers, focused/skipped tests, Python breakpoints). Commit the rule files:
  cloud sessions only see what is in the clone.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"
KEEP = {
    "code-review",
    "commit-commands",
    "feature-dev",
    "frontend-design",
    "playwright",
    "mattpocock-skills",
    "stack-core",
}


def synced_denylist() -> dict:
    out = subprocess.run(
        ["claude", "plugin", "list"], capture_output=True, text=True, timeout=120
    ).stdout
    names = sorted(set(re.findall(r">\s+([\w.-]+)@synced", out)))
    return {f"{n}@synced": False for n in names if n not in KEEP}


def merge(base: dict, add: dict) -> dict:
    out = dict(base)
    perms = dict(out.get("permissions", {}))
    for k in ("allow", "ask", "deny"):
        merged = list(perms.get(k, []))
        merged += [r for r in add.get("permissions", {}).get(k, []) if r not in merged]
        if merged:
            perms[k] = merged
    if perms:
        out["permissions"] = perms
    hooks = {ev: list(v) for ev, v in out.get("hooks", {}).items()}
    for ev, groups in add.get("hooks", {}).items():
        existing = {
            h.get("command") for g in hooks.get(ev, []) for h in g.get("hooks", [])
        }
        for g in groups:
            if not all(h.get("command") in existing for h in g.get("hooks", [])):
                hooks.setdefault(ev, []).append(g)
    if hooks:
        out["hooks"] = hooks
    plugins = dict(add.get("enabledPlugins", {}))
    plugins.update(out.get("enabledPlugins", {}))  # the repo's explicit choices win
    if plugins:
        out["enabledPlugins"] = plugins
    out.setdefault("$schema", add.get("$schema"))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or not Path(args[0]).is_dir():
        print(__doc__)
        return 2
    repo = Path(args[0]).resolve()
    tmpl = json.loads((TEMPLATE / ".claude/settings.json").read_text())
    if "--refresh-denylist" in sys.argv:
        tmpl["enabledPlugins"] = synced_denylist()
    hookify = "--hookify" in sys.argv
    if hookify:
        for rule in sorted((TEMPLATE / "extras/hookify").glob("hookify.*.local.md")):
            dest = repo / ".claude" / rule.name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rule, dest)
                print(f"added   .claude/{rule.name}")

    target = repo / ".claude/settings.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    current = json.loads(target.read_text()) if target.exists() else {}
    if hookify:  # an explicit repo-level true wins over the template's denylist on every later run
        current.setdefault("enabledPlugins", {})["hookify@synced"] = True
    target.write_text(json.dumps(merge(current, tmpl), indent=2) + "\n")
    print(f"merged  {target.relative_to(repo)}")

    hook = repo / ".claude/hooks/session-start.sh"
    if not hook.exists():
        hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / ".claude/hooks/session-start.sh", hook)
        print(f"added   {hook.relative_to(repo)}")

    has_agents, has_claude = (
        (repo / "AGENTS.md").exists(),
        (repo / "CLAUDE.md").exists(),
    )
    if not has_agents and not has_claude:
        shutil.copy2(TEMPLATE / "AGENTS.md", repo / "AGENTS.md")
        print("added   AGENTS.md (fill in the <placeholders>)")
    if not has_claude:
        shutil.copy2(TEMPLATE / "CLAUDE.md", repo / "CLAUDE.md")
        print("added   CLAUDE.md (imports AGENTS.md)")
    else:
        print("kept    existing CLAUDE.md" + (" and AGENTS.md" if has_agents else ""))

    gi = repo / ".gitignore"
    lines = gi.read_text().splitlines() if gi.exists() else []
    if ".claude/settings.local.json" not in lines:
        gi.write_text("\n".join(lines + [".claude/settings.local.json"]) + "\n")
        print("updated .gitignore")
    return 0


if __name__ == "__main__":
    sys.exit(main())
