# <Project name>

<!-- Loaded in every session. Keep it under ~100 lines: facts Claude can't cheaply rediscover from the code.
     Deep docs live in docs/ (point to them); per-area rules go in <area>/AGENTS.md (+ a CLAUDE.md importing it) or .claude/rules/*.md with `paths:`. -->

## What this is

<2–3 sentences: what it does, who uses it, main entry points.>

## Commands

- Install: `<cmd>` — cloud sessions run this automatically (.claude/hooks/session-start.sh)
- Dev server: `<cmd>`
- Test all / one file: `<cmd>` / `<cmd> <path>`
- Typecheck + lint: `<cmd>`
- Format: `<cmd>` — the stack-core plugin runs the project formatter after each edit

## Layout

- `<dir>/` — <what lives here and when to touch it>

## Conventions

- <Repo-specific rules in positive form, e.g. "Validate external input with the zod schemas in src/schemas/.">

## Boundaries

- Generated (edit the source instead): `<paths>`
- Ask first: schema/data migrations, public API changes, dependency major-version bumps, anything under `<path>`.

## References

- Architecture: `docs/architecture.md` — read before cross-module changes.
