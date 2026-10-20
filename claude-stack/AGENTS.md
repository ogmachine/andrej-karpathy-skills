# claude-stack

A lean Claude Code setup for cloud sessions: the `stack-core` guardrail plugin, a cloud setup script, a per-repo template, and curation notes. See `README.md` for setup and `docs/ARCHITECTURE.md` for why each piece sits where it does.

## Commands

- Test the hooks: `python3 tests/test_hooks.py` (pipe-tests every rule; must print `OK`)
- Rebuild generated files after editing `global/CLAUDE.md`, `scripts/setup-script.tmpl.sh` or `plugin/`: `scripts/build.sh`
- Validate plugin + marketplace: `claude plugin validate plugin && claude plugin validate .`
- Try the template on a scratch repo: `python3 scripts/apply-template.py "$(mktemp -d)"`

## Layout

- `plugin/` — `stack-core` plugin; `hooks/guard.py` (PreToolUse deny/ask) and `hooks/format.py` (PostToolUse formatter). Python stdlib only.
- `global/CLAUDE.md` — source for `~/.claude/CLAUDE.md`; embedded into `setup-script.sh` by the build.
- `template/` — what `scripts/apply-template.py` merges into other repos (`extras/hookify/` is opt-in).
- `curation/` — plugin keep/off table with measured costs, fork curation, monorepo config survey.

## Conventions

- `setup-script.sh` and `dist/stack-core.zip` are generated: edit the sources, then run `scripts/build.sh` (CI checks they're in sync).
- Every guard rule change needs pipe-test cases in `tests/test_hooks.py` for both the blocked form and a nearby allowed form.
- Hooks must fail open, never print on success, and stay fast (guard ~40 ms).
- Build fake credentials in tests from concatenated pieces so no file contains a literal token.
