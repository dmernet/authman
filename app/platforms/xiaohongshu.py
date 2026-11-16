from urllib.parse import urlencode

import httpx
import logging
from datetime import date

from app.platforms.base import BasePlatform

log = logging.getLogger("authman.platform.xhs")

class XiaohongshuPlatform(BasePlatform):
    key = "xiaohongshu"
    display = "小红书"
    client_id = "REPLACE_WITH_XHS_CLIENT_ID"
    client_secret = "REPLACE_WITH_XHS_CLIENT_SECRET"
    redirect_uri = "http://localhost:8000/auth/xiaohongshu"

    AUTH_URL = "https://ad.xiaohongshu.com/aurora/oauth2/authorize"

    TOKEN_URL = "https://adapi.xiaohongshu.com/api/open/oauth2/access_token"
    REFRESH_URL = "https://adapi.xiaohongshu.com/api/open/oauth2/refresh_token"

    ACCOUNT_URL = "https://adapi.xiaohongshu.com/api/open/jg/data/report/realtime/account"

    JSON_HEADERS = {
        "Accept-Encoding": "",
        "Content-Type": "application/json;charset:utf-8",
        "Accept": "application/json",
    }

    async def get_auth_url(self, state: str) -> str:
        return f"{self.AUTH_URL}?" + urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        })

    # ---------------- 换取授权令牌 ----------------
    async def exchange_code(self, code: str, 
                            user_id: str | int | None = None,
                            user_name: str | int | None = None,
                            password: str | int | None = None,
                            app_id: str | int | None = None,
                            secret_key: str | int | None = None) -> dict:

        payload = {
            "app_id": app_id,         # 应用 appId
            "auth_code": code,                # 临时授权码
            "secret": secret_key, # 应用 secretKey
        }

        log.info(payload)
        
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.TOKEN_URL, json=payload, headers=self.JSON_HEADERS)

        r.raise_for_status()

        log.info(r.text)

        data = r.json()

        if data.get("code") != 0:
            log.warning("xhs exchange_code 失败: %s", data)
            raise RuntimeError(f"小红书换取令牌失败: {data.get('message')}")

        # 直接把文档返回原样吐出，由 extract_token_fields 统一解析
        return data

    # ---------------- 刷新授权令牌 ----------------
    async def refresh(self, refresh_token: str, 
                        user_id: str | int | None = None,
                        user_name: str | int | None = None,
                        password: str | int | None = None,
                        app_id: str | int | None = None,
                        secret_key: str | int | None = None) -> dict:

        payload = {
            "app_id": app_id,
            "secret": secret_key,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.REFRESH_URL, json=payload, headers=self.JSON_HEADERS)

        r.raise_for_status()

        log.info(r.text)

        data = r.json()

        if data.get("code") != 0:
            log.warning("xhs refresh 失败: %s", data)
            raise RuntimeError(f"小红书刷新令牌失败: {data.get('message')}")

        return data

    # ---------------- 校验令牌 ----------------
    async def check_token(self, access_token: str, user_id: str, user_name: str, app_id: str) -> bool:

        today = date.today().strftime("%Y-%m-%d")

        payload = {
            "advertiser_id": user_id,
            "start_date": today,
            "end_date": today,
            "need_hourly_data": "false"
        }

        http_headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json;charset:utf-8",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(self.ACCOUNT_URL, json=payload, headers=http_headers)

            if r.status_code != 200:
                log.warning("xhs check_token HTTP %s", r.status_code)
                return False

            log.info(r.text)

            hdr = r.json()

            if hdr.get("code") != 0 or hdr.get("success") != True:
                log.warning(
                    "xhs check_token 失败 status=%s succ=%s desc=%s",
                    hdr.get("msg"), hdr.get("success"), hdr.get("code"),
                )
                return False

            return True
        except Exception as e:
            log.debug("xhs check_token 异常: %s", e)
            return False