from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import PromptVersion
from app.prompts.repository import get_active, list_recent, save_new, restore

router = APIRouter(prefix="/prompt", tags=["prompt"])


class PromptUpdateRequest(BaseModel):
    content: str
    note: str | None = None


@router.get("")
async def get_prompt(session: AsyncSession = Depends(get_session)):
    prompt = await get_active(session)
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
async def get_prompt_history(session: AsyncSession = Depends(get_session)):
    prompts = await list_recent(session, limit=10)
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
async def get_prompt_history_item(version_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(PromptVersion).where(PromptVersion.id == version_id))
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
async def update_prompt(body: PromptUpdateRequest, session: AsyncSession = Depends(get_session)):
    prompt = await save_new(session, body.content, body.note)
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
async def restore_prompt(version_id: int, session: AsyncSession = Depends(get_session)):
    prompt = await restore(session, version_id)
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
