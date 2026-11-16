import logging
from urllib.parse import urlencode

import httpx

from app.platforms.base import BasePlatform

log = logging.getLogger("authman.platform.baidu")


class BaiduPlatform(BasePlatform):
    key = "baidu"
    display = "百度营销"
    client_id = "REPLACE_WITH_BAIDU_APP_ID"
    client_secret = "REPLACE_WITH_BAIDU_SECRET_KEY"
    redirect_uri = "http://localhost:19000/auth/baidu"

    # OAuth 授权中心（统一域名 u.baidu.com）
    AUTH_URL = "https://u.baidu.com/oauth/page/index"
    PLATFORM_ID = "4960345965958561794"          # 文档固定值

    # 换取 / 更新令牌
    TOKEN_URL = "https://u.baidu.com/oauth/accessToken"
    REFRESH_URL = "https://u.baidu.com/oauth/refreshToken"

    # 业务 API（校验 token 用）
    ACCOUNT_URL = "https://api.baidu.com/json/sms/service/AccountService/getAccountInfo"

    JSON_HEADERS = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json;charset:utf-8",
        "Accept": "application/json",
    }

    # ---------------- 授权链接 ----------------
    async def get_auth_url(self, state: str) -> str:
        params = {
            "platformId": self.PLATFORM_ID,
            "appId": self.client_id,
            "scope": "1007690",          # 建议从应用管理界面生成的授权链接里拷
            "state": state,
            "callback": self.redirect_uri,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    # ---------------- 换取授权令牌 ----------------
    async def exchange_code(self, code: str, 
                            user_id: str | int | None = None,
                            user_name: str | int | None = None,
                            password: str | int | None = None,
                            app_id: str | int | None = None,
                            secret_key: str | int | None = None) -> dict:

        if not user_id:
            raise ValueError("baidu exchange_code 需要 userId（回调时会带回）")

        payload = {
            "appId": app_id,         # 应用 appId
            "authCode": code,                # 临时授权码
            "secretKey": secret_key, # 应用 secretKey
            "grantType": "auth_code",        # 文档固定值
            "userId": int(user_id),          # 必须是数字
        }

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.TOKEN_URL, json=payload, headers=self.JSON_HEADERS)

        r.raise_for_status()
        log.info(r.text)
        data = r.json()

        if data.get("code") != 0:
            log.warning("baidu exchange_code 失败: %s", data)
            raise RuntimeError(f"百度换取令牌失败: {data.get('message')}")

        # 直接把文档返回原样吐出，由 extract_token_fields 统一解析
        return data

    # ---------------- 刷新授权令牌 ----------------
    async def refresh(self, refresh_token: str, 
                      user_id: str | int | None = None,
                      user_name: str | int | None = None,
                      password: str | int | None = None,
                      app_id: str | int | None = None,
                      secret_key: str | int | None = None,) -> dict:

        if not user_id:
            raise ValueError("baidu refresh 需要 userId")

        payload = {
            "appId": app_id,
            "secretKey": secret_key,
            "refreshToken": refresh_token,
            "userId": int(user_id),
        }

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.REFRESH_URL, json=payload, headers=self.JSON_HEADERS)

        r.raise_for_status()

        log.info(r.text)

        data = r.json()

        if data.get("code") != 0:
            log.warning("baidu refresh 失败: %s", data)
            raise RuntimeError(f"百度刷新令牌失败: {data.get('message')}")

        return data

    # ---------------- 校验令牌 ----------------
    async def check_token(self, access_token: str, user_id: str = "", user_name: str = "", app_id: str = "") -> bool:
        payload = {
            "header": {
                "userName": user_name,
                "accessToken": access_token,
            },
            "body": {
                "accountFields": ["userId"],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(self.ACCOUNT_URL, json=payload, headers=self.JSON_HEADERS)

            if r.status_code != 200:
                log.warning("baidu check_token HTTP %s", r.status_code)
                return False

            log.info(r.text)

            hdr = r.json().get("header") or {}
            if hdr.get("status") != 0 or hdr.get("succ") != 1:
                log.warning(
                    "baidu check_token 失败 status=%s succ=%s desc=%s",
                    hdr.get("status"), hdr.get("succ"), hdr.get("desc"),
                )
                return False

            return True
        except Exception as e:
            log.debug("baidu check_token 异常: %s", e)
            return False