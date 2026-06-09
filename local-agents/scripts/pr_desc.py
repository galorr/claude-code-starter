#!/usr/bin/env python3
"""
pr-desc
=======
Convert the current branch's diff vs. base into a structured PR description
with sections: What / Why / How to Test / Risks.

Designed to be installed as a git alias:
    git config --global alias.pr-desc "!python3 $HOME/local-agents/scripts/pr_desc.py"

After which:
    git pr-desc                              # auto-detect base, print to stdout
    git pr-desc --base origin/develop
    git pr-desc --context "fixes flaky CI"   # extra hint for the Why section
    git pr-desc | pbcopy                     # macOS clipboard

Side effect (when run inside a git repo):
    Writes the same body to .git/PR_BODY.md so you can do:
        gh pr create --title "..." --body-file .git/PR_BODY.md

No external dependencies. Standard library only.

Environment:
  OLLAMA_URL          Default: http://localhost:11434/v1/chat/completions
  PR_DESC_MODEL       Default: qwen3.6:27b
  PR_DESC_NUM_CTX     Default: 32768
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
MODEL = os.environ.get("PR_DESC_MODEL", "qwen3.6:27b")
NUM_CTX = int(os.environ.get("PR_DESC_NUM_CTX", "32768"))

# Hard caps on what we send to the model
MAX_DIFF_CHARS = 60_000     # full diff cap
MAX_COMMITS_CHARS = 6_000   # cap commit log
MAX_STAT_CHARS = 4_000      # cap diffstat


SYSTEM_PROMPT = """You are a senior engineer writing a clear, structured pull request description.

Output EXACTLY four sections in this order, in plain markdown, with no preamble
and no trailing chatter:

## What
2–4 sentences in plain language describing what changed. Reference the most
impactful files or symbols by name. No bullets here — prose.

## Why
The motivation. Use the branch name, commit messages, and any author-provided
context. If genuine context is missing, write ONE bullet starting with
"- Context:" containing your best guess from the commits, and append
"[needs author input]" at the end of that bullet.

## How to Test
3–6 concrete bullets. Each bullet is something a reviewer can actually do.
Include exact commands when relevant (e.g. `npm run test -- auth.spec.ts`,
`curl -X POST /api/foo`). If new automated tests were added, mention them
in the first bullet.

## Risks
2–4 bullets focused on: blast radius, irreversible changes, performance,
security, backwards compatibility, missing coverage, migrations / schema
changes, generated or lock files. If genuinely low-risk, say so in one
short bullet rather than padding.

Hard rules:
- Do NOT wrap the whole output in code fences.
- Do NOT include any section other than the four above.
- Do NOT include a title — only the body.
- Do NOT invent facts that aren't in the diff or context.
- Keep the total under ~400 words.
"""


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return (proc.returncode, (proc.stdout or "") + (proc.stderr or ""))
    except subprocess.TimeoutExpired:
        return (124, f"timeout after {timeout}s")
    except FileNotFoundError as e:
        return (127, str(e))
    except Exception as e:
        return (1, str(e))


def detect_base() -> str:
    """Best-effort base detection. Prefers origin/HEAD."""
    code, out = run(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"])
    if code == 0 and out.strip() and "/" in out.strip():
        return out.strip()
    for candidate in ("origin/main", "origin/master", "origin/develop", "main", "master"):
        code, _ = run(["git", "rev-parse", "--verify", candidate])
        if code == 0:
            return candidate
    return "origin/main"


def gather(base: str) -> dict:
    _, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch.strip()

    _, commits = run(
        ["git", "log", f"{base}..HEAD", "--pretty=format:%h %s%n%b%n---"]
    )
    if len(commits) > MAX_COMMITS_CHARS:
        commits = commits[:MAX_COMMITS_CHARS] + "\n[... commits truncated ...]"

    _, stat = run(["git", "diff", f"{base}...HEAD", "--stat"])
    if len(stat) > MAX_STAT_CHARS:
        stat = stat[:MAX_STAT_CHARS] + "\n[... stat truncated ...]"

    _, diff = run(["git", "diff", f"{base}...HEAD"])
    truncated = False
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS]
        truncated = True

    return {
        "branch": branch,
        "commits": commits.strip() or "(no commits)",
        "stat": stat.strip() or "(no changes)",
        "diff": diff.strip() or "(empty)",
        "diff_truncated": truncated,
    }


def build_user_message(info: dict, base: str, context: str) -> str:
    blocks: list[str] = []
    if context:
        blocks.append(f"## Author-provided context\n{context.strip()}\n")
    blocks.append(f"Base: {base}")
    blocks.append(f"Source branch: {info['branch']}")
    blocks.append("\n## Commits on this branch\n" + info["commits"])
    blocks.append("\n## Diffstat\n" + info["stat"])
    blocks.append("\n## Diff\n" + info["diff"])
    if info["diff_truncated"]:
        blocks.append(f"\n[... diff truncated at {MAX_DIFF_CHARS} chars ...]")
    return "\n".join(blocks)


def call_ollama(messages: list[dict]) -> dict:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 0.3,
            "options": {"num_ctx": NUM_CTX},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def write_pr_body_file(content: str) -> Path | None:
    """Write to .git/PR_BODY.md so it can be used with --body-file."""
    code, git_dir = run(["git", "rev-parse", "--git-dir"])
    if code != 0:
        return None
    target = Path(git_dir.strip()) / "PR_BODY.md"
    try:
        target.write_text(content, encoding="utf-8")
        return target
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a structured PR description from the current branch diff."
    )
    parser.add_argument(
        "--base", help="Base ref (default: auto-detect origin/HEAD)."
    )
    parser.add_argument(
        "--context", default="",
        help="Extra context to feed the 'Why' section (e.g. ticket summary).",
    )
    parser.add_argument(
        "--dir", default=".", help="Repo root (default: cwd)."
    )
    parser.add_argument(
        "--no-write", action="store_true",
        help="Don't write .git/PR_BODY.md, only print to stdout.",
    )
    args = parser.parse_args()

    try:
        os.chdir(args.dir)
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    code, _ = run(["git", "rev-parse", "--show-toplevel"])
    if code != 0:
        print("ERROR: not inside a git repository", file=sys.stderr)
        sys.exit(2)

    base = args.base or detect_base()
    code, _ = run(["git", "rev-parse", "--verify", base])
    if code != 0:
        print(
            f"ERROR: base ref {base!r} not found. Try --base origin/main or run `git fetch`.",
            file=sys.stderr,
        )
        sys.exit(2)

    info = gather(base)
    if info["diff"] == "(empty)":
        print(
            f"ERROR: no diff between HEAD and {base}. "
            "Did you commit, or is your branch up-to-date with base?",
            file=sys.stderr,
        )
        sys.exit(2)

    user_msg = build_user_message(info, base, args.context)

    try:
        resp = call_ollama(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ]
        )
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach Ollama at {OLLAMA_URL}: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: Ollama call failed: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        content = resp["choices"][0]["message"].get("content", "").strip()
    except (KeyError, IndexError):
        print(f"ERROR: unexpected Ollama response: {resp}", file=sys.stderr)
        sys.exit(2)

    if not content:
        print("ERROR: model returned empty response", file=sys.stderr)
        sys.exit(2)

    print(content)

    if not args.no_write:
        target = write_pr_body_file(content)
        if target is not None:
            print(f"\n[wrote body to {target}]", file=sys.stderr)


if __name__ == "__main__":
    main()
