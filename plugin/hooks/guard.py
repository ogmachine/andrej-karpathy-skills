#!/usr/bin/env python3
"""PreToolUse guard for Bash and file tools.

Blocks (deny) or escalates (ask) a small set of actions that are destructive,
irreversible, or leak secrets. Everything else passes silently.

Design rules:
- stdlib only, one process per tool call, no network.
- Fail open: an internal error never blocks work (it prints a warning to stderr).
- Reasons tell Claude the safe alternative, so a deny redirects instead of stalls.
- This is a guardrail against mistakes, not a sandbox against a determined attacker.

Escape hatch: CLAUDE_GUARD=off disables the hook for that process.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import PurePath

DENY, ASK = "deny", "ask"
PROTECTED_BRANCHES = {"main", "master", "trunk", "production", "prod", "release"}

# ---------------------------------------------------------------- secrets

_SAFE_ENV_SUFFIXES = (
    ".example",
    ".sample",
    ".template",
    ".dist",
    ".defaults",
    ".schema",
    ".test.example",
)
_SECRET_NAMES = {
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".netrc",
    ".pgpass",
    ".credentials.json",
    "credentials.json",
    "client_secret.json",
    ".git-credentials",
    ".npmrc.secret",
}
_SECRET_EXTS = (".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".ppk", ".asc.key")
_SECRET_DIR_PARTS = (
    "/.ssh/",
    "/.aws/",
    "/.gnupg/",
    "/.config/gh/",
    "/.kube/",
    "/.docker/config.json",
    "/.config/gcloud/",
)


def is_secret_path(path: str) -> bool:
    if not path:
        return False
    p = os.path.expanduser(path.strip("'\""))
    name = PurePath(p).name
    low = name.lower()
    if low == ".env" or (
        low.startswith(".env.") and not low.endswith(_SAFE_ENV_SUFFIXES)
    ):
        return True
    if (
        low.endswith(".env")
        and low not in (".env",)
        and not low.endswith(_SAFE_ENV_SUFFIXES)
        and "." in low[:-4]
    ):
        # e.g. production.env, secrets.env
        return True
    if low in _SECRET_NAMES or (
        low.startswith("service-account") and low.endswith(".json")
    ):
        return True
    if low.endswith(_SECRET_EXTS) and not low.endswith(".pub"):
        return True
    norm = "/" + p.replace("\\", "/").lstrip("/")
    return any(
        part in norm or norm.endswith(part.rstrip("/")) for part in _SECRET_DIR_PARTS
    )


# ---------------------------------------------------------------- files

_LOCKFILES = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "Cargo.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "pdm.lock",
    "composer.lock",
    "Gemfile.lock",
    "go.sum",
    "flake.lock",
    "pubspec.lock",
    "Package.resolved",
    "mix.lock",
    "deno.lock",
}


def check_file_tool(tool: str, ti: dict, cwd: str):
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or ""
    if not path:
        return None
    name = PurePath(path).name
    norm = path.replace("\\", "/")
    writing = tool in ("Edit", "Write", "MultiEdit", "NotebookEdit")

    if is_secret_path(path):
        if writing:
            return (
                ASK,
                f"{name} looks like a secrets file. Write placeholders to a .env.example instead, or confirm the user wants real values written here.",
            )
        return (
            DENY,
            f"{name} looks like a secrets file, so reading it is blocked. Use .env.example / docs for variable names, or ask the user for the specific non-secret value you need.",
        )
    if not writing:
        return None
    if "/.git/" in norm or norm.startswith(".git/"):
        return DENY, "Don't edit .git internals directly; use git commands."
    if name in _LOCKFILES:
        return (
            ASK,
            f"{name} is a lockfile. Regenerate it with the package manager (install/update/lock) rather than hand-editing.",
        )
    # Claude's own guardrails: changes need a human in the loop.
    home_claude = os.path.expanduser("~/.claude/")
    if (
        norm.startswith(home_claude)
        and (name.startswith("settings") or "/hooks/" in norm)
    ) or re.search(r"(^|/)\.claude/(settings[^/]*\.json|hooks/)", norm):
        return (
            ASK,
            "This edits Claude Code settings or hooks (the agent's own guardrails). Confirm with the user first.",
        )
    return None


# ---------------------------------------------------------------- bash


def _segments(cmd: str):
    """Split a shell command into simple-command token lists (best effort)."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>")
        lex.whitespace_split = True
        lex.commenters = ""
        tokens = list(lex)
    except ValueError:  # unbalanced quotes etc.
        tokens = cmd.split()
    seg: list[str] = []
    for t in tokens:
        if t and set(t) <= set(";&|()<>"):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


_WRAPPERS = {
    "sudo",
    "command",
    "builtin",
    "nohup",
    "time",
    "exec",
    "nice",
    "env",
    "xargs",
    "timeout",
    "stdbuf",
    "doas",
}


def _strip_prefix(seg: list[str]) -> list[str]:
    i = 0
    while i < len(seg):
        t = seg[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):  # VAR=value prefix
            i += 1
        elif t in _WRAPPERS:
            i += 1
            while i < len(seg) and seg[i].startswith(
                "-"
            ):  # wrapper flags, e.g. timeout -k 5
                i += 1
            if t == "timeout" and i < len(seg) and re.match(r"^\d", seg[i]):
                i += 1
        else:
            break
    return seg[i:]


def _expand(cmd: str, depth: int = 0):
    """Yield simple commands, descending into `bash -c '...'` / `eval '...'`."""
    for seg in _segments(cmd):
        seg = _strip_prefix(seg)
        if not seg:
            continue
        yield seg
        prog = PurePath(seg[0]).name
        if depth < 3 and prog in ("bash", "sh", "zsh", "dash", "ksh") and "-c" in seg:
            idx = seg.index("-c")
            if idx + 1 < len(seg):
                yield from _expand(seg[idx + 1], depth + 1)
        elif depth < 3 and prog == "eval" and len(seg) > 1:
            yield from _expand(" ".join(seg[1:]), depth + 1)


def _current_branch(cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", cwd or ".", "symbolic-ref", "--short", "-q", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return out.stdout.strip()
    except Exception:
        return ""


_GIT_OPTS_WITH_VALUE = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--config-env",
}


def _git_sub(seg: list[str]):
    """Return (subcommand, args) for a git invocation, skipping global options."""
    i = 1
    while i < len(seg):
        t = seg[i]
        if t in _GIT_OPTS_WITH_VALUE:
            i += 2
        elif t.startswith("-"):
            i += 1
        else:
            return t, seg[i + 1 :]
    return "", []


def _short_flags(tok: str) -> str:
    return tok[1:] if re.fullmatch(r"-[A-Za-z]+", tok) else ""


def check_git(seg: list[str], cwd: str):
    sub, args = _git_sub(seg)
    if sub == "push":
        if "--no-verify" in args:
            return (
                DENY,
                "Don't bypass git hooks with --no-verify. Fix what the hook reports, then push.",
            )
        lease = any(
            a.startswith(("--force-with-lease", "--force-if-includes")) for a in args
        )
        hard_force = any(
            a == "--force"
            or (
                a.startswith("--force")
                and not a.startswith(("--force-with-lease", "--force-if-includes"))
            )
            for a in args
        ) or any("f" in _short_flags(a) for a in args)
        positional = [a for a in args if not a.startswith("-")]
        refspecs = positional[1:]
        if any(r.startswith("+") for r in refspecs):
            hard_force = True
        if hard_force:
            return (
                DENY,
                "Plain force-push can destroy remote history. Use `git push --force-with-lease` on your own feature branch instead.",
            )
        if (
            "--mirror" in args
            or "--all" in args
            or "--delete" in args
            or "d" in "".join(_short_flags(a) for a in args)
            or any(r.startswith(":") for r in refspecs)
        ):
            return (
                ASK,
                "This push deletes or mirrors remote refs. Confirm with the user.",
            )
        targets = {r.split(":")[-1].removeprefix("refs/heads/") for r in refspecs}
        if not refspecs:
            targets = {_current_branch(cwd)}
        hit = targets & PROTECTED_BRANCHES
        if hit:
            how = "Force-pushing" if lease else "Pushing directly"
            return (
                ASK,
                f"{how} to protected branch '{sorted(hit)[0]}'. Prefer a feature branch + PR; confirm with the user if this is intended.",
            )
        return None
    if sub == "commit":
        valued = {
            "-m",
            "--message",
            "-F",
            "--file",
            "-C",
            "-c",
            "--reuse-message",
            "--reedit-message",
            "--author",
            "--date",
            "--fixup",
            "--squash",
            "--trailer",
            "-t",
            "--template",
            "--cleanup",
        }
        skip = False
        for a in args:
            if skip:
                skip = False
                continue
            if a in valued:
                skip = True
                continue
            if a == "--no-verify":
                return (
                    DENY,
                    "Don't bypass git hooks with --no-verify. Fix what the pre-commit hook reports, then commit.",
                )
            flags = _short_flags(a)
            for ch in flags:
                if (
                    ch in "mFCct"
                ):  # option takes a value; rest of token / next token is the value
                    skip = ch == flags[-1]
                    break
                if ch == "n":
                    return (
                        DENY,
                        "`git commit -n` skips hooks. Fix what the pre-commit hook reports, then commit.",
                    )
        return None
    if sub == "reset" and "--hard" in args:
        return (
            ASK,
            "`git reset --hard` discards uncommitted work. Prefer `git stash` or a new branch; confirm with the user.",
        )
    if (
        sub == "clean"
        and not ({"-n", "--dry-run"} & set(args))
        and (any("f" in _short_flags(a) for a in args) or "--force" in args)
    ):
        return (
            ASK,
            "`git clean -f` permanently deletes untracked files. Run `git clean -n` first and confirm with the user.",
        )
    if sub in ("checkout", "restore"):
        bulk = any(a in (".", ":/", "*") for a in args)
        if (sub == "checkout" and ("-f" in args or "--force" in args)) or (
            bulk and "--staged" not in args
        ):
            return (
                ASK,
                f"`git {sub}` on the whole tree discards uncommitted changes. Restore specific files or stash; confirm with the user.",
            )
    if sub == "stash" and args[:1] and args[0] in ("drop", "clear"):
        return ASK, "Dropping stashes is permanent. Confirm with the user."
    if sub == "branch" and any(
        a in ("-D", "--delete") or ("D" in _short_flags(a)) for a in args
    ):
        if "-D" in args or any("D" in _short_flags(a) for a in args):
            return (
                ASK,
                "`git branch -D` deletes unmerged work. Use `-d` (merged only) or confirm with the user.",
            )
    if sub in ("filter-branch", "filter-repo"):
        return ASK, "History rewrite. Confirm with the user."
    return None


_RM_HARD = re.compile(
    r"^(/|/\*|~|~/|~/\*|\$HOME|\$\{HOME\}|\$HOME/\*|/(etc|usr|bin|sbin|boot|lib|lib64|var|sys|proc|dev|opt|srv)(/.*)?)$"
)
_RM_SOFT = re.compile(r"^(\.|\./|\.\.|\.\./|\*|\.\*|\./\*|\.git|\./\.git)$")

_ASK_PROGRAMS = [
    (
        re.compile(
            r"^(npm|pnpm|yarn|bun) (publish|unpublish|dist-tag)\b|^yarn npm publish\b"
        ),
        "Publishing a package is public and irreversible.",
    ),
    (
        re.compile(
            r"^(cargo publish|cargo yank|twine upload|uv publish|poetry publish|gem push|flit publish|hatch publish)\b"
        ),
        "Publishing a package is public and irreversible.",
    ),
    (
        re.compile(r"^docker (push|system prune|volume rm|volume prune)\b"),
        "Pushes images or deletes Docker data.",
    ),
    (
        re.compile(
            r"^gh (repo (delete|archive|rename|edit)|release (create|delete|edit)|pr merge|secret|variable (set|delete)|api .*(-X|--method) ?(DELETE|PUT|PATCH))"
        ),
        "Changes shared GitHub state.",
    ),
    (
        re.compile(
            r"^terraform (apply|destroy|import|state (rm|mv|push))\b|^tofu (apply|destroy)\b|^pulumi (up|destroy)\b"
        ),
        "Changes real infrastructure.",
    ),
    (
        re.compile(
            r"^(kubectl|oc) (delete|apply|replace|drain|scale|patch|rollout)\b|^helm (uninstall|delete|upgrade|install|rollback)\b"
        ),
        "Changes a live cluster.",
    ),
    (
        re.compile(
            r"^(aws|gcloud|az|doctl|flyctl|fly|vercel|netlify|heroku|railway|wrangler)\b.*(\b(delete|destroy|remove|rm|terminate|deploy)\b|\s--prod\b)"
        ),
        "Changes or deletes cloud resources.",
    ),
]

_SECRET_READERS = {
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "bat",
    "xxd",
    "hexdump",
    "od",
    "strings",
    "base64",
    "nl",
    "tac",
    "grep",
    "rg",
    "awk",
    "sed",
    "scp",
    "rsync",
}

_DB_CLIENTS = {
    "psql",
    "mysql",
    "mariadb",
    "sqlite3",
    "sqlcmd",
    "clickhouse-client",
    "duckdb",
    "cockroach",
    "mongosh",
}


def check_simple(seg: list[str], cwd: str):
    prog = PurePath(seg[0]).name
    args = seg[1:]
    line = " ".join([prog] + args)

    if prog == "git":
        return check_git(seg, cwd)

    if prog == "rm":
        recursive = any(
            a in ("-r", "-R", "--recursive")
            or re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", a)
            for a in args
        )
        targets = [a for a in args if not a.startswith("-")]
        for t in targets:
            if _RM_HARD.match(t.rstrip("/") or "/"):
                return (
                    DENY,
                    f"Refusing `rm` on '{t}' (system or home root). Delete specific paths inside the project.",
                )
        if recursive and any(_RM_SOFT.match(t) for t in targets):
            return (
                ASK,
                "Recursive rm on the current directory, a glob, or .git. Name the exact paths, or confirm with the user.",
            )
        return None

    if prog == "find":
        roots = []
        for a in args:
            if a.startswith(("-", "(", "!")):
                break
            roots.append(a)
        destructive = "-delete" in args or any(
            a in ("-exec", "-execdir")
            and i + 1 < len(args)
            and PurePath(args[i + 1]).name in ("rm", "shred")
            for i, a in enumerate(args)
        )
        if destructive and any(_RM_HARD.match(r.rstrip("/") or "/") for r in roots):
            return (
                DENY,
                "Refusing a deleting `find` rooted at a system or home root. Scope it to a project path.",
            )
        return None

    if (
        prog in ("mkfs",)
        or prog.startswith("mkfs.")
        or prog in ("fdisk", "parted", "wipefs", "shred")
    ):
        return DENY, "Disk-level destructive command."
    if prog == "dd" and any(
        re.match(r"of=/dev/(sd|nvme|hd|xvd|disk|mmcblk)", a) for a in args
    ):
        return DENY, "dd onto a block device."
    if prog in ("shutdown", "reboot", "halt", "poweroff"):
        return DENY, "Don't power off the machine."
    if prog == "chmod" and any(
        re.fullmatch(r"-?[0-7]?777", a) or a in ("a+rwx", "ugo+rwx") for a in args
    ):
        if any(
            a == "/" or re.match(r"^/(etc|usr|bin|var|home|root)\b", a) for a in args
        ):
            return DENY, "World-writable permissions on system paths."
        if any(
            a in ("-R", "--recursive") or re.fullmatch(r"-[a-zA-Z]*R[a-zA-Z]*", a)
            for a in args
        ):
            return (
                ASK,
                "Recursive chmod 777 makes everything world-writable. Use the narrowest mode needed.",
            )

    if prog in _SECRET_READERS and any(
        is_secret_path(a) for a in args if not a.startswith("-")
    ):
        return (
            DENY,
            "This would print or copy a secrets file. Use .env.example / docs for names, or ask the user for the specific non-secret value.",
        )

    for rx, why in _ASK_PROGRAMS:
        if rx.search(line):
            return ASK, f"{why} Confirm with the user before running."
    if prog in _DB_CLIENTS and re.search(
        r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*;?\s*$)",
        line,
        re.I,
    ):
        return (
            ASK,
            "Destructive SQL (DROP/TRUNCATE/unfiltered DELETE). Confirm with the user and the target database.",
        )
    return None


_PIPE_TO_SHELL = re.compile(
    r"\b(curl|wget|fetch)\b[^;&]*\|\s*(sudo\s+)?(env\s+\S+\s+)?(ba|z|da|k)?sh\b|\b(curl|wget)\b[^;&]*\|\s*(sudo\s+)?python3?\b"
)
_EXFIL = re.compile(
    r"\b(printenv|env|set)\b\s*(\|\s*[^;&]*)?\|\s*[^;&]*\b(curl|wget|nc|ncat|socat)\b"
)
_UPLOAD_SECRET = re.compile(
    r"\b(curl|wget)\b[^;&]*(-d|--data(-binary|-raw|-urlencode)?|-F|--form|-T|--upload-file)\s*=?\s*['\"]?([\w.-]+=)?@?(\S*/)?(\.env(\.[\w-]+)?|id_rsa|id_ed25519|\S+\.pem|\.credentials\.json|credentials\.json)\b"
)


def check_bash(cmd: str, cwd: str):
    if not cmd.strip():
        return None
    if re.search(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", cmd):
        return DENY, "Fork bomb."
    if _EXFIL.search(cmd) or _UPLOAD_SECRET.search(cmd):
        return (
            DENY,
            "This sends environment variables or a secrets file over the network. Send only the specific non-secret values needed.",
        )
    if re.search(r">\s*/dev/(sd|nvme|hd|xvd|disk)", cmd):
        return DENY, "Writing directly to a block device."
    worst = None
    for seg in _expand(cmd):
        r = check_simple(seg, cwd)
        if r and r[0] == DENY:
            return r
        worst = worst or r
    if worst:
        return worst
    if _PIPE_TO_SHELL.search(cmd):
        return (
            ASK,
            "Piping a download into a shell runs unreviewed code. Download, inspect, then run — or confirm with the user.",
        )
    return None


# ---------------------------------------------------------------- main


def decide(event: dict):
    tool = event.get("tool_name", "")
    ti = event.get("tool_input") or {}
    cwd = event.get("cwd") or os.getcwd()
    if tool == "Bash":
        return check_bash(ti.get("command", ""), cwd)
    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        return check_file_tool(tool, ti, cwd)
    return None


def main() -> int:
    if os.environ.get("CLAUDE_GUARD", "").lower() in ("off", "0", "false"):
        return 0
    try:
        event = json.load(sys.stdin)
        result = decide(event)
    except Exception as e:  # fail open
        print(f"guard.py: internal error, allowing: {e}", file=sys.stderr)
        return 0
    if result:
        decision, reason = result
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": f"[guard] {reason}",
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
