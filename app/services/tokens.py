import logging

from datetime import timedelta, datetime

from sqlalchemy import select

from app.database import SessionLocal, utcnow
from app.models import Token
from app.platforms import PLATFORM_REGISTRY

log = logging.getLogger("authman.tokens")


def extract_token_fields(platform_key: str, data: dict) -> dict:
    """把各平台不同的返回结构统一成标准字段。"""
    inner = data.get("data") if isinstance(data.get("data"), dict) else data

    def pick(*keys):
        for k in keys:
            if inner.get(k) not in (None, ""):
                return inner[k]
        return None

    expires = pick("expires_in", "expiresIn", "expires_in_seconds")
    refresh_expires = pick("refresh_token_expires_in", "refreshTokenExpiresIn", "refresh_expires_in")

    return {
        "accessToken": pick("access_token", "accessToken", "accessTokenVal", "access_token"),
        "refreshToken": pick("refresh_token", "refreshToken", "refresh_token"),
        "expires_in": pick("access_token_expires_in","expires_in"),
        "refresh_expires_in": pick("refresh_token_expires_in"),
        "userId": str(pick("user_id", "userId", "advertiser_id", "advertiserId", "uid") or "") or None,
        "userName": pick("user_name", "userName", "name", "nickname", "username"),
        "expiresTime": pick("expiresTime"),
        "refreshExpiresTime": pick("refreshExpiresTime"),
    }


async def refresh_token_row(row: Token) -> bool:
    """刷新单条记录，成功返回 True。"""
    platform = PLATFORM_REGISTRY.get(row.platform)
    if not platform:
        log.warning("未知平台: %s", row.platform)
        return False

    refreshToken = row.refreshToken or "none";

    if not refreshToken:
        log.warning("id=%s 无 refreshToken", row.id)
        return False

    try:
        data = await platform.refresh(row.refreshToken,
                                      user_id=row.userId,
                                      user_name=row.userName,
                                      password=row.password,
                                      app_id=row.appId,
                                      secret_key=row.secretKey)
        
        fields = extract_token_fields(row.platform, data)

        with SessionLocal() as s:
            obj = s.get(Token, row.id)
            if not obj:
                return False

            if fields["accessToken"]:
                obj.accessToken = fields["accessToken"]
            if fields["refreshToken"]:
                obj.refreshToken = fields["refreshToken"]
            if fields.get("expiresTime"):
                obj.accessTokenExpireTime = parse_cn_time(fields["expiresTime"])
            if fields.get("refreshExpiresTime"):
                obj.refreshTokenExpireTime = parse_cn_time(fields["refreshExpiresTime"])
            
            if fields["expires_in"]:
                obj.accessTokenExpireTime = utcnow() + timedelta(seconds=fields["expires_in"])
            if fields["refresh_expires_in"]:
                obj.refreshTokenExpireTime = utcnow() + timedelta(seconds=fields["refresh_expires_in"])
            
            s.commit()

        log.info("✅ 刷新成功 id=%s platform=%s", row.id, row.platform)
        return True
    except Exception as e:
        log.exception("❌ 刷新失败 id=%s platform=%s: %s", row.id, row.platform, e)
        return False


async def list_tokens() -> list[Token]:
    with SessionLocal() as s:
        return list(s.scalars(select(Token)))

def parse_cn_time(s: str | None) -> datetime | None:
    """
    把百度返回的北京时间字符串解析成朴素 datetime（不做时区换算，原样入库）。
    兼容多种格式：
        2026-11-13 15:49:19
        2026-11-13 15:49
        2026-11-13
        202611131549
        20261113
    """
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    log.warning("无法解析时间字符串: %s", s)
    return None    