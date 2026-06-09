#!/usr/bin/env python3
"""
git-yoda
========
A local agent that translates natural-language requests into `git` and
`gh` CLI commands and executes them. Wise it is, with the CLI.

Default safety model:
  - Commands MUST start with `git ` or `gh `. Anything else is rejected.
  - Read-only commands run immediately.
  - Write commands are previewed and require approval:
        --yes        : auto-approve everything (use with care)
        --dry-run    : never execute writes, just print them
        (default)    : interactive y/N prompt per write command

Usage:
  python git_yoda.py "open a PR with my current changes"
  python git_yoda.py "create a branch called feat/oauth-fix from main" --yes
  python git_yoda.py "what's the status of PR 142?"  # read-only, runs free
  python git_yoda.py "delete merged local branches" --dry-run

No external dependencies. Standard library only.

Environment:
  OLLAMA_URL          Default: http://localhost:11434/v1/chat/completions
  GIT_YODA_MODEL      Default: qwen3.6:27b
  GIT_YODA_MAX_TURNS  Default: 20
  GIT_YODA_NUM_CTX    Default: 16384
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
MODEL = os.environ.get("GIT_YODA_MODEL", "qwen3.6:27b")
MAX_TURNS = int(os.environ.get("GIT_YODA_MAX_TURNS", "20"))
NUM_CTX = int(os.environ.get("GIT_YODA_NUM_CTX", "16384"))

MAX_OUTPUT_BYTES = 8000
COMMAND_TIMEOUT = 60  # seconds


SYSTEM_PROMPT = """You are git-yoda, a focused git and GitHub CLI agent.

Your job: turn the user's natural-language request into the correct
`git` or `gh` commands, run them with the bash tool, and report results.

Rules:
- Use ONLY `git ` and `gh ` commands. The tool will reject anything else.
- ONE shell command per tool call. No `&&`, `||`, `;`, pipes, or redirects.
- Before any write (commit, push, branch -d, pr create, etc.), read first
  to know the current state: `git status --short`, `git branch --show-current`,
  `git log -n 5 --oneline`, `gh pr list`, etc.
- For PR creation, you MUST follow this exact sequence:
    1. `git status --short` and `git log <base>..HEAD --oneline` to confirm state
    2. `git pr-desc` to generate the structured description (writes to .git/PR_BODY.md)
    3. `gh pr create --title "<title>" --body-file .git/PR_BODY.md --base <base>`
  Pick the title from the most recent well-formed commit subject, or summarize
  the diff in <= 60 chars, imperative mood. Add --draft if the user said "WIP",
  "draft", or "not ready".
- If a destructive operation is ambiguous (delete which branches?), ask the
  user via a final answer instead of guessing.
- When done, reply with a short summary of what you did and the relevant
  URL/output, in plain text. No markdown headers.
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run",
            "description": "Run a single git or gh command. Read-only commands execute immediately; write commands may require approval. Returns stdout+stderr and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "A single command starting with 'git ' or 'gh '. No shell metacharacters (&&, ||, ;, |, >, <).",
                    },
                    "reason": {
                        "type": "string",
                        "description": "One short sentence explaining why you're running this.",
                    },
                },
                "required": ["command"],
            },
        }
    }
]


# ---------- command classification ----------

# Read-only git verbs (always safe)
READ_ONLY_GIT = {
    "status", "log", "diff", "show", "branch", "tag", "remote",
    "config", "fetch", "ls-files", "ls-remote", "rev-parse",
    "describe", "blame", "shortlog", "reflog", "stash",
    "for-each-ref", "cat-file", "name-rev", "whatchanged",
    "annotate", "grep", "merge-base", "rev-list",
    # Known safe aliases shipped with this kit
    "pr-desc",
}
# But some of these have write flags — narrow:
WRITE_GIT_BRANCH_FLAGS = {"-d", "-D", "--delete", "-m", "--move", "-c", "--copy"}
WRITE_GIT_TAG_FLAGS = {"-d", "--delete", "-f", "--force"}
WRITE_GIT_REMOTE_VERBS = {"add", "remove", "rm", "rename", "set-url", "set-head"}
WRITE_GIT_STASH_VERBS = {"push", "save", "pop", "apply", "drop", "clear", "create", "store"}
WRITE_GIT_CONFIG_FLAGS = {"--add", "--unset", "--unset-all", "--replace-all", "--rename-section", "--remove-section"}

# Write git verbs (always require approval)
WRITE_GIT = {
    "add", "commit", "push", "pull", "merge", "rebase", "reset",
    "checkout", "switch", "restore", "cherry-pick", "revert",
    "clean", "mv", "rm", "init", "clone", "submodule", "worktree",
    "am", "apply", "format-patch", "filter-branch", "filter-repo",
    "update-ref", "update-index", "gc", "prune", "repack",
    "notes", "bisect", "replace",
}

# gh: subcommand → kind
GH_READ_ONLY_SUBCOMMANDS = {
    ("auth", "status"), ("auth", "token"),
    ("pr", "list"), ("pr", "view"), ("pr", "status"), ("pr", "diff"), ("pr", "checks"),
    ("issue", "list"), ("issue", "view"), ("issue", "status"),
    ("repo", "view"), ("repo", "list"),
    ("release", "list"), ("release", "view"),
    ("workflow", "list"), ("workflow", "view"),
    ("run", "list"), ("run", "view"), ("run", "watch"),
    ("search", "repos"), ("search", "prs"), ("search", "issues"), ("search", "code"), ("search", "commits"),
    ("label", "list"),
    ("gist", "list"), ("gist", "view"),
    ("alias", "list"),
    ("api",),
}
GH_WRITE_SUBCOMMANDS = {
    ("pr", "create"), ("pr", "edit"), ("pr", "close"), ("pr", "reopen"),
    ("pr", "merge"), ("pr", "review"), ("pr", "ready"), ("pr", "comment"),
    ("pr", "checkout"), ("pr", "lock"), ("pr", "unlock"),
    ("issue", "create"), ("issue", "edit"), ("issue", "close"), ("issue", "reopen"),
    ("issue", "comment"), ("issue", "delete"), ("issue", "transfer"), ("issue", "pin"), ("issue", "unpin"),
    ("repo", "create"), ("repo", "clone"), ("repo", "delete"), ("repo", "rename"),
    ("repo", "fork"), ("repo", "archive"), ("repo", "unarchive"), ("repo", "edit"), ("repo", "sync"),
    ("release", "create"), ("release", "edit"), ("release", "delete"), ("release", "upload"),
    ("workflow", "run"), ("workflow", "enable"), ("workflow", "disable"),
    ("run", "cancel"), ("run", "rerun"), ("run", "delete"),
    ("label", "create"), ("label", "edit"), ("label", "delete"), ("label", "clone"),
    ("gist", "create"), ("gist", "edit"), ("gist", "delete"), ("gist", "clone"),
    ("alias", "set"), ("alias", "delete"),
    ("auth", "login"), ("auth", "logout"), ("auth", "refresh"), ("auth", "setup-git"),
    ("secret", "set"), ("secret", "delete"),
    ("variable", "set"), ("variable", "delete"),
    ("ssh-key", "add"), ("ssh-key", "delete"),
    ("gpg-key", "add"), ("gpg-key", "delete"),
}

# Tokens that, when standalone (after shlex.split), indicate the model is
# trying to write a shell pipeline. We reject these. Note: subprocess.run
# without shell=True means there's no actual shell interpretation, but
# accepting these would silently break in confusing ways.
SUSPICIOUS_TOKENS = {"&&", "||", ";", "|", ">", "<", ">>", "<<", "<<<"}


class CommandRejected(Exception):
    pass


def classify(cmd: str) -> tuple[str, str]:
    """Return (kind, reason). kind ∈ {'read', 'write', 'reject'}."""
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return ("reject", f"could not parse command: {e}")
    if not parts:
        return ("reject", "empty command")

    # Block standalone shell-pipeline tokens and command substitution.
    # Args quoted with these characters inside (e.g. --body "...;...") are fine
    # because shlex pulls them into a single token.
    for tok in parts:
        if tok in SUSPICIOUS_TOKENS:
            return ("reject", f"shell-pipeline token not allowed: {tok!r}")
        if tok.startswith("`") or "$(" in tok:
            return ("reject", f"command substitution not allowed in {tok!r}")

    head = parts[0]
    if head not in {"git", "gh"}:
        return ("reject", f"only git and gh are allowed, got {head!r}")

    if head == "git":
        return _classify_git(parts[1:])
    return _classify_gh(parts[1:])


def _strip_global_flags(args: list[str]) -> list[str]:
    # Skip leading global flags like `-C path`, `--git-dir=...`, `-c key=val`, `-p`
    out = list(args)
    while out and out[0].startswith("-"):
        if out[0] in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"} and len(out) > 1:
            out = out[2:]
        else:
            out = out[1:]
    return out


def _classify_git(args: list[str]) -> tuple[str, str]:
    args = _strip_global_flags(args)
    if not args:
        return ("read", "git with no subcommand (help)")
    verb = args[0]
    rest = args[1:]

    if verb in WRITE_GIT:
        return ("write", f"git {verb} mutates state")

    if verb == "branch":
        if any(f in WRITE_GIT_BRANCH_FLAGS for f in rest):
            return ("write", "git branch with delete/rename/copy flag")
        return ("read", "git branch (list)")
    if verb == "tag":
        if any(f in WRITE_GIT_TAG_FLAGS for f in rest) or (rest and not rest[0].startswith("-")):
            return ("write", "git tag (creation or delete)")
        return ("read", "git tag (list)")
    if verb == "remote":
        if rest and rest[0] in WRITE_GIT_REMOTE_VERBS:
            return ("write", f"git remote {rest[0]}")
        return ("read", "git remote (read)")
    if verb == "stash":
        if rest and rest[0] in WRITE_GIT_STASH_VERBS:
            return ("write", f"git stash {rest[0]}")
        return ("read", "git stash (list/show)")
    if verb == "config":
        if any(f in WRITE_GIT_CONFIG_FLAGS for f in rest):
            return ("write", "git config mutation")
        # `git config <key> <value>` is also a write
        non_flag = [a for a in rest if not a.startswith("-")]
        if len(non_flag) >= 2:
            return ("write", "git config set")
        return ("read", "git config read")
    if verb == "fetch":
        return ("read", "git fetch (network-only, no working-tree mutation)")

    if verb in READ_ONLY_GIT:
        return ("read", f"git {verb} is read-only")

    return ("write", f"git {verb} treated as write (unknown verb)")


def _classify_gh(args: list[str]) -> tuple[str, str]:
    args = _strip_global_flags(args)
    if not args:
        return ("read", "gh help")
    # Look at first two non-flag tokens
    non_flag = [a for a in args if not a.startswith("-")]
    if not non_flag:
        return ("read", "gh top-level flag")
    top = non_flag[0]
    sub = non_flag[1] if len(non_flag) > 1 else None

    if sub is None:
        return ("read", f"gh {top} alone")

    pair = (top, sub)
    if pair in GH_READ_ONLY_SUBCOMMANDS:
        return ("read", f"gh {top} {sub} is read-only")
    if pair in GH_WRITE_SUBCOMMANDS:
        # gh api with -X GET is read; assume default
        return ("write", f"gh {top} {sub} mutates state")
    if top == "api":
        # gh api defaults to GET; require explicit allow for other methods
        method = None
        i = 0
        while i < len(args):
            a = args[i]
            if a in {"-X", "--method"} and i + 1 < len(args):
                method = args[i + 1].upper()
                break
            if a.startswith("--method="):
                method = a.split("=", 1)[1].upper()
                break
            i += 1
        if method is None or method == "GET":
            return ("read", "gh api GET")
        return ("write", f"gh api {method}")
    # Unknown subcommand pair: be safe
    return ("write", f"gh {top} {sub} (unknown — treating as write)")


# ---------- approval ----------

def approve(cmd: str, reason: str, mode: str) -> bool:
    if mode == "yes":
        print(f"  [auto-approved] {cmd}", file=sys.stderr)
        return True
    if mode == "dry-run":
        print(f"  [DRY-RUN, would run] {cmd}", file=sys.stderr)
        return False
    # interactive
    print(f"\n  Proposed command: {cmd}", file=sys.stderr)
    print(f"  Reason: {reason or '(none)'}", file=sys.stderr)
    try:
        ans = input("  Run it? [y/N] ").strip().lower()
    except EOFError:
        ans = ""
    return ans in {"y", "yes"}


# ---------- execution ----------

def run_command(cmd: str, cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return (124, f"ERROR: command timed out after {COMMAND_TIMEOUT}s")
    except FileNotFoundError as e:
        return (127, f"ERROR: {e}")
    except Exception as e:
        return (1, f"ERROR: {e}")
    out = (proc.stdout or "") + (proc.stderr or "")
    if len(out) > MAX_OUTPUT_BYTES:
        out = out[:MAX_OUTPUT_BYTES] + "\n[... output truncated ...]"
    return (proc.returncode, out)


def tool_run(cmd: str, reason: str, cwd: Path, approval_mode: str) -> str:
    kind, why = classify(cmd)
    if kind == "reject":
        return f"REJECTED: {why}"
    if kind == "write":
        ok = approve(cmd, reason, approval_mode)
        if not ok:
            return "DENIED by user (or dry-run). Adjust plan or ask the user."
    code, out = run_command(cmd, cwd)
    return f"$ {cmd}\nexit={code}\n{out}" if out else f"$ {cmd}\nexit={code}"


# ---------- Ollama ----------

def call_ollama(messages: list[dict]) -> dict:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "temperature": 0.1,
            "options": {"num_ctx": NUM_CTX},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


# ---------- agent loop ----------

def run_agent(task: str, cwd: Path, approval_mode: str, verbose: bool) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Working directory: {cwd}\n"
                f"Approval mode: {approval_mode}\n\n"
                f"Task:\n{task}"
            ),
        },
    ]
    for turn in range(1, MAX_TURNS + 1):
        try:
            resp = call_ollama(messages)
        except urllib.error.URLError as e:
            return f"ERROR: cannot reach Ollama at {OLLAMA_URL}: {e}"
        except Exception as e:
            return f"ERROR: Ollama call failed: {e}"

        try:
            msg = resp["choices"][0]["message"]
        except (KeyError, IndexError):
            return f"ERROR: unexpected Ollama response: {resp}"
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return msg.get("content") or "(empty response)"

        for tc in tool_calls:
            fn = tc.get("function", {}).get("name", "")
            raw_args = tc.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            if fn != "run":
                result = f"ERROR: unknown tool {fn}"
            else:
                cmd = (args.get("command") or "").strip()
                reason = (args.get("reason") or "").strip()
                if verbose:
                    print(f"[turn {turn}] proposing: {cmd}", file=sys.stderr)
                result = tool_run(cmd, reason, cwd, approval_mode)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                }
            )
    return "ERROR: max turns reached without final answer"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="git-yoda: natural language → git/gh commands via local LLM"
    )
    parser.add_argument("task", help="What you want done.")
    parser.add_argument("--dir", default=".", help="Working directory (default: cwd).")
    approval = parser.add_mutually_exclusive_group()
    approval.add_argument("--yes", action="store_true", help="Auto-approve write commands.")
    approval.add_argument("--dry-run", action="store_true", help="Never execute writes.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    cwd = Path(args.dir).resolve()
    if not cwd.is_dir():
        print(f"ERROR: {cwd} is not a directory", file=sys.stderr)
        sys.exit(2)

    mode = "interactive"
    if args.yes:
        mode = "yes"
    elif args.dry_run:
        mode = "dry-run"

    print(run_agent(args.task, cwd, mode, args.verbose))


if __name__ == "__main__":
    main()
