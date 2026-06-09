#!/usr/bin/env python3
"""
codebase-qa
===========
An internal "ask the codebase anything" bot. Point it at ANY repo and ask a
question in plain English; it explores the repo with a local LLM (grep / read /
glob in a tool loop) and returns a direct, cited answer.

This is the interactive, on-any-repo cousin of the knowledge-transfer (KT)
agent: instead of pre-generating a docs tree, it answers live, so the answer is
always current and there is no index to maintain. It is designed to be exposed
as a tool inside Claude Desktop (see ../mcp/server.py).

Every Q&A pair is optionally written to SHARED memory (kind="qa"), and prior
Q&A for the same repo is recalled first — so repeated/related questions get
faster, more consistent answers and institutional knowledge accumulates.

Usage:
  python codebase_qa.py "How is auth validated and where?" --repo ~/code/growth
  python codebase_qa.py "What env vars are required at startup?" --repo .
  python codebase_qa.py "Where are Mongo queries and which collections?" --repo . --no-memory

No third-party deps for Q&A; memory needs `pymongo` (see memory.py).

Environment:
  OLLAMA_URL              Default: http://localhost:11434/v1/chat/completions
  CODEBASE_QA_MODEL       Default: qwen3.6:27b
  CODEBASE_QA_MAX_TURNS   Default: 30
  CODEBASE_QA_NUM_CTX     Default: 32768
  (plus memory.py env vars)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory  # noqa: E402

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
MODEL = os.environ.get("CODEBASE_QA_MODEL", "qwen3.6:27b")
MAX_TURNS = int(os.environ.get("CODEBASE_QA_MAX_TURNS", "30"))
NUM_CTX = int(os.environ.get("CODEBASE_QA_NUM_CTX", "32768"))

MAX_FILE_BYTES = 200_000
MAX_GREP_MATCHES = 200
MAX_GLOB_MATCHES = 500
MAX_TOOL_OUTPUT = 12_000
IGNORED_DIRS = {
    "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".git", "target", ".next", ".turbo",
    "coverage", ".pytest_cache", ".mypy_cache",
}

SYSTEM_PROMPT = """You are codebase-qa, an internal expert on THIS repository.

A teammate asks a question; you answer it accurately by reading the code
yourself, then giving a direct, well-cited answer. The asker cannot see the
files — your answer must stand alone.

Tools:
- list_dir / read_file / grep / glob : explore the repo.
- prior_qa(query)                    : retrieve previous Q&A about this repo
                                       from shared memory. Call it FIRST — a
                                       teammate may have asked something similar.

How to answer well:
- Begin with prior_qa() on the question, then list_dir('.') to orient.
- Use grep to locate things before reading whole files. Read only what you need.
- ALWAYS cite concrete evidence as `path:line`. Quote short snippets only when
  they materially help; never paste large blocks.
- Be direct: lead with the answer, then the supporting detail, then "where to
  look" (the key files). If the repo genuinely doesn't do the thing asked, say
  so and show what you checked.
- If the question is ambiguous, answer the most likely interpretation and note
  the assumption.
- When confident, STOP calling tools and give the final answer in markdown:
    a short direct answer, then **Details**, then **Where to look** (file list).
"""


def _safe_path(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Path escapes repo root: {rel}")
    return target


def _is_ignored(rel_parts: tuple[str, ...]) -> bool:
    if any(p.startswith(".") and p not in (".",) for p in rel_parts):
        return True
    return any(p in IGNORED_DIRS for p in rel_parts)


def tool_list_dir(root: Path, path: str) -> str:
    p = _safe_path(root, path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if not p.is_dir():
        return f"ERROR: {path} is not a directory"
    entries = []
    for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:200]:
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
    text = data[:MAX_FILE_BYTES].decode("utf-8", errors="replace")
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


def tool_prior_qa(query: str, namespace: str) -> str:
    try:
        return memory.format_recall(
            memory.recall(query, namespace=namespace, k=4, kinds=["qa", "note", "decision"])
        )
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List files/subdirs at a path relative to repo root.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Relative path. '.' for root."}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": f"Read a file relative to repo root. Truncated at {MAX_FILE_BYTES} bytes.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "grep",
        "description": f"Search a Python regex across files (max {MAX_GREP_MATCHES} hits as path:line: text).",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "glob": {"type": "string", "description": "Filename glob like '*.ts'."}},
            "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "glob",
        "description": f"Find files by glob relative to root (max {MAX_GLOB_MATCHES}). '**/*.ext' recurses.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "prior_qa",
        "description": "Retrieve previous Q&A / notes about THIS repo from shared memory.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
]


def dispatch(name: str, args: dict, root: Path, namespace: str) -> str:
    try:
        if name == "list_dir":
            return tool_list_dir(root, args["path"])
        if name == "read_file":
            return tool_read_file(root, args["path"])
        if name == "grep":
            return tool_grep(root, args["pattern"], args.get("path", "."), args.get("glob"))
        if name == "glob":
            return tool_glob(root, args["pattern"])
        if name == "prior_qa":
            return tool_prior_qa(args["query"], namespace)
        return f"ERROR: unknown tool {name}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


def call_ollama(messages: list[dict]) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": False,
        "temperature": 0.2,
        "options": {"num_ctx": NUM_CTX},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def answer(question: str, root: Path, namespace: str, verbose: bool = False) -> str:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Repository root: {root}\nMemory namespace: {namespace}\n\nQuestion:\n{question}"},
    ]
    for turn in range(1, MAX_TURNS + 1):
        try:
            resp = call_ollama(messages)
        except urllib.error.URLError as e:
            return f"ERROR: cannot reach Ollama at {OLLAMA_URL}: {e}"
        except Exception as e:  # noqa: BLE001
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
            if verbose:
                print(f"[turn {turn}] {fn}({json.dumps(args)[:120]})", file=sys.stderr)
            result = dispatch(fn, args, root, namespace)
            if len(result) > MAX_TOOL_OUTPUT:
                result = result[:MAX_TOOL_OUTPUT] + "\n[... output truncated ...]"
            messages.append({
                "role": "tool", "tool_call_id": tc.get("id", ""), "content": result,
            })
    return "ERROR: max turns reached without final answer"


def main() -> None:
    p = argparse.ArgumentParser(description="codebase-qa: ask any repo a question.")
    p.add_argument("question", help="What you want to know about the repo.")
    p.add_argument("--repo", default=".", help="Repo root (default: cwd).")
    p.add_argument("--namespace", default=None,
                   help="Memory namespace (default: repo dir name).")
    p.add_argument("--no-memory", action="store_true",
                   help="Don't write this Q&A to shared memory.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    namespace = args.namespace or root.name

    result = answer(args.question, root, namespace, args.verbose)
    print(result)

    if not args.no_memory and not result.startswith("ERROR"):
        try:
            memory.remember(
                f"Q: {args.question}\nA: {result}",
                namespace=namespace, kind="qa", agent="codebase-qa",
            )
            print("\n[Q&A saved to shared memory]", file=sys.stderr)
        except memory.MemoryUnavailable as e:
            print(f"\n[Q&A not saved — memory unavailable: {e}]", file=sys.stderr)


if __name__ == "__main__":
    main()
