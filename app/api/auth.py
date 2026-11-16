import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.database import SessionLocal, utcnow
from app.models import Token, token_to_dict
from app.platforms import PLATFORM_REGISTRY
from app.services.tokens import extract_token_fields, parse_cn_time



log = logging.getLogger("authman.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

def _get_user_id(platform_key: str, app_id: str) -> Optional[str]:
    if not app_id:
        return None
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(
                Token.platform == platform_key,
                Token.appId == app_id,
            )
        )
        return row.userId if row else None 

def _get_user_name(platform_key: str, app_id: str) -> Optional[str]:
    if not app_id:
        return None
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(
                Token.platform == platform_key,
                Token.appId == app_id,
            )
        )
        return row.userName if row else None         

def _get_password(platform_key: str, app_id: str) -> Optional[str]:
    if not app_id:
        return None
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(
                Token.platform == platform_key,
                Token.appId == app_id,
            )
        )
        return row.password if row else None   

def _get_secret_key(platform_key: str, app_id: str) -> Optional[str]:
    """从 Tokens 表里按 platform + appId 取已存的 secretKey。"""
    if not app_id:
        return None
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(
                Token.platform == platform_key,
                Token.appId == app_id,
            )
        )
        return row.secretKey if row else None   

@router.get("/{platform_key}")
async def auth_entry(
    platform_key: str,
    code: Optional[str] = None,            # 通用 OAuth 回调参数名
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    authCode: Optional[str] = None,        # 百度用 authCode，不是 code
    userId: Optional[str] = None,          # 百度回调必带
    timestamp: Optional[str] = None,       # 百度签名相关
    signature: Optional[str] = None,       # 百度签名（暂未校验）
    appId: Optional[str] = None,           # 百度回调会带
    auth_code: Optional[str] = None,       # 小红书
    app_id: Optional[str] = None,          # 巨量
):
    
    userName = ""; #360需要
    password = ""; #360需要
    
    platform = PLATFORM_REGISTRY.get(platform_key)
    
    
    if not platform:
        raise HTTPException(404, f"未知平台: {platform_key}")

    if platform_key == "xiaohongshu":
        appId = state
        userId = _get_user_id(platform_key, state)

    if platform_key == "juliang":
        appId = app_id
        userId = _get_user_id(platform_key, appId)

    if platform_key == "qihoo":
        appId = state
        userId = _get_user_id(platform_key, appId)
        userName = _get_user_name(platform_key, appId)
        password = _get_password(platform_key, appId)
    
    secret_key = _get_secret_key(platform_key, appId)

    # 1) 平台回调带 error
    if error:
        return JSONResponse(
            {"ok": False, "platform": platform_key, "error": error, "desc": error_description},
            status_code=400,
        )

    # 2) 兼容百度把 code 叫 authCode
    real_code = code or authCode or auth_code

    # 3) 没带 code → 跳转到平台授权页
    if not real_code:
        url = await platform.get_auth_url(state or "authman")
        return RedirectResponse(url)

    # 4) 带 code → 换 token 并入库
    try:
        data = await platform.exchange_code(code=real_code, 
                                            user_id=userId, 
                                            user_name=userName, 
                                            password=password, 
                                            app_id=appId, 
                                            secret_key=secret_key)
    except Exception as e:
        log.exception("exchange_code 失败")
        raise HTTPException(500, f"换取 token 失败: {e}")

    fields = extract_token_fields(platform_key, data)

    with SessionLocal() as s:
        # 5) 判重用 platform + userId，优先用平台返回的 userId，
        #    百度回调有时不返回 userId，就用回调里的 userId 兜底
        final_user_id = userId

        existing = None

        if final_user_id:
            existing = s.scalar(
                select(Token).where(
                    Token.platform == platform_key,
                    Token.userId == str(final_user_id),
                )
            )

        obj = existing or Token(platform=platform_key)
        if not existing:
            s.add(obj)

        obj.accessToken = fields["accessToken"] or obj.accessToken
        obj.refreshToken = fields["refreshToken"] or obj.refreshToken

        if fields.get("expiresTime"):
            obj.accessTokenExpireTime = parse_cn_time(fields["expiresTime"])
        if fields.get("refreshExpiresTime"):
            obj.refreshTokenExpireTime = parse_cn_time(fields["refreshExpiresTime"])
        if fields["expires_in"]:
            obj.accessTokenExpireTime = utcnow() + timedelta(seconds=fields["expires_in"])
        if fields["refresh_expires_in"]:
            obj.refreshTokenExpireTime = utcnow() + timedelta(seconds=fields["refresh_expires_in"])
        obj.updateAt = utcnow()

        s.commit()
        s.refresh(obj)
        saved = token_to_dict(obj)

    return {"ok": True, "platform": platform_key, "saved": saved}