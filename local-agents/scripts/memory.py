#!/usr/bin/env python3
"""
memory
======
Shared, semantic memory for the local-agents kit. Every agent
(local-agent, codebase-qa, git-yoda) reads and writes the SAME store, so a
note one agent records is recallable by another — this is the "multi-agent
shared memory" layer.

Backend:
  - Embeddings : Ollama (local), default model `nomic-embed-text` (768 dims).
  - Storage    : MongoDB Atlas with a Vector Search index ($vectorSearch).

Each memory is one document:
  {
    "_id": ObjectId,
    "namespace": "growth",        # usually the repo name; isolates projects
    "kind": "note" | "handover" | "qa" | "decision",
    "session": "2026-06-08-oauth",   # optional, groups a working session
    "agent": "local-agent",          # who wrote it
    "text": "...",                   # the human-readable content
    "meta": {...},                   # arbitrary structured extras
    "embedding": [float, ...],       # 768-d vector of `text`
    "ts": "2026-06-08T10:30:00Z"
  }

Design notes:
  - No hard dependency at import time. `pymongo` is only imported when a
    memory operation actually runs, so the other agents work even if memory
    isn't configured. If MONGODB_URI is unset, memory ops raise
    MemoryUnavailable with a clear message; callers treat memory as optional.
  - Pure stdlib for embeddings (urllib), pymongo for storage.

Environment:
  MONGODB_URI            MongoDB Atlas connection string (required for memory).
  MEMORY_DB              Default: agent_memory
  MEMORY_COLLECTION      Default: memories
  MEMORY_VECTOR_INDEX    Default: agent_memory_vec
  MEMORY_VECTOR_MODE     auto (default) | atlas | bruteforce
                         - atlas      : use $vectorSearch (Atlas / Atlas-Local only)
                         - bruteforce : load candidates and rank by cosine in
                                        Python — works on ANY MongoDB (incl. a
                                        plain self-hosted mongod on localhost)
                         - auto       : try atlas, fall back to bruteforce if the
                                        server lacks $vectorSearch
  MEMORY_BRUTEFORCE_SCAN Default: 5000 (max docs scanned in bruteforce mode)
  OLLAMA_EMBED_URL       Default: http://localhost:11434/api/embeddings
  MEMORY_EMBED_MODEL     Default: nomic-embed-text
  MEMORY_EMBED_DIMS      Default: 768   (must match your Atlas index, if using atlas)
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

MONGODB_URI = os.environ.get("MONGODB_URI", "")
DB_NAME = os.environ.get("MEMORY_DB", "agent_memory")
COLL_NAME = os.environ.get("MEMORY_COLLECTION", "memories")
VECTOR_INDEX = os.environ.get("MEMORY_VECTOR_INDEX", "agent_memory_vec")
VECTOR_MODE = os.environ.get("MEMORY_VECTOR_MODE", "auto").lower()
BRUTEFORCE_SCAN = int(os.environ.get("MEMORY_BRUTEFORCE_SCAN", "5000"))

OLLAMA_EMBED_URL = os.environ.get(
    "OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings"
)
EMBED_MODEL = os.environ.get("MEMORY_EMBED_MODEL", "nomic-embed-text")
EMBED_DIMS = int(os.environ.get("MEMORY_EMBED_DIMS", "768"))


class MemoryUnavailable(RuntimeError):
    """Raised when memory is requested but not configured/reachable."""


# ---------- embeddings (Ollama, local) ----------

def embed(text: str) -> list[float]:
    """Return an embedding vector for `text` via the local Ollama server."""
    text = (text or "").strip()
    if not text:
        raise MemoryUnavailable("cannot embed empty text")
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_EMBED_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise MemoryUnavailable(
            f"cannot reach Ollama embeddings at {OLLAMA_EMBED_URL}: {e}. "
            f"Is `ollama serve` running and have you run "
            f"`ollama pull {EMBED_MODEL}`?"
        ) from e
    vec = data.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise MemoryUnavailable(f"unexpected embeddings response: {data}")
    if len(vec) != EMBED_DIMS:
        # Not fatal, but the Atlas index will reject a dimension mismatch.
        raise MemoryUnavailable(
            f"embedding has {len(vec)} dims but MEMORY_EMBED_DIMS={EMBED_DIMS}. "
            f"Set MEMORY_EMBED_DIMS to match `{EMBED_MODEL}` and rebuild the "
            f"Atlas vector index with numDimensions={len(vec)}."
        )
    return vec


# ---------- storage (MongoDB Atlas) ----------

_collection = None  # lazily-initialised pymongo Collection


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    if not MONGODB_URI:
        raise MemoryUnavailable(
            "MONGODB_URI is not set. Shared memory is disabled. Set MONGODB_URI "
            "to your Atlas connection string to enable remember/recall/handover."
        )
    try:
        from pymongo import MongoClient
    except ImportError as e:
        raise MemoryUnavailable(
            "pymongo is not installed. Run: pip install pymongo"
        ) from e
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
    except Exception as e:  # noqa: BLE001 - surface any connection failure
        raise MemoryUnavailable(f"cannot connect to MongoDB Atlas: {e}") from e
    _collection = client[DB_NAME][COLL_NAME]
    return _collection


def is_available() -> bool:
    """True if memory can be used right now (URI set + reachable)."""
    try:
        _get_collection()
        return True
    except MemoryUnavailable:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def remember(
    text: str,
    namespace: str,
    kind: str = "note",
    agent: str = "unknown",
    session: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Embed `text` and store it. Returns the new document id as a string."""
    coll = _get_collection()
    doc = {
        "namespace": namespace,
        "kind": kind,
        "agent": agent,
        "session": session,
        "text": text,
        "meta": meta or {},
        "embedding": embed(text),
        "ts": _now(),
    }
    res = coll.insert_one(doc)
    return str(res.inserted_id)


# cached after the first successful detection so we don't re-probe every call
_atlas_supported: bool | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _atlas_recall(coll, qvec, namespace, k, kinds):
    vfilter: dict[str, Any] = {"namespace": {"$eq": namespace}}
    if kinds:
        vfilter = {"$and": [vfilter, {"kind": {"$in": kinds}}]}
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX,
                "path": "embedding",
                "queryVector": qvec,
                "numCandidates": max(50, k * 15),
                "limit": k,
                "filter": vfilter,
            }
        },
        {
            "$project": {
                "_id": 0, "text": 1, "kind": 1, "agent": 1, "session": 1,
                "ts": 1, "meta": 1, "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(coll.aggregate(pipeline))


def _bruteforce_recall(coll, qvec, namespace, k, kinds):
    """Rank by cosine in Python. Works on any MongoDB (no search engine needed)."""
    q: dict[str, Any] = {"namespace": namespace}
    if kinds:
        q["kind"] = {"$in": kinds}
    proj = {"text": 1, "kind": 1, "agent": 1, "session": 1, "ts": 1,
            "meta": 1, "embedding": 1, "_id": 0}
    scored = []
    for doc in coll.find(q, proj).limit(BRUTEFORCE_SCAN):
        emb = doc.pop("embedding", None)
        if not emb:
            continue
        doc["score"] = _cosine(qvec, emb)
        scored.append(doc)
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:k]


def recall(
    query: str,
    namespace: str,
    k: int = 5,
    kinds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Vector-search the store for memories relevant to `query`.

    Backend chosen by MEMORY_VECTOR_MODE:
      - "atlas"      : Atlas $vectorSearch only
      - "bruteforce" : Python cosine over candidates (any MongoDB)
      - "auto"       : try Atlas, fall back to bruteforce on this process

    Returns a list of {text, kind, agent, session, ts, score, meta}, best first.
    """
    global _atlas_supported
    coll = _get_collection()
    qvec = embed(query)

    if VECTOR_MODE == "bruteforce":
        return _bruteforce_recall(coll, qvec, namespace, k, kinds)
    if VECTOR_MODE == "atlas":
        return _atlas_recall(coll, qvec, namespace, k, kinds)

    # auto
    if _atlas_supported is False:
        return _bruteforce_recall(coll, qvec, namespace, k, kinds)
    try:
        from pymongo.errors import OperationFailure
    except ImportError:  # pragma: no cover
        OperationFailure = Exception  # type: ignore
    try:
        res = _atlas_recall(coll, qvec, namespace, k, kinds)
        _atlas_supported = True
        return res
    except OperationFailure:
        # Server doesn't know $vectorSearch (plain mongod) — fall back for good.
        _atlas_supported = False
        return _bruteforce_recall(coll, qvec, namespace, k, kinds)


def save_handover(
    summary: str,
    namespace: str,
    session: str,
    agent: str = "local-agent",
    meta: dict[str, Any] | None = None,
) -> str:
    """Store a structured handover summary (kind='handover')."""
    return remember(
        summary,
        namespace=namespace,
        kind="handover",
        agent=agent,
        session=session,
        meta=meta,
    )


def latest_handover(
    namespace: str, session: str | None = None
) -> dict[str, Any] | None:
    """Return the most recent handover for a namespace (optionally a session)."""
    coll = _get_collection()
    q: dict[str, Any] = {"namespace": namespace, "kind": "handover"}
    if session:
        q["session"] = session
    docs = list(
        coll.find(q, {"embedding": 0}).sort("ts", -1).limit(1)
    )
    if not docs:
        return None
    d = docs[0]
    d["_id"] = str(d.get("_id", ""))
    return d


# ---------- formatting helpers (for CLI / agent prompts) ----------

def format_recall(results: list[dict[str, Any]]) -> str:
    if not results:
        return "(no relevant memories found)"
    lines = []
    for i, r in enumerate(results, 1):
        score = r.get("score", 0.0)
        head = f"[{i}] ({r.get('kind','note')}, {r.get('agent','?')}, " \
               f"{r.get('ts','?')}, score={score:.3f})"
        lines.append(head)
        lines.append(r.get("text", "").strip())
        lines.append("")
    return "\n".join(lines).strip()


# ---------- diagnostics ----------

def _doctor() -> None:
    """Print a step-by-step health check for the whole memory path."""
    ok = "  OK  "
    bad = " FAIL "

    print("local-agents memory doctor")
    print("=" * 32)

    # 1. env
    print(f"[{ok if MONGODB_URI else bad}] MONGODB_URI set"
          + ("" if MONGODB_URI else "  -> export MONGODB_URI=..."))
    print(f"        db={DB_NAME} collection={COLL_NAME} "
          f"vector_mode={VECTOR_MODE} index={VECTOR_INDEX}")
    print(f"        embed_model={EMBED_MODEL} dims={EMBED_DIMS}")

    # 2. ollama embeddings
    try:
        v = embed("connectivity probe")
        print(f"[{ok}] Ollama embeddings reachable (got {len(v)} dims)")
    except MemoryUnavailable as e:
        print(f"[{bad}] Ollama embeddings: {e}")
        print("\nFix Ollama first, then re-run `doctor`.")
        raise SystemExit(3)

    # 3. mongo connection
    try:
        coll = _get_collection()
        print(f"[{ok}] MongoDB connection + auth")
    except MemoryUnavailable as e:
        print(f"[{bad}] MongoDB: {e}")
        raise SystemExit(3)

    # 4. round-trip remember/recall on a throwaway namespace
    ns = "__doctor__"
    try:
        _id = remember("doctor canary: the auth guard lives in jwt.guard.ts",
                       namespace=ns, kind="note", agent="doctor")
        hits = recall("where is the auth guard", namespace=ns, k=1)
        coll.delete_many({"namespace": ns})  # cleanup
        if hits:
            backend = ("atlas" if _atlas_supported else "bruteforce") \
                if VECTOR_MODE == "auto" else VECTOR_MODE
            print(f"[{ok}] remember + recall round-trip (backend={backend}, "
                  f"top score={hits[0].get('score', 0):.3f})")
        else:
            print(f"[{bad}] recall returned nothing after a write")
            raise SystemExit(3)
    except MemoryUnavailable as e:
        print(f"[{bad}] round-trip: {e}")
        raise SystemExit(3)

    print("\nAll green. The agents can share memory.")


# ---------- tiny CLI for manual inspection / scripting ----------

def _main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Shared agent memory (Atlas vector).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("remember", help="Store a memory.")
    pr.add_argument("text")
    pr.add_argument("--namespace", required=True)
    pr.add_argument("--kind", default="note")
    pr.add_argument("--agent", default="cli")
    pr.add_argument("--session", default=None)

    pc = sub.add_parser("recall", help="Vector-search memories.")
    pc.add_argument("query")
    pc.add_argument("--namespace", required=True)
    pc.add_argument("-k", type=int, default=5)
    pc.add_argument("--kinds", nargs="*", default=None)

    ph = sub.add_parser("latest-handover", help="Show latest handover.")
    ph.add_argument("--namespace", required=True)
    ph.add_argument("--session", default=None)

    sub.add_parser("status", help="Check memory availability.")
    sub.add_parser("doctor", help="Full end-to-end connectivity check.")

    args = p.parse_args()
    try:
        if args.cmd == "doctor":
            _doctor()
        elif args.cmd == "status":
            print("available" if is_available() else "unavailable")
        elif args.cmd == "remember":
            _id = remember(
                args.text, args.namespace, args.kind, args.agent, args.session
            )
            print(f"stored {_id}")
        elif args.cmd == "recall":
            print(format_recall(recall(args.query, args.namespace, args.k, args.kinds)))
        elif args.cmd == "latest-handover":
            h = latest_handover(args.namespace, args.session)
            print(json.dumps(h, indent=2) if h else "(none)")
    except MemoryUnavailable as e:
        print(f"MEMORY UNAVAILABLE: {e}")
        raise SystemExit(3)


if __name__ == "__main__":
    _main()
