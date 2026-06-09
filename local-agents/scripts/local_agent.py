#!/usr/bin/env python3
"""
local-agent
===========
A local LLM helper for LONG Claude Code / Claude Desktop tasks. It does three
jobs the orchestrator otherwise burns its own context window on:

1. EXPLORE  — read files, grep, glob in its own context and return ONE summary
              (same as local-explorer, kept here so this is a drop-in superset).
2. REMEMBER — persist findings/decisions to a SHARED memory store (MongoDB
              Atlas vector search) so any agent can recall them later.
3. HANDOVER — when a session gets long, produce a structured handover note and
              save it to shared memory; a fresh session can `--resume` from it.

Runs on a local model (default Qwen3.6 27B via Ollama). The model is given the
file tools PLUS two memory tools (remember, recall), so during a long task it
can stash and retrieve context on its own.

Usage:
  # explore + auto-recall relevant prior memory, namespaced by repo
  python local_agent.py "trace the /api/users request lifecycle" --dir . --namespace growth

  # write a handover note for the current session and store it
  python local_agent.py --handover "finished auth refactor, tests green" \
      --dir . --namespace growth --session oauth-fix

  # start a new session by loading the latest handover + relevant memory
  python local_agent.py "continue where we left off on auth" \
      --dir . --namespace growth --session oauth-fix --resume

  # just recall, no exploration
  python local_agent.py --recall "how does auth validation work" --namespace growth

Memory is OPTIONAL. If MONGODB_URI is unset (or Atlas/Ollama-embeddings are
unreachable), exploration still works; memory tools degrade to a clear notice.

No third-party deps for exploration; memory needs `pymongo` (see memory.py).

Environment:
  OLLAMA_URL              Default: http://localhost:11434/v1/chat/completions
  LOCAL_AGENT_MODEL       Default: qwen3.6:27b
  LOCAL_AGENT_MAX_TURNS   Default: 30
  LOCAL_AGENT_NUM_CTX     Default: 32768
  (plus all memory.py env vars: MONGODB_URI, MEMORY_*, OLLAMA_EMBED_URL, ...)
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

# memory.py lives next to this file; import it without requiring a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory  # noqa: E402

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
MODEL = os.environ.get("LOCAL_AGENT_MODEL", "qwen3.6:27b")
MAX_TURNS = int(os.environ.get("LOCAL_AGENT_MAX_TURNS", "30"))
NUM_CTX = int(os.environ.get("LOCAL_AGENT_NUM_CTX", "32768"))

MAX_FILE_BYTES = 200_000
MAX_GREP_MATCHES = 200
MAX_GLOB_MATCHES = 500
MAX_TOOL_OUTPUT = 12_000
IGNORED_DIRS = {
    "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".git", "target", ".next", ".turbo",
    "coverage", ".pytest_cache", ".mypy_cache",
}

SYSTEM_PROMPT = """You are local-agent, a focused codebase + memory assistant.

You support a long-running orchestrator (Claude Code / Claude Desktop) by doing
work in YOUR OWN context and returning only a compact result. The orchestrator
will NOT see the files you read — only your final summary.

Tools available:
- list_dir / read_file / grep / glob : explore the codebase.
- recall(query)                      : search SHARED memory for prior findings,
                                       decisions, and handovers. Call this EARLY
                                       if the task references past work.
- remember(text, kind)               : persist a durable finding or decision to
                                       shared memory so future sessions/agents
                                       can recall it. Use kind="decision" for
                                       choices made, "note" for facts learned.

Rules:
- Start by orienting: recall() if the task hints at prior work, then list_dir('.').
- Prefer grep over reading whole files. Cite concrete file paths and line numbers.
- Persist only durable, reusable facts with remember() — not transient steps.
- When done, STOP calling tools and reply with ONE concise markdown summary,
  complete enough that the orchestrator need not re-read the files.
- If something is impossible (missing path, memory unavailable), say so plainly.
"""

HANDOVER_PROMPT = """You are local-agent writing a CONTEXT HANDOVER so a fresh
session can resume with zero prior chat history. Be precise and self-contained.

Use these tools to ground the handover in the real repo state if helpful:
list_dir, read_file, grep, glob, recall.

Produce a markdown handover with EXACTLY these sections:

## State
What is the current state of the work? Branch, what's done, what's verified.

## Key Files
Bullet list of the files that matter, each with a one-line "why it matters".

## Decisions
Decisions made so far and their rationale. If none, say "none yet".

## Next Steps
Ordered, concrete next actions the resuming session should take.

## Open Questions
Anything ambiguous or needing the human's input. If none, say "none".

Keep it under ~400 words. No preamble, no code fences around the whole thing.
"""


# ---------- path safety ----------

def _safe_path(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"Path escapes project root: {rel}")
    return target


def _is_ignored(rel_parts: tuple[str, ...]) -> bool:
    if any(p.startswith(".") and p not in (".",) for p in rel_parts):
        return True
    return any(p in IGNORED_DIRS for p in rel_parts)


# ---------- file tools ----------

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


# ---------- memory tools (exposed to the model) ----------

def tool_recall(query: str, namespace: str) -> str:
    try:
        results = memory.recall(query, namespace=namespace, k=5)
        return memory.format_recall(results)
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


def tool_remember(text: str, namespace: str, session: str | None, kind: str) -> str:
    try:
        _id = memory.remember(
            text, namespace=namespace, kind=kind or "note",
            agent="local-agent", session=session,
        )
        return f"stored memory {_id} (kind={kind or 'note'})"
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


# ---------- tool schema ----------

def build_tools() -> list[dict]:
    return [
        {"type": "function", "function": {
            "name": "list_dir",
            "description": "List files/subdirs at a path relative to project root. Ignores junk dirs.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "Relative path. '.' for root."}},
                "required": ["path"]}}},
        {"type": "function", "function": {
            "name": "read_file",
            "description": f"Read a file relative to project root. Truncated at {MAX_FILE_BYTES} bytes.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {
            "name": "grep",
            "description": f"Search a Python regex across files (max {MAX_GREP_MATCHES} hits as path:line: text).",
            "parameters": {"type": "object", "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "Subdir; '.' for whole project."},
                "glob": {"type": "string", "description": "Filename glob like '*.ts'."}},
                "required": ["pattern"]}}},
        {"type": "function", "function": {
            "name": "glob",
            "description": f"Find files by glob relative to root (max {MAX_GLOB_MATCHES}). Use '**/*.ext' to recurse.",
            "parameters": {"type": "object", "properties": {
                "pattern": {"type": "string"}}, "required": ["pattern"]}}},
        {"type": "function", "function": {
            "name": "recall",
            "description": "Search SHARED memory for prior findings/decisions/handovers relevant to a query.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"}}, "required": ["query"]}}},
        {"type": "function", "function": {
            "name": "remember",
            "description": "Persist a durable finding or decision to SHARED memory for future recall.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"},
                "kind": {"type": "string", "description": "'note' or 'decision'."}},
                "required": ["text"]}}},
    ]


def dispatch(name: str, args: dict, root: Path, namespace: str, session: str | None) -> str:
    try:
        if name == "list_dir":
            return tool_list_dir(root, args["path"])
        if name == "read_file":
            return tool_read_file(root, args["path"])
        if name == "grep":
            return tool_grep(root, args["pattern"], args.get("path", "."), args.get("glob"))
        if name == "glob":
            return tool_glob(root, args["pattern"])
        if name == "recall":
            return tool_recall(args["query"], namespace)
        if name == "remember":
            return tool_remember(args["text"], namespace, session, args.get("kind", "note"))
        return f"ERROR: unknown tool {name}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


# ---------- Ollama ----------

def call_ollama(messages: list[dict], tools: list[dict]) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "tools": tools,
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


# ---------- agent loop ----------

def run_agent(
    task: str, root: Path, namespace: str, session: str | None,
    system_prompt: str, seed_context: str = "", verbose: bool = False,
) -> str:
    tools = build_tools()
    user = f"Project root: {root}\nMemory namespace: {namespace}\n"
    if session:
        user += f"Session: {session}\n"
    if seed_context:
        user += f"\n## Loaded context (from shared memory)\n{seed_context}\n"
    user += f"\nTask:\n{task}"

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]
    for turn in range(1, MAX_TURNS + 1):
        try:
            resp = call_ollama(messages, tools)
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
            result = dispatch(fn, args, root, namespace, session)
            if len(result) > MAX_TOOL_OUTPUT:
                result = result[:MAX_TOOL_OUTPUT] + "\n[... output truncated ...]"
            messages.append({
                "role": "tool", "tool_call_id": tc.get("id", ""), "content": result,
            })
    return "ERROR: max turns reached without final answer"


# ---------- high-level modes ----------

def do_explore(task, root, namespace, session, resume, verbose) -> str:
    seed = ""
    if resume:
        parts = []
        try:
            h = memory.latest_handover(namespace, session)
            if h:
                parts.append("### Latest handover\n" + h.get("text", ""))
        except memory.MemoryUnavailable as e:
            parts.append(f"(handover unavailable: {e})")
        try:
            rel = memory.recall(task, namespace=namespace, k=5)
            if rel:
                parts.append("### Relevant memories\n" + memory.format_recall(rel))
        except memory.MemoryUnavailable:
            pass
        seed = "\n\n".join(parts)
    return run_agent(task, root, namespace, session, SYSTEM_PROMPT, seed, verbose)


def do_handover(note, root, namespace, session, verbose) -> str:
    task = (
        "Write the handover. The human's one-line note about the current state "
        f"is: {note!r}. Ground it in the repo and any relevant prior memory."
    )
    summary = run_agent(task, root, namespace, session, HANDOVER_PROMPT, "", verbose)
    if summary.startswith("ERROR"):
        return summary
    try:
        _id = memory.save_handover(
            summary, namespace=namespace, session=session or "default",
            agent="local-agent", meta={"note": note},
        )
        return summary + f"\n\n[handover saved to shared memory: {_id}]"
    except memory.MemoryUnavailable as e:
        return summary + f"\n\n[NOT saved — memory unavailable: {e}]"


def do_recall(query, namespace) -> str:
    try:
        return memory.format_recall(memory.recall(query, namespace=namespace, k=8))
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


def main() -> None:
    p = argparse.ArgumentParser(
        description="local-agent: long-task helper with shared memory + handover."
    )
    p.add_argument("task", nargs="?", help="Exploration task / question.")
    p.add_argument("--dir", default=".", help="Project root (default: cwd).")
    p.add_argument("--namespace", default=None,
                   help="Memory namespace (default: repo dir name).")
    p.add_argument("--session", default=None, help="Session id to group memory.")
    p.add_argument("--resume", action="store_true",
                   help="Seed the task with latest handover + relevant memory.")
    p.add_argument("--handover", metavar="NOTE",
                   help="Produce + store a handover. NOTE is your one-line status.")
    p.add_argument("--recall", metavar="QUERY",
                   help="Only recall memories matching QUERY; no exploration.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    root = Path(args.dir).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    namespace = args.namespace or root.name

    if args.recall:
        print(do_recall(args.recall, namespace))
        return
    if args.handover:
        print(do_handover(args.handover, root, namespace, args.session, args.verbose))
        return
    if not args.task:
        print("ERROR: provide a task, or use --handover / --recall", file=sys.stderr)
        sys.exit(2)
    print(do_explore(args.task, root, namespace, args.session, args.resume, args.verbose))


if __name__ == "__main__":
    main()
