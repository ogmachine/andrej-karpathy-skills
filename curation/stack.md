# Stack curation — forks and stars

Source: ogmachine's 186 forks (a proxy for the stars: the ~669 stars are private, and both the API and the stars page return nothing to logged-out readers). Upstream stars verified via GitHub search on 2026-10-20; "—" = not verified.

Rule: **one default owner per capability.** Prefer on-demand cost (skills, subagents) over always-on context and hot-path hooks. Cloud containers are ephemeral, so anything that keeps state on local disk (memory DBs, indexes) starts empty every session.

## CORE — in the default stack

| Repo                                                                                        | Stars | What it gives                                                                                                                         | How it reaches cloud                                        |
| ------------------------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| [mattpocock/skills](https://github.com/mattpocock/skills)                                   | 297k  | Owns the **methodology** capability: tdd, diagnosing-bugs, research, prototype, domain-modeling, grilling. User-invoked, 1.6k tokens. | claude.ai plugin `mattpocock-skills` (already synced, kept) |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 43k   | Source of the 5 other kept plugins: code-review, commit-commands, feature-dev, frontend-design, playwright                            | claude.ai plugin directory (kept)                           |
| [anthropics/skills](https://github.com/anthropics/skills)                                   | 182k  | docx / pdf / pptx / xlsx, skill-creator, mcp-builder                                                                                  | claude.ai skills (already synced)                           |
| stack-core (this repo)                                                                      | —     | Guard + formatter hooks                                                                                                               | upload to claude.ai                                         |

## ON-DEMAND — enable per repo or per task

| Repo                                                                | Stars | Use when                                                                                  | How                                                                                                                                                          |
| ------------------------------------------------------------------- | ----- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [obra/superpowers](https://github.com/obra/superpowers)             | 302k  | A long feature where you want the full brainstorm → plan → subagent-execute → review loop | Enable on claude.ai, then turn `mattpocock-skills` off in that repo. Its SessionStart bootstrap adds ~2k always-on tokens. Don't run both methodology packs. |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable)         | 83k   | Design-heavy frontend work beyond `frontend-design`                                       | Already synced as claude.ai skill `cw-impeccable`; or commit its skill to the repo's `.claude/skills/`                                                       |
| [garrytan/gstack](https://github.com/garrytan/gstack)               | 137k  | Product sprints that want role tools (CEO/design/QA review, release)                      | Commit selected skills into `.claude/skills/`; skip its browser daemon (playwright owns browsing)                                                            |
| [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) | 34k   | A second-model review of risky diffs                                                      | Needs the Codex CLI and an OpenAI key as a cloud **network secret**; install via the setup script                                                            |
| design.md / awesome-design-md / ui-ux-pro-max-skill / taste-skill   | —     | Giving a UI repo a written design system                                                  | Commit one `DESIGN.md` to the repo and reference it from CLAUDE.md                                                                                           |
| strix                                                               | —     | Security testing of your own app                                                          | Run as a CLI from the setup script; never against third-party targets                                                                                        |
| codegraph / codebase-memory-mcp / Understand-Anything               | —     | Very large codebases where grep-driven exploration is slow                                | Project `.mcp.json`; expect a re-index each cloud session                                                                                                    |

## REFERENCE — read, don't install

[anthropics/claude-code](https://github.com/anthropics/claude-code) (153k; changelog, plugin examples) · [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) (56k; discovery list) · learn-claude-code, claude-howto (how the harness works) · system-prompts-and-models-of-ai-tools, system_prompts_leaks (prompt patterns) · deepagents, OpenHands, goose, hermes-agent (other harnesses, useful for comparing designs) · Prompt-Engineering-Guide.

## SKIP — and why

| Repo                                                                                              | Stars | Reason                                                                                                                                               |
| ------------------------------------------------------------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)                             | 109k  | Same capability as mattpocock/skills, and it ships as the synced `agent-protocols` plugin, which adds a SessionStart hook, 32 skills and 2.9k tokens |
| [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)                                 | 102k  | Hooks on every event plus a local DB that is wiped with each cloud container. In cloud, memory belongs in committed notes (`docs/plans/`)            |
| [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode)                   | 40k   | Multi-agent orchestration that built-in subagents and Workflows now cover; heavy hooks                                                               |
| [SuperClaude-Org/SuperClaude_Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) | 24k   | Large persona/command injection into context; superseded by skills                                                                                   |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)         | 30k   | Keep in **Cowork**; off in code repos (it's the source of the legal/finance/sales packs)                                                             |
| agentmemory, OpenViking, cognee, context-hub, headroom                                            | —     | Memory and context layers: same ephemeral-disk problem; overlap with CLAUDE.md, skills and plans                                                     |
| cc-switch, vibe-kanban, orca, claudian, claude-obsidian                                           | —     | Desktop or local apps; nothing to run in a cloud container                                                                                           |
| browser-use, CloakBrowser                                                                         | —     | playwright owns browser automation                                                                                                                   |
| Thinking-Claude                                                                                   | —     | Obsolete; models have native extended thinking                                                                                                       |

## Overlaps resolved

| Capability                             | Owner                                         | Rejected alternatives                                                                             |
| -------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Methodology (TDD, debugging, planning) | mattpocock-skills                             | superpowers (on-demand), agent-protocols, zizi-skills, backend-design, ship                       |
| Safety guard                           | stack-core `guard.py`                         | claude-hooks safety-net, security-guidance, hookify (hookify stays as the opt-in _warning_ layer) |
| Formatting                             | stack-core `format.py`                        | per-plugin formatters                                                                             |
| Code review                            | code-review + feature-dev reviewer            | pr-review-toolkit (2.9k tokens; opt-in), shepherd, codex-plugin-cc (on-demand)                    |
| Browser                                | playwright                                    | browser-use, tinyfish/firecrawl plugins (their connectors stay)                                   |
| Memory across sessions                 | committed `docs/plans/<task>.md` + CLAUDE.md  | claude-mem, active-memory, agent-memory, baton, wherewasi, governor                               |
| Status line / usage meters             | none in cloud (the web UI has no status line) | claude-pulse, claudemeter, cc-token-statusline, crystools, rich-statusline, statusquote           |

## To finish this with the real star list

Export the 669 stars on your Mac (`gh api --paginate user/starred --jq '.[].full_name' > stars.txt`, or use the existing `vibe-config-sandbox/system/github-stars-all.tsv`), commit the file to this repo, and re-run the curation against it.
