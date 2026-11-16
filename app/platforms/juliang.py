from urllib.parse import urlencode
import logging
import httpx

from app.platforms.base import BasePlatform

log = logging.getLogger("authman.platform.juliang")

class JuliangPlatform(BasePlatform):
    key = "juliang"
    display = "巨量引擎"
    client_id = "REPLACE_WITH_OCEANENGINE_APP_ID"
    client_secret = "REPLACE_WITH_OCEANENGINE_SECRET"
    redirect_uri = "http://localhost:8000/auth/juliang"

    AUTH_URL = "https://open.oceanengine.com/audit/oauth.html"
    TOKEN_URL = "https://api.oceanengine.com/open_api/oauth2/access_token/"
    REFRESH_URL = "https://api.oceanengine.com/open_api/oauth2/refresh_token/"
    ACCOUNT_URL = "https://api.oceanengine.com/open_api/2/user/info/"

    async def get_auth_url(self, state: str) -> str:
        return f"{self.AUTH_URL}?" + urlencode({
            "app_id": self.client_id,
            "state": state,
            "scope": "advertiser",
            "redirect_uri": self.redirect_uri,
        })

    # ---------------- 换取授权令牌 ----------------
    async def exchange_code(self, code: str, 
                        user_id: str | int | None = None,
                        user_name: str | int | None = None,
                        password: str | int | None = None,
                        app_id: str | int | None = None,
                        secret_key: str | int | None = None,) -> dict:

        payload = {
            "app_id": app_id,         # 应用 appId
            "auth_code": code,                # 临时授权码
            "secret": secret_key, # 应用 secretKey
        }

        http_headers = {
            "Content-Type": "application/json",
        }        

        log.info(payload)
        
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.TOKEN_URL, json=payload, headers=http_headers)

        r.raise_for_status()

        log.info(r.text)

        data = r.json()

        if data.get("code") != 0:
            log.warning("juliang exchange_code 失败: %s", data)
            raise RuntimeError(f"巨量换取令牌失败: {data.get('message')}")

        # 直接把文档返回原样吐出，由 extract_token_fields 统一解析
        return data

    # ---------------- 刷新授权令牌 ----------------
    async def refresh(self, refresh_token: str, 
                      user_id: str | int | None = None,
                      user_name: str | int | None = None,
                      password: str | int | None = None,
                      app_id: str | int | None = None,
                      secret_key: str | int | None = None,) -> dict:

        payload = {
            "app_id": app_id,
            "secret": secret_key,
            "refresh_token": refresh_token,
        }
        http_headers = {
            "Content-Type": "application/json",
        } 
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.REFRESH_URL, json=payload, headers=http_headers)

        r.raise_for_status()

        log.info(r.text)

        data = r.json()

        if data.get("code") != 0:
            log.warning("juliang refresh 失败: %s", data)
            raise RuntimeError(f"巨量刷新令牌失败: {data.get('message')}")

        return data

    # ---------------- 校验令牌 ----------------
    async def check_token(self, access_token: str, user_id: str, user_name: str, app_id: str) -> bool:

        http_headers = {
            "Access-Token": access_token
        }

        try:
            async with httpx.AsyncClient() as client:
                    r = await client.get(self.ACCOUNT_URL, headers=http_headers)

            if r.status_code != 200:
                log.warning("juliang check_token HTTP %s", r.status_code)
                return False

            # log.info(r.text)

            hdr = r.json()

            if hdr.get("code") != 0 or hdr.get("message") != "OK":
                log.warning(
                    "juliang check_token 失败 status=%s succ=%s desc=%s",
                    hdr.get("message"), hdr.get("code"),
                )
                return False

            log.info("message: %s", hdr.get("message"))

            return True
        except Exception as e:
            log.debug("juliang check_token 异常: %s", e)
            return False