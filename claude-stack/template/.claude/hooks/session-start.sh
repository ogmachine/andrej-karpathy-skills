#!/usr/bin/env bash
# SessionStart (startup): install project dependencies in cloud sessions.
# The cloud environment cache keeps toolchains from the setup script, but each session
# is a fresh clone, so lockfile installs belong here. Locally this is a no-op.
set -uo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

run() { echo "session-start: $*" >&2; "$@" >/dev/null 2>&1 || echo "session-start: '$*' failed (continuing)" >&2; }

# JS: one lockfile decides the package manager.
if   [ -f pnpm-lock.yaml ];    then command -v pnpm >/dev/null || run npm i -g pnpm; run pnpm install --frozen-lockfile
elif [ -f bun.lock ] || [ -f bun.lockb ]; then run bun install --frozen-lockfile
elif [ -f yarn.lock ];         then run yarn install --frozen-lockfile
elif [ -f package-lock.json ]; then run npm ci
elif [ -f package.json ];      then run npm install
fi

# Python
if   [ -f uv.lock ];           then run uv sync --frozen
elif [ -f poetry.lock ];       then command -v poetry >/dev/null && run poetry install --no-interaction
elif [ -f requirements.txt ];  then run python3 -m pip install -q -r requirements.txt
fi

# Go / Rust: warm the module cache so builds don't stall on first test run.
[ -f go.mod ] && run go mod download
[ -f Cargo.toml ] && run cargo fetch

exit 0
