# Architecture

How this stack is laid out, why, and what each piece costs. Verified against Claude Code 2.1.304 docs and measured in a cloud session on 2026-10-19.

## The problem it replaces

The account synced **217 claude.ai plugins** into every session: ~**201k tokens of always-on context** (projected by `claude plugin details`; skill descriptions are truncated to fit the listing budget, agent descriptions are not), **99 hooks** (20 on SessionStart, 14 on every prompt, 10 on every tool call), **228 MCP servers** (most failing through the cloud proxy), 1,418 skills, 184 agents. Hooks from different plugins fought each other (two safety guards, three memory systems, five status lines) and rewrote subagent prompts. Result: slow starts, permission noise, and a model choosing between 1,400 skills.

## Rule: put each thing at the cheapest layer that still reaches cloud

| Cost class        | What                                                                   | Paid when                                           |
| ----------------- | ---------------------------------------------------------------------- | --------------------------------------------------- |
| Always-on context | CLAUDE.md files, skill + agent descriptions, MCP tool names            | every turn                                          |
| Per-event latency | hooks                                                                  | every matching event (PreToolUse = every tool call) |
| On demand         | skill bodies, subagents, commands, path-scoped rules, nested CLAUDE.md | only when used                                      |
| Zero              | setup-script installs (CLIs), git config                               | never in context                                    |

Deterministic rules go in **hooks** (they can't be forgotten and cost no context). Judgment and conventions go in **CLAUDE.md**, kept short. Procedures go in **skills** (body loads only when invoked). Big searches go to **subagents** (their context is thrown away).

## What reaches a cloud session (Anthropic-hosted)

| Source                                                   | Read in cloud?                                   | Used here for                                             |
| -------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------- | ---------------------- | --- | --------------------- |
| Plugins enabled on claude.ai (incl. your uploads)        | Yes, every session                               | `stack-core` hooks + the 6 kept plugins                   |
| Repo `.claude/settings.json` (single-repo sessions)      | Yes: permissions, hooks, `enabledPlugins: false` | allowlist, SessionStart deps, synced-plugin denylist      |
| Repo `CLAUDE.md`, `.claude/rules                         | skills                                           | agents                                                    | commands`, `.mcp.json` | Yes | per-project knowledge |
| `~/.claude/CLAUDE.md` written by the setup script        | Yes                                              | global working agreement                                  |
| Setup script installs (CLIs, git config)                 | Yes (cached ~7 days)                             | fd, shellcheck, shfmt, ast-grep, just, tree, sqlite3      |
| `~/.claude/settings.json`, `.claude/settings.local.json` | **No**                                           | — (so `syncClaudeAiPlugins:false` can't be used in cloud) |
| `~/.claude/skills                                        | agents`, user-scope MCP                          | **No**                                                    | —                      |
| Plugins/marketplaces a repo _enables_                    | **No** (only `false` is honored)                 | —                                                         |

Sources: code.claude.com/docs/en/cloud-environments ("What carries over"), /settings ("Settings in cloud sessions"), /plugins/loading ("Control which synced plugins load").

## Layers

1. **`stack-core` plugin** (`plugin/`, upload `dist/stack-core.zip` to claude.ai). Two hooks, 0 always-on tokens:
   - `guard.py` (PreToolUse: Bash, Read, Edit, Write, MultiEdit, NotebookEdit, ~40 ms): **deny** `rm -rf` of `/`/`~`/system dirs, deleting `find` at those roots, disk writes, plain force-push, `--no-verify`, printing/uploading secrets (`.env`, keys, `~/.ssh`), env-dump-to-network, `.git/` edits. **Ask** for push to protected branches, `reset --hard`, `clean -f`, bulk checkout/restore, `branch -D`, curl-pipe-to-shell, publish/deploy/infra/cluster commands, destructive SQL in DB clients, lockfile/`.env` writes, edits to Claude's own settings/hooks. Shell-aware (parses `bash -c`, `eval`, `sudo`, env prefixes; ignores heredoc/echo data). Fails open; `CLAUDE_GUARD=off` disables.
   - `format.py` (PostToolUse: Edit, Write, MultiEdit): runs the **project's own** formatter (biome, prettier, ruff, black, gofmt, rustfmt, terraform fmt, shfmt) only when the repo has its config and a local binary; never downloads, never prints.
2. **Setup script** (`setup-script.sh`, generated): writes `~/.claude/CLAUDE.md` (36 lines, ~500 tokens), installs missing CLIs in parallel, sets safe git defaults. Runs in ~8 s; exits 0 even on partial failure.
3. **Repo template** (`template/`, apply with `scripts/apply-template.py <repo>`):
   - `.claude/settings.json`: 102 allow rules for the normal dev loop (the guard still catches the dangerous variants inside them), secret-path read denies, SessionStart dependency install, and `"<plugin>@synced": false` for every synced plugin outside the keep set → **6 plugins load instead of 217** (verified with `claude plugin list`). Cowork is unaffected.
   - `.claude/hooks/session-start.sh`: lockfile-driven install (`pnpm/bun/yarn/npm ci`, `uv sync`, `poetry`, `pip`, `go mod download`, `cargo fetch`) only when `CLAUDE_CODE_REMOTE=true`.
   - `CLAUDE.md`: ~30-line recipe-book skeleton (commands, layout, conventions, boundaries, pointers).
4. **claude.ai account**: keep the plugins you use in Cowork; prune dead connectors at claude.ai/customize/connectors (each connected server adds tool names to every session).

## Kept plugins (coding repos)

| Plugin            | Always-on tokens | Why                                                                              |
| ----------------- | ---------------- | -------------------------------------------------------------------------------- |
| code-review       | 22               | `/code-review` on diffs/PRs                                                      |
| commit-commands   | 105              | commit / push / PR commands                                                      |
| feature-dev       | 240              | explorer, architect, reviewer subagents                                          |
| frontend-design   | 80               | UI quality skill                                                                 |
| playwright        | 0 (deferred MCP) | see UI changes in a browser                                                      |
| mattpocock-skills | 1,651            | one methodology pack: tdd, diagnosing-bugs, research, prototype, domain modeling |

Everything else is one line away: remove its `false` entry in that repo's `.claude/settings.json`. Full table with per-plugin cost, hooks and MCP counts: `curation/claude-ai-plugins.tsv`.

## Permission prompts in cloud

"Accept edits" auto-approves file edits only. Bash, MCP and web calls still prompt unless allowed. Fix: the template's allowlist (committed per repo), or pick **Auto** in the mode dropdown. Cloud ignores `defaultMode: bypassPermissions/dontAsk` in settings files.

## Known limits

- The guard is a guardrail against mistakes, not a sandbox: obfuscated commands (`x=rm; $x -rf /`) and `xargs rm -rf < list` pass.
- `enabledPlugins` denylist is by name: a plugin newly enabled on claude.ai loads until you rerun `scripts/apply-template.py <repo> --refresh-denylist`.
- Multi-repo cloud sessions read only `enabledPlugins`/`extraKnownMarketplaces` from repo settings — no permissions or hooks.
