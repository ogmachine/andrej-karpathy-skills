# Token-load report — 2026-10-20

**Answer:** In this cloud session the big load is not plugins. `claude plugin list --json` returns `[]`. The 217 synced plugins (~201k tokens) did not load. What loads instead: about 22 claude.ai MCP connectors (~464 deferred tool names, ~12k tokens est.) and 53 synced claude.ai skills (~5k tokens est.). The template's safety hooks (`stack-core`) did not load either, because they ship as a synced plugin.

Scope: this cloud container only. The Mac ("MacBookPro") was **offline** (Desktop Commander `list_devices`: "Offline, last seen 93h ago"). Every Mac item below is marked **not checked**.

Read-only run. No settings, plugins, connectors or claude.ai state were changed. No secrets were copied: env vars were checked by name only.

## Method

- `ai-adoption:token-doctor` and `mattpocock-skills:grill-with-docs` were **not available** in this session. Both come from synced plugins, and no synced plugins loaded (see F1). I followed their intent by hand: diagnose → one question per finding, each with a recommended answer, checked against code.claude.com docs.
- Measured with: `claude plugin list --json`, directory listings under `~/.claude/`, character counts of skill `description` frontmatter (tokens ≈ chars ÷ 4), and a count of the MCP tool names this session was offered.
- `/context` is a slash command for the user. I could not run it, so the numbers are estimates, not the `/context` figure.
- Claude Code version: 2.1.304 (`claude --version`).

## Measured load (this cloud session)

| Source | Measured here | Template target (`claude-stack/`) | Source of claim |
| --- | --- | --- | --- |
| Synced claude.ai plugins | **0** (`claude plugin list --json` → `[]`; `~/.claude/plugins/synced/<org>/` is empty) | 6 plugins, ~2.1k tokens | measurement; `claude-stack/README.md` line 6 |
| Plugin hooks | **0** (no settings files, no plugins) | 3 (guard, format, SessionStart install) | measurement; `claude-stack/docs/ARCHITECTURE.md` "Layers" |
| Synced claude.ai skills | **53** (52 in `~/.claude/skills/synced/`, plus `session-start-hook`); descriptions 20,079 chars ≈ **5.0k tokens** | not covered by the template | measurement |
| — of which Cowork design skills (`cw-*`) | 29 | — | measurement |
| MCP connectors (claude.ai) | ~22 servers, ~464 deferred tool names; 1 failed (`ccd_session`) | "prune dead connectors" (manual) | count of tool names offered this session; ARCHITECTURE.md layer 4 |
| — names + server instructions | ≈ **12k tokens** (est.: ~55 chars per prefixed name ≈ 9k, server instructions ≈ 3k) | — | estimate |
| — duplicate GitHub tools | ~46 names (a GitHub connector plus the built-in `github` server) | — | count |
| Repo `CLAUDE.md` | 2,357 chars ≈ 0.6k tokens | ~30-line `AGENTS.md` + 1-line `CLAUDE.md` | `wc -c CLAUDE.md` |
| `~/.claude/CLAUDE.md` (setup script) | **absent** | 36 lines, ~500 tokens | `ls ~/.claude`; ARCHITECTURE.md layer 2 |
| Harness tools + system prompt | not measured; not user-controllable | — | — |

Rough always-on total you control here: **~18k tokens** (MCP ~12k + skills ~5k + CLAUDE.md ~0.6k). The ~201k plugin figure from 2026-10-19 does not reproduce in this session.

## Doc facts used (code.claude.com)

- **Synced plugins**: they "load in Cowork sessions and in terminal sessions where you sign in with your claude.ai account". Cloud sessions are not on that list. — `/docs/en/plugins/loading#synced-plugins`
- **What carries over to cloud**: the table lists repo `CLAUDE.md`, repo `.claude/settings.json` hooks and permissions, `.mcp.json`, and repo skills, agents and rules. It says "Cloud sessions automatically load skills you enable on claude.ai". It does not list claude.ai-synced plugins. — `/docs/en/cloud-environments#what-carries-over-from-your-setup`
- **Hooks in cloud**: "Claude Code runs hooks from the repository and from your organization's server-managed settings." User-level hooks don't run. — `/docs/en/cloud-environments` (SessionStart hooks section)
- **Turning off synced plugins**: `"<name>@synced": false` in user or project `enabledPlugins`, or `syncClaudeAiPlugins: false` in user settings, which moves them to `~/.claude/plugins/.trash/`. — `/docs/en/plugins/loading#control-which-synced-plugins-load`
- **Skill listing**: descriptions are always in context; the listing budget is 1% of the context window; each entry is capped at 1,536 chars (`skillListingMaxDescChars`); `skillOverrides` can set an entry to `"name-only"`; `disable-model-invocation: true` removes the description from context. — `/docs/en/skills` ("Skill descriptions are cut short", "Control who invokes a skill")
- **MCP**: "MCP tool definitions are deferred by default, so only tool names and server instructions enter context… Disable unused servers." CLI tools are "more context-efficient than MCP servers". — `/docs/en/costs#reduce-mcp-server-overhead`
- **CLAUDE.md**: "Aim to keep CLAUDE.md under 200 lines." — `/docs/en/costs#move-instructions-from-claudemd-to-skills`
- Output styles: none are set in this session (no settings files exist). I did not fetch the output-styles page because there was nothing to check against it.

## Findings → questions (my recommendation in each; the decision is yours)

### F1. The template's main cut targets a load that doesn't appear in cloud
Measured: 0 synced plugins in this cloud session. Docs list synced plugins for Cowork and terminal sessions, not cloud (`/plugins/loading#synced-plugins`). `ARCHITECTURE.md` says "Plugins enabled on claude.ai — Yes, every session" for cloud, and that the denylist was "verified with `claude plugin list`". That claim conflicts with both this measurement and the docs.

**Q1. Where should the 211-plugin cut live: per repo (template), on the Mac, or both?**
Recommended: keep the repo denylist as cheap insurance, but treat the **Mac** as the real target (see F6). Correct the cloud row in `ARCHITECTURE.md` after one more cloud check in a repo that has the template applied.

### F2. The safety guard isn't running in this cloud session
`stack-core` (guard.py, format.py) is delivered as a synced claude.ai plugin (ARCHITECTURE.md layer 1). No synced plugin loaded here, so neither hook ran. Docs: cloud runs hooks from **the repository** and server-managed settings (`/cloud-environments`).

**Q2. Move guard and format hooks from the `stack-core` plugin into the template's repo `.claude/settings.json` (scripts in `.claude/hooks/`)?**
Recommended: **yes**. Repo hooks are the documented path in cloud. Cost: 0 context tokens, ~40 ms per matching tool call (ARCHITECTURE.md).

### F3. MCP connectors are the biggest controllable load here (~12k tokens est.)
About 22 claude.ai connectors and ~464 tool names. The GitHub tools appear twice (~46 duplicate names). Many connectors are unrelated to coding: Shopify, Lovable, Replit, Miro, Notion, TinyFish, Gmail, Calendar, Slides, Drive. One failed to connect (`ccd_session`). Docs: only names and server instructions load, and you should disable unused servers (`/costs`).

**Q3a. Disconnect the duplicate GitHub connector?** Recommended: **yes**. The built-in `github` server already covers it.
**Q3b. Which of the other connectors should stay connected?** Recommended: keep what you use weekly and disconnect the rest at claude.ai → Customize → Connectors. Caveat: this affects every surface (chat, Cowork, cloud), so it's your call per connector. Expected saving: roughly 0.4k–2.5k tokens per server, depending on its tool count and instructions (est.).

### F4. 53 synced skills ≈ 5k tokens; 29 are Cowork design skills
Docs: every listed skill "adds to your context on every turn" (`/skills`). `skillOverrides` with `"name-only"` keeps a skill callable without its description.

**Q4. Set the 29 `cw-*` skills to `"name-only"` in the template's repo `.claude/settings.json`?**
Recommended: **yes, as a test**. Expected saving ≈ 2–3k tokens (est.). Caveat: **not verified** that `skillOverrides` in repo settings applies to claude.ai-synced skills in cloud. Check with `/context` before and after. Alternative: turn the skills off on claude.ai, but that also removes them from Cowork.

### F5. The global working agreement isn't present here
`~/.claude/CLAUDE.md` doesn't exist, so this cloud environment isn't running `claude-stack/setup-script.sh`.

**Q5. Attach the setup script to this cloud environment?**
Recommended: **yes, if you want the global agreement in cloud** (+~500 tokens, per ARCHITECTURE.md). Otherwise leave it off. The repo `CLAUDE.md` already carries similar guidance.

### F6. The Mac — not checked
Docs: synced plugins load in terminal sessions signed in with claude.ai (`/plugins/loading`). So the ~201k load most likely lives on the Mac. Not checked: `~/.claude/settings.json`, `~/.claude/CLAUDE.md` and its imports, `~/.agents/`, `~/_agent-work/CLAUDE.md`, plugin and skill dirs, Code-tab `/context`.

**Q6. On the Mac, use `syncClaudeAiPlugins: false` (stops all sync) or per-plugin `"<name>@synced": false` (keeps the 6)?**
Recommended: **per-plugin**, mirroring the template's keep set. `syncClaudeAiPlugins: false` would also drop `stack-core` and the 6 kept plugins. Re-run this doctor when the Mac is online.

### F7. The numbers in your brief disagree with the repo
Your brief says 95 hooks (15 SessionStart, 16 per Bash, 24 per write). `curation/claude-ai-plugins.tsv` sums to **99** hooks, and `README.md` and `ARCHITECTURE.md` say 99 (20 SessionStart). Other TSV totals match the brief: 217 plugins, 201,027 tokens, 228 MCP servers, 1,418 skills, 184 agents.

**Q7. Which hook count is right?** Recommended: trust the TSV (99), since it's the per-plugin source. Re-measure on the Mac to settle it.

## Not checked

- Everything on the Mac (F6).
- The exact `/context` breakdown, including harness system prompt and built-in tool schemas.
- Whether the plugin load differs in a cloud session started in a repo that has the template applied.
