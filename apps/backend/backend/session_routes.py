"""Session management API endpoints.

Routes are ordered with fixed paths before parameterized paths to avoid FastAPI
treating literal segments like "archive" and "index" as session IDs.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.session_store import (
    _live_dir,
    append_activity_entries,
    delete_iteration,
    delete_session,
    derive_session_tabs,
    import_archive,
    import_session,
    list_archive_metas,
    list_iteration_dirs,
    move_live_to_archive,
    read_activity_log,
    read_iteration_full,
    read_iteration_meta,
    read_session_meta,
    restore_archive_to_live,
    rewrite_activity_log,
    trash_session,
    write_iteration,
    write_session_meta,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


# =============================================================================
# Request / Response Models
# =============================================================================

class SessionTabsBody(BaseModel):
    tabs: list[dict]


class SessionMetaBody(BaseModel):
    backtestParams: dict
    selectedIterationId: Optional[str] = None


class ActivityAppendBody(BaseModel):
    entries: list[dict]


class ActivityRewriteBody(BaseModel):
    entries: list[dict]


class IterationUpsertBody(BaseModel):
    index: int
    node: dict


class ArchiveBody(BaseModel):
    archiveMeta: dict


class ImportArchiveBody(BaseModel):
    archiveMeta: dict
    sessionData: dict


class RestoreBody(BaseModel):
    newSessionId: str


class ImportBody(BaseModel):
    sessionData: dict


# =============================================================================
# Fixed-path routes (MUST come before /{session_id})
# =============================================================================

@router.get("")
async def list_session_tabs():
    """List live session tabs derived from the live/ directory."""
    tabs = await asyncio.to_thread(derive_session_tabs)
    return {"tabs": tabs}


@router.put("/index")
async def save_session_tabs(body: SessionTabsBody):
    """Distribute name+lastAccessedAt from each tab into its session.json."""
    def _run():
        for tab in body.tabs:
            tab_id = tab.get("id")
            if tab_id and _live_dir(tab_id).exists():
                write_session_meta(tab_id, {
                    "name": tab.get("name"),
                    "lastAccessedAt": tab.get("lastAccessedAt"),
                })
    await asyncio.to_thread(_run)
    return {"ok": True}


@router.get("/archive")
async def list_archive():
    """List all archive session headers."""
    archive = await asyncio.to_thread(list_archive_metas)
    return {"archive": archive}


@router.post("/archive")
async def import_archive_endpoint(body: ImportArchiveBody):
    """Import a full session directly into the archive (for migration)."""
    archive_id = await asyncio.to_thread(import_archive, body.archiveMeta, body.sessionData)
    return {"ok": True, "archiveId": archive_id}


@router.post("/archive/{archive_id}/restore")
async def restore_archive(archive_id: str, body: RestoreBody):
    """Restore an archived session to a new live session."""
    await asyncio.to_thread(restore_archive_to_live, archive_id, body.newSessionId)
    return {"ok": True, "newSessionId": body.newSessionId}


@router.delete("/archive/{archive_id}")
async def delete_archive_entry(archive_id: str):
    """Delete an archived session."""
    await asyncio.to_thread(delete_session, archive_id, True)
    return {"ok": True}


# =============================================================================
# Session CRUD (parameterized routes)
# =============================================================================

@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get full session: meta + activity log + all iterations."""
    def _load():
        meta = read_session_meta(session_id) or {}
        activity = read_activity_log(session_id)

        iterations = []
        for d in list_iteration_dirs(session_id):
            parts = d.name.split("_", 1)
            if len(parts) < 2:
                continue
            node = read_iteration_full(session_id, parts[1])
            if node:
                iterations.append(node)
        return meta, activity, iterations

    meta, activity, iterations = await asyncio.to_thread(_load)

    # Only 404 if nothing exists for this session
    if not meta and not activity and not iterations:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "sessionId": session_id,
        "backtestParams": meta.get("backtestParams", {}),
        "selectedIterationId": meta.get("selectedIterationId"),
        "activityLog": activity,
        "iterationHistory": iterations,
    }


@router.post("/{session_id}")
async def import_session_endpoint(session_id: str, body: ImportBody):
    """Bulk import a full session (for migration from localStorage)."""
    await asyncio.to_thread(import_session, session_id, body.sessionData)
    return {"ok": True}


@router.api_route("/{session_id}/meta", methods=["PUT", "POST"])
async def save_session_meta_endpoint(session_id: str, body: SessionMetaBody):
    """Save backtestParams + selectedIterationId."""
    await asyncio.to_thread(write_session_meta, session_id, {
        "backtestParams": body.backtestParams,
        "selectedIterationId": body.selectedIterationId,
    })
    return {"ok": True}


@router.post("/{session_id}/activity")
async def append_activity(session_id: str, body: ActivityAppendBody):
    """Append new activity entries (O(1) append to activity.jsonl)."""
    await asyncio.to_thread(append_activity_entries, session_id, body.entries)
    return {"ok": True}


@router.put("/{session_id}/activity")
async def rewrite_activity(session_id: str, body: ActivityRewriteBody):
    """Full rewrite of the activity log."""
    await asyncio.to_thread(rewrite_activity_log, session_id, body.entries)
    return {"ok": True}


@router.get("/{session_id}/iterations")
async def list_iterations(session_id: str):
    """List iteration metas (lightweight — no result/rating data)."""
    def _list():
        metas = []
        for d in list_iteration_dirs(session_id):
            parts = d.name.split("_", 1)
            if len(parts) < 2:
                continue
            meta = read_iteration_meta(session_id, parts[1])
            if meta:
                metas.append(meta)
        return metas
    metas = await asyncio.to_thread(_list)
    return {"iterations": metas}


@router.post("/{session_id}/iterations")
async def upsert_iteration(session_id: str, body: IterationUpsertBody):
    """Create or overwrite one iteration (upsert)."""
    await asyncio.to_thread(write_iteration, session_id, body.index, body.node)
    return {"ok": True}


@router.get("/{session_id}/iterations/{iteration_id}")
async def get_iteration(session_id: str, iteration_id: str):
    """Get full IterationNode including result and rating data."""
    node = await asyncio.to_thread(read_iteration_full, session_id, iteration_id)
    if node is None:
        raise HTTPException(
            status_code=404, detail=f"Iteration {iteration_id} not found"
        )
    return node


@router.delete("/{session_id}/iterations/{iteration_id}")
async def delete_iteration_endpoint(session_id: str, iteration_id: str):
    """Delete one iteration."""
    await asyncio.to_thread(delete_iteration, session_id, iteration_id)
    return {"ok": True}


@router.delete("/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Move session to archive/ as recycle bin (invisible in UI, recoverable on disk)."""
    await asyncio.to_thread(trash_session, session_id)
    return {"ok": True}


@router.post("/{session_id}/archive")
async def archive_session_endpoint(session_id: str, body: ArchiveBody):
    """Archive a live session (copy to archive directory)."""
    archive_id = await asyncio.to_thread(move_live_to_archive, session_id, body.archiveMeta)
    return {"ok": True, "archiveId": archive_id}
