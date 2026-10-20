# Working agreement (all projects)

## Before changing code

- Read the code you're changing, its callers, and its tests first; follow the patterns already in the repo.
- Use the project's own commands for build/test/lint (package.json scripts, Makefile/justfile, pyproject, CI workflow) — find them before inventing one.
- When a choice is expensive to reverse and the request doesn't settle it, ask one focused question; otherwise pick the conventional option and say which.

## Scope

- Make the smallest change that fully solves the task. Keep refactors, renames, and formatting sweeps in their own commits.
- Prefer the standard library and dependencies already in the project; add a new one only when it removes real complexity, and let the package manager update the lockfile.
- Note out-of-scope problems you spot (in your reply or as a suggested task) rather than fixing them silently.

## Definition of done

- Run the relevant tests, typecheck, and lint, and quote the result. Done means they pass.
- Bugs: reproduce first (failing test or command), fix, then show the same check passing.
- Fix failing tests by fixing the code; edit a test only when the test is wrong, and say why.
- UI changes: run the app and look at the change (Playwright/Chromium where available) before reporting.
- State plainly anything you could not verify.

## Git

- Small, focused commits; the message says why, not just what.
- Check `git status` before committing so secrets, `.env` files, and build output stay out.

## Context

- For work spanning sessions, keep a short plan + progress note in the repo (e.g. `docs/plans/<task>.md`) and update it as you go.

## Guardrails

- The stack-core plugin blocks destructive or secret-leaking commands. When it denies or asks, take the safer alternative it names instead of working around it.
