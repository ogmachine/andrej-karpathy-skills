#!/usr/bin/env python3
"""PostToolUse formatter: format the file Claude just wrote, using the project's own formatter.

Only runs a formatter when the project clearly uses it (config file present and binary
installed locally), so it never introduces style churn in repos that don't format.
Never downloads anything, never blocks, never prints on success.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 20

JS_EXT = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".mts",
    ".cts",
    ".json",
    ".jsonc",
    ".css",
    ".scss",
    ".less",
    ".html",
    ".vue",
    ".svelte",
    ".astro",
    ".md",
    ".mdx",
    ".yaml",
    ".yml",
    ".graphql",
}
BIOME_EXT = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".mts",
    ".cts",
    ".json",
    ".jsonc",
    ".css",
    ".graphql",
}


def find_up(start: Path, names: tuple[str, ...], stop: Path) -> Path | None:
    for d in [start, *start.parents]:
        for n in names:
            if (d / n).exists():
                return d / n
        if d == stop:
            break
    return None


def project_root(path: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return path.parent


def local_bin(root: Path, start: Path, name: str) -> str | None:
    for d in [start, *start.parents]:
        cand = d / "node_modules" / ".bin" / name
        if cand.exists():
            return str(cand)
        if d == root:
            break
    for venv in (".venv", "venv"):
        cand = root / venv / "bin" / name
        if cand.exists():
            return str(cand)
    return None


def pyproject_has(root: Path, start: Path, section: str) -> bool:
    p = find_up(start, ("pyproject.toml",), root)
    try:
        return p is not None and f"[{section}" in p.read_text(errors="ignore")
    except OSError:
        return False


def pick(path: Path) -> list[str] | None:
    ext = path.suffix.lower()
    root = project_root(path)
    start = path.parent

    if ext in JS_EXT:
        if ext in BIOME_EXT and find_up(start, ("biome.json", "biome.jsonc"), root):
            b = local_bin(root, start, "biome")
            if b:
                return [b, "format", "--write", str(path)]
        prettier_cfg = find_up(
            start,
            (
                ".prettierrc",
                ".prettierrc.json",
                ".prettierrc.yaml",
                ".prettierrc.yml",
                ".prettierrc.js",
                ".prettierrc.cjs",
                ".prettierrc.mjs",
                ".prettierrc.toml",
                "prettier.config.js",
                "prettier.config.cjs",
                "prettier.config.mjs",
                "prettier.config.ts",
            ),
            root,
        )
        if not prettier_cfg:
            pkg = find_up(start, ("package.json",), root)
            try:
                prettier_cfg = (
                    pkg
                    if pkg and '"prettier"' in pkg.read_text(errors="ignore")
                    else None
                )
            except OSError:
                prettier_cfg = None
        if prettier_cfg:
            p = local_bin(root, start, "prettier")
            if p:
                return [
                    p,
                    "--write",
                    "--log-level",
                    "warn",
                    "--ignore-unknown",
                    str(path),
                ]
        return None

    if ext in (".py", ".pyi"):
        if find_up(start, ("ruff.toml", ".ruff.toml"), root) or pyproject_has(
            root, start, "tool.ruff"
        ):
            r = local_bin(root, start, "ruff") or shutil.which("ruff")
            if r:
                return [r, "format", "--quiet", str(path)]
        if pyproject_has(root, start, "tool.black"):
            b = local_bin(root, start, "black") or shutil.which("black")
            if b:
                return [b, "--quiet", str(path)]
        return None

    if ext == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", str(path)]
    if (
        ext == ".rs"
        and shutil.which("rustfmt")
        and find_up(start, ("Cargo.toml",), root)
    ):
        edition = "2021"
        cargo = find_up(start, ("Cargo.toml",), root)
        try:
            for line in cargo.read_text(errors="ignore").splitlines():
                if line.strip().startswith("edition"):
                    edition = line.split("=", 1)[1].strip().strip('"') or edition
                    break
        except OSError:
            pass
        return ["rustfmt", "--edition", edition, str(path)]
    if ext in (".tf", ".tfvars") and shutil.which("terraform"):
        return ["terraform", "fmt", str(path)]
    if (
        ext in (".sh", ".bash")
        and shutil.which("shfmt")
        and find_up(start, (".editorconfig",), root)
    ):
        return ["shfmt", "-w", str(path)]
    return None


def main() -> int:
    if os.environ.get("CLAUDE_FORMAT", "").lower() in ("off", "0", "false"):
        return 0
    try:
        event = json.load(sys.stdin)
        ti = event.get("tool_input") or {}
        tr = event.get("tool_response") or {}
        f = ti.get("file_path") or (
            tr.get("filePath") if isinstance(tr, dict) else None
        )
        if not f:
            return 0
        path = Path(f)
        if not path.is_file() or "/node_modules/" in str(path) or "/.git/" in str(path):
            return 0
        cmd = pick(path)
        if cmd:
            subprocess.run(
                cmd, cwd=str(path.parent), capture_output=True, timeout=TIMEOUT
            )
    except Exception as e:  # never break the session over formatting
        print(f"format.py: skipped ({e})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
