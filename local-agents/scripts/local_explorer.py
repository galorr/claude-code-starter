#!/usr/bin/env python3
"""
local-explorer
==============
A focused file-exploration agent that runs entirely on a local LLM
(default: Qwen3.6 27B via Ollama). It reads files, greps, and lists
directories on your behalf, then returns ONE concise summary.

Designed to be invoked either:
  - Directly from the terminal:
      python local_explorer.py "what does the auth layer do?" --dir ~/code/repo
  - From a Claude Code subagent via Bash (handover / context savings)

No external dependencies. Standard library only.

Environment:
  OLLAMA_URL              Default: http://localhost:11434/v1/chat/completions
  LOCAL_EXPLORER_MODEL    Default: qwen3.6:27b
  LOCAL_EXPLORER_MAX_TURNS Default: 30
  LOCAL_EXPLORER_NUM_CTX  Default: 32768
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
MODEL = os.environ.get("LOCAL_EXPLORER_MODEL", "qwen3.6:27b")
MAX_TURNS = int(os.environ.get("LOCAL_EXPLORER_MAX_TURNS", "30"))
NUM_CTX = int(os.environ.get("LOCAL_EXPLORER_NUM_CTX", "32768"))

MAX_FILE_BYTES = 200_000          # cap per file read
MAX_GREP_MATCHES = 200            # cap total grep matches
MAX_GLOB_MATCHES = 500            # cap total glob matches
MAX_TOOL_OUTPUT = 12_000          # cap fed back to the model
IGNORED_DIRS = {
    "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".git", "target", ".next", ".turbo",
    "coverage", ".pytest_cache", ".mypy_cache",
}

SYSTEM_PROMPT = """You are local-explorer, a focused file-exploration agent.

Your job: answer the user's question about a codebase by reading files
yourself, then return ONE concise summary. The orchestrator will NOT see
the files you read — only your final summary. Make it complete enough that
they don't need to re-read.

Rules:
- Start with list_dir on '.' to orient yourself.
- Prefer grep over reading whole files. Read whole files only when needed.
- Reference findings with concrete file paths and line numbers.
- Do NOT include large code blocks unless directly necessary.
- When you have enough information, STOP calling tools and reply with the
  final summary in plain markdown.
- If the task is impossible (path doesn't exist, etc.), say so plainly.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and subdirectories at a path (relative to project root). Returns up to 200 entries. Ignores common junk (node_modules, .git, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path. Use '.' for project root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": f"Read a file's contents (relative to project root). Truncated at {MAX_FILE_BYTES} bytes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": f"Search for a Python regex pattern across files. Returns up to {MAX_GREP_MATCHES} matching lines as 'path:line: content'. Skips junk dirs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Python regex."},
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search; use '.' for whole project.",
                    },
                    "glob": {
                        "type": "string",
                        "description": "Optional filename glob like '*.py' or '*.ts'.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": f"Find files matching a glob pattern relative to project root. Up to {MAX_GLOB_MATCHES} results. Use '**/*.ext' to recurse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
]


# ---------- path safety ----------

def _safe_path(root: Path, rel: str) -> Path:
    """Resolve `rel` under `root` and prevent escape via .."""
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Path escapes project root: {rel}")
    return target


def _is_ignored(rel_parts: tuple[str, ...]) -> bool:
    if any(p.startswith(".") and p not in (".",) for p in rel_parts):
        return True
    return any(p in IGNORED_DIRS for p in rel_parts)


# ---------- tools ----------

def tool_list_dir(root: Path, path: str) -> str:
    p = _safe_path(root, path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if not p.is_dir():
        return f"ERROR: {path} is not a directory"
    entries = []
    children = sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))
    for child in children[:200]:
        if child.name.startswith("."):
            continue
        if child.is_dir() and child.name in IGNORED_DIRS:
            continue
        if child.is_dir():
            entries.append(f"dir   {child.name}/")
        else:
            try:
                size = child.stat().st_size
            except OSError:
                size = 0
            entries.append(f"file  {child.name}  ({size} bytes)")
    return "\n".join(entries) or "(empty)"


def tool_read_file(root: Path, path: str) -> str:
    p = _safe_path(root, path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if not p.is_file():
        return f"ERROR: {path} is not a file"
    try:
        data = p.read_bytes()[: MAX_FILE_BYTES + 1]
    except OSError as e:
        return f"ERROR: {e}"
    truncated = len(data) > MAX_FILE_BYTES
    data = data[:MAX_FILE_BYTES]
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n[... truncated at {MAX_FILE_BYTES} bytes ...]"
    return text


def tool_grep(root: Path, pattern: str, path: str = ".", glob: str | None = None) -> str:
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: invalid regex: {e}"
    start = _safe_path(root, path)
    if not start.exists():
        return f"ERROR: {path} does not exist"
    matches: list[str] = []
    for fp in start.rglob("*"):
        if not fp.is_file():
            continue
        rel = fp.relative_to(root)
        if _is_ignored(rel.parts):
            continue
        if glob and not fnmatch.fnmatch(fp.name, glob):
            continue
        try:
            with fp.open("r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        matches.append(f"{rel}:{i}: {line.rstrip()}")
                        if len(matches) >= MAX_GREP_MATCHES:
                            return "\n".join(matches) + "\n[... more matches truncated ...]"
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(matches) or "(no matches)"


def tool_glob(root: Path, pattern: str) -> str:
    matches: list[str] = []
    for fp in root.glob(pattern):
        rel = fp.relative_to(root)
        if _is_ignored(rel.parts):
            continue
        matches.append(str(rel))
        if len(matches) >= MAX_GLOB_MATCHES:
            break
    return "\n".join(matches) or "(no matches)"


def dispatch(name: str, args: dict, root: Path) -> str:
    try:
        if name == "list_dir":
            return tool_list_dir(root, args["path"])
        if name == "read_file":
            return tool_read_file(root, args["path"])
        if name == "grep":
            return tool_grep(
                root, args["pattern"], args.get("path", "."), args.get("glob")
            )
        if name == "glob":
            return tool_glob(root, args["pattern"])
        return f"ERROR: unknown tool {name}"
    except Exception as e:
        return f"ERROR: {e}"


# ---------- Ollama call ----------

def call_ollama(messages: list[dict]) -> dict:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "temperature": 0.2,
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


# ---------- agent loop ----------

def run_agent(task: str, root: Path, verbose: bool = False) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Project root: {root}\n\nTask:\n{task}",
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

        # Persist the assistant message (with any tool_calls)
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            content = msg.get("content") or "(empty response)"
            if verbose:
                print(f"[turn {turn}] final answer ({len(content)} chars)", file=sys.stderr)
            return content

        for tc in tool_calls:
            fn = tc.get("function", {}).get("name", "")
            raw_args = tc.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            if verbose:
                short = json.dumps(args)[:120]
                print(f"[turn {turn}] {fn}({short})", file=sys.stderr)
            result = dispatch(fn, args, root)
            if len(result) > MAX_TOOL_OUTPUT:
                result = result[:MAX_TOOL_OUTPUT] + "\n[... output truncated ...]"
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
        description="local-explorer: file exploration via local LLM"
    )
    parser.add_argument("task", help="What to explore or answer.")
    parser.add_argument("--dir", default=".", help="Project root (default: cwd).")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(2)

    print(run_agent(args.task, root, args.verbose))


if __name__ == "__main__":
    main()
