import asyncio
import logging

from app.database import SessionLocal
from app.models import Token
from app.platforms.baidu import BaiduPlatform
from sqlalchemy import select

logging.basicConfig(level=logging.DEBUG)


async def main():
    with SessionLocal() as s:
        row = s.scalar(
            select(Token).where(Token.platform == "baidu").limit(1)
        )

    if not row:
        print("数据库里没有 baidu 平台的记录")
        return

    print(f"id={row.id} userId={row.userId} userName={row.userName}")
    print(f"accessToken={row.accessToken[:20]}...")

    p = BaiduPlatform()
    ok = await p.check_token(row.accessToken, row.userName or "")
    print("check_token ->", ok)


if __name__ == "__main__":
    asyncio.run(main())