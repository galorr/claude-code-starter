#!/usr/bin/env python3
"""
local-agents MCP server
=======================
Exposes the local-agents kit as tools inside Claude Desktop (or any MCP client).
The heavy lifting still runs on your LOCAL model (Qwen via Ollama); this server
is a thin, typed wrapper so Desktop can call the agents like any other tool.

Tools exposed:
  - codebase_qa        : ask any repo a question (cited answer, local LLM)
  - explore            : run local-agent exploration over a repo (with shared memory)
  - explore_lite       : lightweight file exploration with no memory requirement
  - save_handover      : write a context-handover note for a session
  - latest_handover    : fetch the most recent handover for a namespace/session
  - memory_remember    : store a durable note/decision in shared memory
  - memory_recall      : semantic search over shared memory
  - git_yoda           : natural-language git/gh (DRY-RUN by default; writes need
                         allow_writes=true, since Desktop can't do y/N prompts)
  - pr_desc            : generate a structured PR description from the current branch diff

Install (one-time):
  pip install "mcp[cli]" pymongo

Register in Claude Desktop (claude_desktop_config.json) — see
docs/claude_desktop_config.example.json. The "env" block there is how you pass
MONGODB_URI, model names, etc. to this server.

Safety: git_yoda defaults to DRY-RUN. It will only execute write commands when
the caller explicitly passes allow_writes=true. Read-only git/gh always runs.
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stderr
from pathlib import Path

# Make the sibling scripts/ importable.
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import memory  # noqa: E402
import local_agent  # noqa: E402
import local_explorer as le_mod  # noqa: E402  (aliased: tool below is named explore_lite)
import codebase_qa as qa_mod  # noqa: E402  (aliased: tool below is named codebase_qa)
import git_yoda as gy_mod  # noqa: E402     (aliased: tool below is named git_yoda)
import pr_desc as pr_mod  # noqa: E402      (aliased: tool below is named pr_desc)

# Optional defaults so end users can ask a question without naming a repo/namespace
# every time. Set these in the Desktop config env block.
DEFAULT_REPO = os.environ.get("LOCAL_AGENTS_DEFAULT_REPO", "")
DEFAULT_NAMESPACE = os.environ.get("LOCAL_AGENTS_DEFAULT_NAMESPACE", "")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: the MCP SDK is not installed. Run: pip install \"mcp[cli]\"\n"
    )
    raise

mcp = FastMCP("local-agents")


def _resolve_repo(repo: str | None) -> Path:
    repo = repo or DEFAULT_REPO
    if not repo:
        raise ValueError(
            "no repo given and LOCAL_AGENTS_DEFAULT_REPO is not set. "
            "Pass repo=... or set a default in the Desktop config."
        )
    p = Path(repo).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"repo path is not a directory: {p}")
    return p


def _ns(namespace: str | None, root: Path) -> str:
    return namespace or DEFAULT_NAMESPACE or root.name


@mcp.tool()
def codebase_qa(question: str, repo: str | None = None, namespace: str | None = None) -> str:
    """Ask a question about a code repository and get a cited, direct answer.

    The answer is produced by a local LLM that reads the repo (grep/read/glob)
    in its own context, so only the answer comes back. Prior Q&A for the same
    repo is recalled from shared memory and new Q&A is stored automatically.

    Args:
        question: Plain-English question about the repository.
        repo: Path to the repo root. Optional if LOCAL_AGENTS_DEFAULT_REPO is set.
        namespace: Shared-memory namespace (defaults to the configured default or
            the repo dir name).
    """
    root = _resolve_repo(repo)
    ns = _ns(namespace, root)
    result = qa_mod.answer(question, root, ns)
    if not result.startswith("ERROR"):
        try:
            memory.remember(f"Q: {question}\nA: {result}", namespace=ns,
                            kind="qa", agent="codebase-qa")
        except memory.MemoryUnavailable:
            pass
    return result


@mcp.tool()
def explore(
    task: str,
    repo: str | None = None,
    namespace: str | None = None,
    session: str | None = None,
    resume: bool = False,
) -> str:
    """Run a local-agent exploration of a repo and return one compact summary.

    Use for "how does X work", "where does Y live", "trace request Z" — work
    you'd otherwise spend the main context window on. Set resume=true to seed
    the run with the latest handover plus relevant shared memory.

    Args:
        task: What to explore or summarize.
        repo: Path to the repo root. Optional if LOCAL_AGENTS_DEFAULT_REPO is set.
        namespace: Shared-memory namespace (defaults to repo dir name).
        session: Optional session id for grouping memory/handovers.
        resume: If true, load the latest handover + relevant memory first.
    """
    root = _resolve_repo(repo)
    return local_agent.do_explore(
        task, root, _ns(namespace, root), session, resume, verbose=False
    )


@mcp.tool()
def save_handover(
    note: str,
    repo: str,
    session: str,
    namespace: str | None = None,
) -> str:
    """Generate a structured context-handover and store it in shared memory.

    Produces State / Key Files / Decisions / Next Steps / Open Questions so a
    fresh session can resume with no prior chat history.

    Args:
        note: Your one-line status of where things stand.
        repo: Path to the repo root.
        session: Session id to attach the handover to.
        namespace: Shared-memory namespace (defaults to repo dir name).
    """
    root = _resolve_repo(repo)
    return local_agent.do_handover(note, root, _ns(namespace, root), session, verbose=False)


@mcp.tool()
def latest_handover(namespace: str, session: str | None = None) -> str:
    """Return the most recent handover note for a namespace (and session).

    Args:
        namespace: Shared-memory namespace (usually the repo dir name).
        session: Optional session id to scope the lookup.
    """
    try:
        h = memory.latest_handover(namespace, session)
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"
    if not h:
        return "(no handover found)"
    return f"[{h.get('ts','?')}] session={h.get('session','?')}\n\n{h.get('text','')}"


@mcp.tool()
def memory_remember(
    text: str,
    namespace: str,
    kind: str = "note",
    session: str | None = None,
) -> str:
    """Store a durable note or decision in shared memory for later recall.

    Args:
        text: The content to remember.
        namespace: Shared-memory namespace (usually the repo dir name).
        kind: "note" or "decision".
        session: Optional session id.
    """
    try:
        _id = memory.remember(text, namespace=namespace, kind=kind,
                              agent="desktop", session=session)
        return f"stored {_id}"
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


@mcp.tool()
def memory_recall(query: str, namespace: str, k: int = 5) -> str:
    """Semantic search over shared memory; returns the most relevant entries.

    Args:
        query: What to look for.
        namespace: Shared-memory namespace (usually the repo dir name).
        k: How many results to return.
    """
    try:
        return memory.format_recall(memory.recall(query, namespace=namespace, k=k))
    except memory.MemoryUnavailable as e:
        return f"MEMORY UNAVAILABLE: {e}"


@mcp.tool()
def git_yoda(task: str, repo: str | None = None, allow_writes: bool = False) -> str:
    """Translate a natural-language git/GitHub request into git/gh commands and
    run them via the local model. Read-only commands run freely.

    SAFETY: defaults to DRY-RUN — write commands (commit/push/PR create/branch
    delete/...) are previewed, not executed. Pass allow_writes=true to actually
    execute writes. The returned text includes the model's summary plus the log
    of commands that were run or would have been run.

    Args:
        task: Plain-English git/GitHub request.
        repo: Path to the repo root.
        allow_writes: If true, execute write commands; otherwise dry-run them.
    """
    root = _resolve_repo(repo)
    mode = "yes" if allow_writes else "dry-run"
    buf = io.StringIO()
    with redirect_stderr(buf):
        summary = gy_mod.run_agent(task, root, mode, verbose=True)
    log = buf.getvalue().strip()
    parts = [summary]
    if log:
        header = "Executed commands:" if allow_writes else "Planned commands (DRY-RUN — not executed):"
        parts.append(f"\n---\n{header}\n{log}")
    return "\n".join(parts)


@mcp.tool()
def explore_lite(task: str, repo: str | None = None) -> str:
    """Lightweight file exploration of a repo — no memory required.

    Faster and simpler than `explore`: runs a local LLM agent over the repo
    using only file tools (list_dir, read_file, grep, glob) and returns one
    compact summary. Use this for quick "how does X work" or "where is Y"
    questions that don't need shared memory or session continuity.

    Args:
        task: What to explore or answer about the repo.
        repo: Path to the repo root. Optional if LOCAL_AGENTS_DEFAULT_REPO is set.
    """
    root = _resolve_repo(repo)
    return le_mod.run_agent(task, root, verbose=False)


@mcp.tool()
def pr_desc(
    repo: str | None = None,
    base: str | None = None,
    context: str = "",
) -> str:
    """Generate a structured PR description from the current branch's diff.

    Produces four sections — What / Why / How to Test / Risks — by feeding the
    diff, diffstat, and commit log to a local LLM. Also writes the body to
    .git/PR_BODY.md so you can run:
        gh pr create --title "..." --body-file .git/PR_BODY.md

    Args:
        repo: Path to the repo root. Optional if LOCAL_AGENTS_DEFAULT_REPO is set.
        base: Base ref to diff against (e.g. "origin/main"). Auto-detected if omitted.
        context: Extra author context for the Why section (e.g. a ticket summary).
    """
    import os
    root = _resolve_repo(repo)
    orig_dir = os.getcwd()
    try:
        os.chdir(str(root))
        detected_base = base or pr_mod.detect_base()
        info = pr_mod.gather(detected_base)
        if info["diff"] == "(empty)":
            return f"ERROR: no diff between HEAD and {detected_base}. Commit your changes first."
        user_msg = pr_mod.build_user_message(info, detected_base, context)
        resp = pr_mod.call_ollama([
            {"role": "system", "content": pr_mod.SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        content = resp["choices"][0]["message"].get("content", "").strip()
        if not content:
            return "ERROR: model returned empty response"
        pr_mod.write_pr_body_file(content)
        return content
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"
    finally:
        os.chdir(orig_dir)


if __name__ == "__main__":
    # stdio transport: how Claude Desktop launches and talks to this server.
    mcp.run(transport="stdio")
