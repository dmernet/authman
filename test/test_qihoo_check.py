import asyncio
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
    print(f"id          = {row.id}")
    print(f"userId      = {row.userId}")
    print(f"userName    = {row.userName}")
    print(f"accessToken = {(row.accessToken or '')[:40]}…")
    print(f"过期时间     = {row.accessTokenExpireTime}")
    print("=" * 60)

    p = QihooPlatform()
    try:
        ok = await p.check_token(access_token=row.accessToken, user_id=row.userId, app_id=row.appId)
        print(f"\ncheck_token -> {ok}")
    except Exception as e:
        print(f"\n❌ check_token 异常: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())