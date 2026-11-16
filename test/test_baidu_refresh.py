import asyncio
import logging
import json
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Token
from app.platforms.baidu import BaiduPlatform

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    # 1) 从库里取一条百度记录
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(Token.platform == "baidu").order_by(Token.id.desc()).limit(1)
        )

    if not row:
        print("❌ 库里没有 baidu 记录，先去 /auth/baidu 授权一次")
        return

    print("=" * 60)
    print(f"id          = {row.id}")
    print(f"userId      = {row.userId}")
    print(f"appId       = {row.appId}")
    print(f"secretKey   = {(row.secretKey or '')[:10]}…")
    print(f"refreshToken= {(row.refreshToken or '')[:30]}…")
    print(f"过期时间     = {row.refreshTokenExpireTime}")
    print("=" * 60)

    # 2) 直接调 refresh
    p = BaiduPlatform()
    try:
        data = await p.refresh(
            row.refreshToken,
            user_id=row.userId,
            app_id=row.appId,
            secret_key=row.secretKey,
        )
        print("\n✅ 刷新返回：")
        
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 3) 顺手打印关键字段
        d = data.get("data") or {}
        print("\n--- 关键字段 ---")
        print("new accessToken  =", (d.get("accessToken") or "")[:40], "…")
        print("new refreshToken =", (d.get("refreshToken") or "")[:40], "…")
        print("expiresIn        =", d.get("expiresIn"))
        print("expiresTime      =", d.get("expiresTime"))
        print("refreshExpiresIn =", d.get("refreshExpiresIn"))
        print("refreshExpiresTime =", d.get("refreshExpiresTime"))

    except Exception as e:
        print(f"\n❌ 刷新失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())