from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.main import _app_state
from app.db.models import PromptVersion
from app.prompts.repository import get_active, list_recent, save_new, restore

router = APIRouter(prefix="/prompt", tags=["prompt"])


class PromptUpdateRequest(BaseModel):
    content: str
    note: str | None = None


@router.get("")
async def get_prompt():
    """Get the currently active prompt version."""
    prompt = await get_active(_app_state.db_session)
    if not prompt:
        return {"data": None, "error": "No active prompt found"}

    return {
        "data": {
            "id": prompt.id,
            "content": prompt.content,
            "note": prompt.note,
            "created_at": prompt.created_at.isoformat(),
        },
        "error": None,
    }


@router.get("/history")
async def get_prompt_history():
    """Get the 10 most recent prompt versions (without content)."""
    prompts = await list_recent(_app_state.db_session, limit=10)
    return {
        "data": [
            {
                "id": p.id,
                "note": p.note,
                "created_at": p.created_at.isoformat(),
                "is_active": p.is_active,
            }
            for p in prompts
        ],
        "error": None,
    }


@router.get("/history/{version_id}")
async def get_prompt_history_item(version_id: int):
    """Get a specific prompt version with full content."""
    stmt = select(PromptVersion).where(PromptVersion.id == version_id)
    result = await _app_state.db_session.execute(stmt)
    prompt = result.scalar_one_or_none()

    if not prompt:
        return {"data": None, "error": "Prompt version not found"}

    return {
        "data": {
            "id": prompt.id,
            "content": prompt.content,
            "note": prompt.note,
            "created_at": prompt.created_at.isoformat(),
            "is_active": prompt.is_active,
        },
        "error": None,
    }


@router.put("")
async def update_prompt(body: PromptUpdateRequest):
    """Save a new prompt version and set it as active."""
    prompt = await save_new(_app_state.db_session, body.content, body.note)
    return {
        "data": {
            "id": prompt.id,
            "content": prompt.content,
            "note": prompt.note,
            "created_at": prompt.created_at.isoformat(),
            "is_active": prompt.is_active,
        },
        "error": None,
    }


@router.post("/restore/{version_id}")
async def restore_prompt(version_id: int):
    """Restore an older prompt version (creates new active version from it)."""
    prompt = await restore(_app_state.db_session, version_id)

    if not prompt:
        return {"data": None, "error": "Prompt version not found"}

    return {
        "data": {
            "id": prompt.id,
            "content": prompt.content,
            "note": prompt.note,
            "created_at": prompt.created_at.isoformat(),
            "is_active": prompt.is_active,
        },
        "error": None,
    }
