from fastapi import APIRouter, HTTPException

from app.models import token_to_dict
from app.services.scheduler import scheduled_check
from app.services.tokens import list_tokens, refresh_token_row

router = APIRouter(tags=["public"])


@router.get("/get")
async def get_all():
    """返回 SQLite 中 Tokens 表全部数据。"""
    rows = await list_tokens()
    return {"count": len(rows), "data": [token_to_dict(r) for r in rows]}


@router.post("/refresh/{token_id}")
async def manual_refresh(token_id: int):
    rows = await list_tokens()
    row = next((r for r in rows if r.id == token_id), None)
    if not row:
        raise HTTPException(404, "token not found")
    ok = await refresh_token_row(row)
    return {"ok": ok, "id": token_id}


@router.get("/check/now")
async def check_now():
    await scheduled_check()
    return {"ok": True}