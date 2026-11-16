from urllib.parse import urlencode

import httpx
import logging
from app.platforms.base import BasePlatform


import hashlib
from Crypto.Cipher import AES
import base64
from binascii import b2a_hex



log = logging.getLogger("authman.platform.qihoo")

def create_md5_pwd(password):
    m = hashlib.md5()
    b = password.encode(encoding='utf-8')
    m.update(b)
    md5_pwd = m.hexdigest()
    return md5_pwd

class PrpCrypt(object):

    def __init__(self, API_SECRET):
        self.key = API_SECRET[:16].encode('gbk')
        self.iv = API_SECRET[16:].encode('gbk')

    def encrypt(self,text):
        # 加密
        mycipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        # 加密的明文长度必须为16的倍数，如果长度不为16的倍数，则需要补足为16的倍数
        # 将iv（密钥向量）加到加密的密文开头，一起传输
        ciphertext = self.iv + mycipher.encrypt(text.encode())
        return ciphertext  # 加密


    def decrypt(self,text):
        # 解密
        mydecrypt = AES.new(self.key, AES.MODE_CBC, text[:16])
        decrypttext = mydecrypt.decrypt(text[16:])
        decrypt_pwd = decrypttext.decode()  # 解密后数据
        return decrypt_pwd

        
class QihooPlatform(BasePlatform):
    key = "qihoo"
    display = "qihoo"
    client_id = "REPLACE_WITH_360_CLIENT_ID"
    client_secret = "REPLACE_WITH_360_CLIENT_SECRET"
    redirect_uri = "http://localhost:8000/auth/qihoo"

    AUTH_URL = "https://openapi.360.cn/oauth2/authorize"
    TOKEN_URL = "https://api.e.360.cn/account/clientLogin"
    
    ACCOUNT_URL = "https://api.e.360.cn/uc/account/getInfo"

    async def get_auth_url(self, state: str) -> str:
        return f"{self.AUTH_URL}?" + urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "basic",
            "state": state,
        })

    # ---------------- 换取授权令牌 ----------------
    async def exchange_code(self, code: str, 
                              user_id: str | int | None = None,
                              user_name: str | int | None = None,
                              password: str | int | None = None,
                              app_id: str | int | None = None,
                              secret_key: str | int | None = None) -> dict:

        text = create_md5_pwd(password)
        pc = PrpCrypt(secret_key)
        ciphertext = pc.encrypt(text)
        e = b2a_hex(ciphertext)[32:].decode()
        d = pc.decrypt(ciphertext)
        
        # print('加密后:' + e)
        # print('解密后:' + d)

        payload = {
            "username": user_name,
            "passwd": e,
        }
        
        http_headers = {
            "apiKey": app_id,
        }

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.TOKEN_URL, data=payload, headers=http_headers)

        r.raise_for_status()
        
        log.info(r.text)

        data = r.json()

        # ---- 业务失败：存在且非空的 failures ----
        failures = data.get("failures") or []
        if failures:
            first = failures[0] if isinstance(failures[0], dict) else {}
            code = first.get("code")
            msg = first.get("message") or first.get("description") or ""
            log.warning("qihoo refresh 失败: code=%s msg=%s raw=%s", code, msg, data)
            raise RuntimeError(f"360刷新令牌失败: code={code}, message={msg}")

        # ---- 业务成功：必须拿到 accessToken ----
        access_token = data.get("accessToken")
        if not access_token:
            log.warning("qihoo refresh 返回异常，缺少 accessToken: %s", data)
            raise RuntimeError(f"360刷新令牌失败: 响应中缺少 accessToken, raw={data}")

        log.info("qihoo refresh 成功: uid=%s", data.get("uid"))

        return {
            "message": "OK",
            "code": 0,
            "data": {
                "access_token": access_token,
                "expires_in": 10 * 3600,  # 360 接口不返回有效期，按约定的 10 小时
            },
        }

    # ---------------- 刷新授权令牌 ----------------
    async def refresh(self, refresh_token: str, 
                      user_id: str | int | None = None,
                      user_name: str | int | None = None,
                      password: str | int | None = None,
                      app_id: str | int | None = None,
                      secret_key: str | int | None = None) -> dict:

        text = create_md5_pwd(password)
        pc = PrpCrypt(secret_key)
        ciphertext = pc.encrypt(text)
        e = b2a_hex(ciphertext)[32:].decode()
        d = pc.decrypt(ciphertext)
        
        # print('加密后:' + e)
        # print('解密后:' + d)

        payload = {
            "username": user_name,
            "passwd": e,
        }
        
        http_headers = {
            "apiKey": app_id,
        }

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.TOKEN_URL, data=payload, headers=http_headers)

        r.raise_for_status()
        
        log.info(r.text)

        data = r.json()

        # ---- 业务失败：存在且非空的 failures ----
        failures = data.get("failures") or []
        if failures:
            first = failures[0] if isinstance(failures[0], dict) else {}
            code = first.get("code")
            msg = first.get("message") or first.get("description") or ""
            log.warning("qihoo refresh 失败: code=%s msg=%s raw=%s", code, msg, data)
            raise RuntimeError(f"360刷新令牌失败: code={code}, message={msg}")

        # ---- 业务成功：必须拿到 accessToken ----
        access_token = data.get("accessToken")
        if not access_token:
            log.warning("qihoo refresh 返回异常，缺少 accessToken: %s", data)
            raise RuntimeError(f"360刷新令牌失败: 响应中缺少 accessToken, raw={data}")

        log.info("qihoo refresh 成功: uid=%s", data.get("uid"))

        return {
            "message": "OK",
            "code": 0,
            "data": {
                "access_token": access_token,
                "expires_in": 10 * 3600,  # 360 接口不返回有效期，按约定的 10 小时
            },
        }

    # ---------------- 校验令牌 ----------------
    async def check_token(self, access_token: str, user_id: str, user_name: str, app_id: str) -> bool:

        http_headers = {
            "apiKey": app_id,
            "accessToken": access_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        log.info("accessToken: %s", access_token)
        
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(self.ACCOUNT_URL, headers=http_headers)

            if r.status_code != 200:
                log.warning("qihoo check_token HTTP %s", r.status_code)
                return False

            #log.info(r.text)

            hdr = r.json()

            uid = hdr.get("uid") or []
           
            if not uid:
                log.warning(
                    "qihoo check_token 失败"
                )
                return False
            
            log.info("uid: %s", uid)

            return True
        except Exception as e:
            log.debug("qihoo check_token 异常: %s", e)
            return False