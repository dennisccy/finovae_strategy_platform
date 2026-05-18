"""File-based session persistence for backtest sessions.

Stores all data under BASE_DIR (default: a durable in-repo <repo>/.data/backtests
resolved from this file's location, NOT volatile /tmp; override with
BACKTEST_STORE_DIR):
  live/{sessionId}/session.json  — name, lastAccessedAt, backtestParams, selectedIterationId
  live/{sessionId}/activity.jsonl          — one ActivityEntry per line (append-friendly)
  live/{sessionId}/iterations/{NNN}_{id}/  — one dir per iteration
      prompt.txt, strategy.py, meta.json, insights.json
      timeframes/{tf}/result.json, rating.json
  archive/{archiveId}/meta.json            — ArchivedSession header
  archive/{archiveId}/...                  — same structure as live/{sessionId}/

Session tabs are derived directly from the live/ directory (no _index.json).
Deleted sessions are moved to archive/ without a meta.json (invisible in UI but recoverable).
"""

import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Durable, CWD-independent default resolved from this file's location
# (apps/backend/backend/session_store.py -> parents[3] == repo root). This is
# the SAME path the runtime .env advertises (<repo>/.data/backtests), so the
# default and an explicit BACKTEST_STORE_DIR point at the same on-disk store
# and session/run history survives a process restart with no .env present.
_DEFAULT_STORE_DIR = Path(__file__).resolve().parents[3] / ".data" / "backtests"
BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR") or _DEFAULT_STORE_DIR)


# =============================================================================
# Helpers
# =============================================================================

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _live_dir(session_id: str) -> Path:
    return BASE_DIR / "live" / session_id


def _archive_dir(archive_id: str) -> Path:
    return BASE_DIR / "archive" / archive_id


def _session_dir(session_id: str, archived: bool = False) -> Path:
    return _archive_dir(session_id) if archived else _live_dir(session_id)


def _iters_dir(session_id: str, archived: bool = False) -> Path:
    return _session_dir(session_id, archived) / "iterations"


# =============================================================================
# Session tabs (derived from live/ directory)
# =============================================================================

def derive_session_tabs() -> list[dict]:
    """Derive session tab list from live/ directory.

    One-time migrates _index.json (if present) by merging names/timestamps
    into each session's session.json, then deletes _index.json.
    """
    live = BASE_DIR / "live"
    index_path = BASE_DIR / "_index.json"

    # One-time migration: apply names/timestamps from _index.json into session.json files
    if index_path.exists():
        try:
            old_tabs = json.loads(index_path.read_text(encoding="utf-8"))
            for tab in old_tabs:
                tab_id = tab.get("id")
                if tab_id and _live_dir(tab_id).exists():
                    write_session_meta(tab_id, {
                        "name": tab.get("name"),
                        "lastAccessedAt": tab.get("lastAccessedAt"),
                    })
        except Exception:
            pass
        index_path.unlink(missing_ok=True)

    if not live.exists():
        return []

    tabs = []
    for d in live.iterdir():
        if not d.is_dir():
            continue
        session_id = d.name
        meta = read_session_meta(session_id) or {}

        name = meta.get("name")
        last_accessed = meta.get("lastAccessedAt")

        # Fallback: derive name from first complete iteration's strategyName
        if not name:
            iters_base = _iters_dir(session_id)
            if iters_base.exists():
                for iter_dir in sorted(iters_base.iterdir()):
                    if not iter_dir.is_dir():
                        continue
                    meta_file = iter_dir / "meta.json"
                    if meta_file.exists():
                        try:
                            iter_meta = json.loads(meta_file.read_text(encoding="utf-8"))
                            name = iter_meta.get("strategyName")
                            if name:
                                break
                        except Exception:
                            pass

        # Fallback: use directory mtime
        if not last_accessed:
            last_accessed = int(d.stat().st_mtime * 1000)

        tabs.append({
            "id": session_id,
            "name": name or "Session",
            "lastAccessedAt": last_accessed,
        })

    return sorted(tabs, key=lambda t: t["lastAccessedAt"], reverse=True)


# =============================================================================
# Session metadata (session.json)
# =============================================================================

def read_session_meta(session_id: str, archived: bool = False) -> Optional[dict]:
    path = _session_dir(session_id, archived) / "session.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_session_meta(session_id: str, data: dict, archived: bool = False) -> None:
    """Merge data into session.json (read-update-write, not full overwrite)."""
    d = _ensure_dir(_session_dir(session_id, archived))
    path = d / "session.json"
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.update(data)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


# =============================================================================
# Activity log (activity.jsonl)
# =============================================================================

def read_activity_log(session_id: str, archived: bool = False) -> list[dict]:
    path = _session_dir(session_id, archived) / "activity.jsonl"
    if not path.exists():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def append_activity_entries(
    session_id: str, entries: list[dict], archived: bool = False
) -> None:
    if not entries:
        return
    _ensure_dir(_session_dir(session_id, archived))
    path = _session_dir(session_id, archived) / "activity.jsonl"
    lines = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(lines)


def rewrite_activity_log(
    session_id: str, entries: list[dict], archived: bool = False
) -> None:
    _ensure_dir(_session_dir(session_id, archived))
    path = _session_dir(session_id, archived) / "activity.jsonl"
    text = (
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
        if entries
        else ""
    )
    path.write_text(text, encoding="utf-8")


# =============================================================================
# Iterations
# =============================================================================

def list_iteration_dirs(session_id: str, archived: bool = False) -> list[Path]:
    base = _iters_dir(session_id, archived)
    if not base.exists():
        return []
    return sorted(
        [d for d in base.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )


def find_iter_dir(
    session_id: str, iteration_id: str, archived: bool = False
) -> Optional[Path]:
    base = _iters_dir(session_id, archived)
    if not base.exists():
        return None
    for d in base.iterdir():
        if d.is_dir() and d.name.endswith(f"_{iteration_id}"):
            return d
    return None


def write_iteration(
    session_id: str, index: int, node_dict: dict, archived: bool = False
) -> None:
    """Write (or overwrite) a single iteration to disk, splitting into files."""
    iteration_id = node_dict.get("id", "")
    existing = find_iter_dir(session_id, iteration_id, archived)
    if existing:
        iter_dir = existing
    else:
        _ensure_dir(_iters_dir(session_id, archived))
        iter_dir = _iters_dir(session_id, archived) / f"{index:03d}_{iteration_id}"
        iter_dir.mkdir(parents=True, exist_ok=True)

    # prompt.txt
    (iter_dir / "prompt.txt").write_text(
        node_dict.get("prompt", ""), encoding="utf-8"
    )

    # strategy.py
    (iter_dir / "strategy.py").write_text(
        node_dict.get("scriptCode", ""), encoding="utf-8"
    )

    # insights.json
    (iter_dir / "insights.json").write_text(
        json.dumps(node_dict.get("insights"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # meta.json — all fields except the bulk ones
    _BULK_KEYS = {"prompt", "scriptCode", "insights", "result", "rating", "timeframeResults"}
    meta = {k: v for k, v in node_dict.items() if k not in _BULK_KEYS}
    (iter_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # timeframes/{tf}/result.json + rating.json
    params = node_dict.get("params") or {}
    timeframe = params.get("timeframe") or (params.get("timeframes") or ["4h"])[0]
    primary_result = node_dict.get("result")
    primary_rating = node_dict.get("rating")
    if primary_result is not None or primary_rating is not None:
        tf_dir = iter_dir / "timeframes" / timeframe
        tf_dir.mkdir(parents=True, exist_ok=True)
        (tf_dir / "result.json").write_text(
            json.dumps(primary_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (tf_dir / "rating.json").write_text(
            json.dumps(primary_rating, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _read_json_safe(path: Path) -> Optional[object]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_iteration_meta(
    session_id: str, iteration_id: str, archived: bool = False
) -> Optional[dict]:
    d = find_iter_dir(session_id, iteration_id, archived)
    if not d:
        return None
    result = _read_json_safe(d / "meta.json")
    return result if isinstance(result, dict) else None


def read_iteration_full(
    session_id: str, iteration_id: str, archived: bool = False
) -> Optional[dict]:
    """Reassemble all iteration files back into a complete node dict."""
    d = find_iter_dir(session_id, iteration_id, archived)
    if not d:
        return None

    meta_raw = _read_json_safe(d / "meta.json")
    if not isinstance(meta_raw, dict):
        return None
    node: dict = dict(meta_raw)

    prompt_path = d / "prompt.txt"
    node["prompt"] = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    script_path = d / "strategy.py"
    node["scriptCode"] = script_path.read_text(encoding="utf-8") if script_path.exists() else ""

    node["insights"] = _read_json_safe(d / "insights.json")

    # result / rating — read from actual timeframe dir, fallback to _primary (old data)
    tf_base = d / "timeframes"
    node["result"] = None
    node["rating"] = None
    if tf_base.exists():
        for tf_dir in sorted(tf_base.iterdir()):
            if not tf_dir.is_dir() or tf_dir.name == "_primary":
                continue
            result_data = _read_json_safe(tf_dir / "result.json")
            if result_data is not None:
                node["result"] = result_data
                node["rating"] = _read_json_safe(tf_dir / "rating.json")
                break
        if node["result"] is None:
            pdir = tf_base / "_primary"
            node["result"] = _read_json_safe(pdir / "result.json")
            node["rating"] = _read_json_safe(pdir / "rating.json")
    node["timeframeResults"] = []

    return node


def delete_iteration(session_id: str, iteration_id: str) -> None:
    d = find_iter_dir(session_id, iteration_id, archived=False)
    if d and d.exists():
        shutil.rmtree(d)


def delete_session(session_id: str, archived: bool = False) -> None:
    d = _session_dir(session_id, archived)
    if d.exists():
        shutil.rmtree(d)


def trash_session(session_id: str) -> None:
    """Move live session to archive/ as a recycle bin.

    No meta.json is written, so the session remains invisible in the UI archive
    list (list_archive_metas only returns entries with meta.json) but the folder
    stays on disk for manual recovery.
    """
    src = _live_dir(session_id)
    dst = _archive_dir(session_id)
    if src.exists():
        _ensure_dir(dst.parent)
        if dst.exists():
            shutil.rmtree(dst)  # overwrite any prior trash with same ID
        shutil.move(str(src), str(dst))


# =============================================================================
# Archive
# =============================================================================

def list_archive_metas() -> list[dict]:
    base = BASE_DIR / "archive"
    if not base.exists():
        return []
    metas = []
    for d in base.iterdir():
        if not d.is_dir():
            continue
        raw = _read_json_safe(d / "meta.json")
        if isinstance(raw, dict):
            metas.append(raw)
    return sorted(metas, key=lambda m: m.get("createdAt", ""), reverse=True)


def write_archive_meta(archive_meta: dict) -> None:
    archive_id = archive_meta["id"]
    d = _ensure_dir(_archive_dir(archive_id))
    (d / "meta.json").write_text(
        json.dumps(archive_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def move_live_to_archive(session_id: str, archive_meta: dict) -> str:
    """Copy live session to archive directory and write archive meta header."""
    archive_id = archive_meta.get("id") or str(uuid.uuid4())
    archive_meta = {**archive_meta, "id": archive_id}

    src = _live_dir(session_id)
    dst = _archive_dir(archive_id)
    _ensure_dir(dst.parent)
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    write_archive_meta(archive_meta)
    return archive_id


def restore_archive_to_live(archive_id: str, new_session_id: str) -> None:
    """Copy archive to a new live session directory."""
    src = _archive_dir(archive_id)
    dst = _live_dir(new_session_id)
    _ensure_dir(dst.parent)
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    # Remove archive-specific meta from the live copy
    live_meta = dst / "meta.json"
    if live_meta.exists():
        live_meta.unlink()


def import_archive(archive_meta: dict, session_data: dict) -> str:
    """Import a full SessionData dict directly into an archive directory."""
    archive_id = archive_meta.get("id") or str(uuid.uuid4())
    archive_meta = {**archive_meta, "id": archive_id}

    write_session_meta(archive_id, {
        "backtestParams": session_data.get("backtestParams", {}),
        "selectedIterationId": session_data.get("selectedIterationId"),
    }, archived=True)
    rewrite_activity_log(archive_id, session_data.get("activityLog", []), archived=True)
    for idx, node in enumerate(session_data.get("iterationHistory", []), start=1):
        write_iteration(archive_id, idx, node, archived=True)
    write_archive_meta(archive_meta)
    return archive_id


# =============================================================================
# Bulk import (migration from localStorage)
# =============================================================================

def import_session(session_id: str, session_data: dict) -> None:
    """Import a full SessionData dict (from old localStorage format) into file storage."""
    write_session_meta(session_id, {
        "backtestParams": session_data.get("backtestParams", {}),
        "selectedIterationId": session_data.get("selectedIterationId"),
    })
    rewrite_activity_log(session_id, session_data.get("activityLog", []))
    for idx, node in enumerate(session_data.get("iterationHistory", []), start=1):
        write_iteration(session_id, idx, node)


# =============================================================================
# Startup
# =============================================================================

def initialize() -> None:
    """Create base directory structure on startup."""
    _ensure_dir(BASE_DIR)
    _ensure_dir(BASE_DIR / "live")
    _ensure_dir(BASE_DIR / "archive")
    logger.info("Session store initialized at %s", BASE_DIR)
