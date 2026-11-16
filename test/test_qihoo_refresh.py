import asyncio
import json
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Token
from app.platforms.qihoo import QihooPlatform

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    with SessionLocal() as s:
        row = s.scalar(
            select(Token)
            .where(Token.platform == "qihoo")
            .order_by(Token.id.desc())
            .limit(1)
        )

    if not row:
        print("❌ 库里没有 qihoo 记录，先去 /auth/qihoo 授权一次")
        return

    print("=" * 60)
    print(f"id           = {row.id}")
    print(f"userId       = {row.userId}")
    print(f"userName     = {row.userName}")
    print(f"refreshToken = {(row.refreshToken or '')[:40]}…")
    print(f"过期时间      = {row.refreshTokenExpireTime}")
    print("=" * 60)

    p = QihooPlatform()
    try:
        data = await p.refresh(
            row.refreshToken,
            user_id=row.userId,
            user_name=row.userName,
            password=row.password,
            app_id=row.appId,
            secret_key=row.secretKey,
        )
        print("\n✅ 刷新返回：")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        


        # 常见字段
        d = data.get("data") if isinstance(data.get("data"), dict) else data
        print("\n--- 关键字段 ---")
        print("accessToken  =", (d.get("access_token") or d.get("accessToken") or "")[:40], "…")
        print("refreshToken =", (d.get("refresh_token") or d.get("refreshToken") or "")[:40], "…")
        print("expires_in   =", d.get("expires_in") or d.get("expiresIn"))

    except Exception as e:
        print(f"\n❌ 刷新失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())