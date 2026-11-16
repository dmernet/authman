import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import CHECK_INTERVAL_MINUTES, REFRESH_AHEAD_HOURS
from app.database import utcnow
from app.platforms import PLATFORM_REGISTRY
from app.services.tokens import list_tokens, refresh_token_row

log = logging.getLogger("authman.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")


async def scheduled_check():
    """每 CHECK_INTERVAL_MINUTES 分钟：
       ① accessToken 将在 REFRESH_AHEAD_HOURS 内到期 → 提前刷新
       ② 否则调用平台账户接口校验 → 失效则刷新
    """
    log.info("========== 开始巡检 token ==========")
    rows = await list_tokens()
    now = utcnow()
    ahead = timedelta(hours=REFRESH_AHEAD_HOURS)
    refreshed = 0

    for row in rows:
        try:
            expire = row.accessTokenExpireTime
            
            if expire and (expire - now) <= ahead:
                log.info("id=%s 将于 %s 到期，提前刷新", row.id, expire.isoformat())
                if await refresh_token_row(row):
                    refreshed += 1
                continue

            platform = PLATFORM_REGISTRY.get(row.platform)
            
            if not platform or not row.accessToken:
                continue

            ok = await platform.check_token(access_token=row.accessToken, user_id=row.userId, user_name=row.userName, app_id=row.appId)
            
            if not ok:
                log.warning("id=%s accessToken 失效，尝试刷新", row.id)
                if await refresh_token_row(row):
                    refreshed += 1
        except Exception as e:
            log.exception("巡检 id=%s 出错: %s", row.id, e)

    log.info("========== 巡检完成：%d 条，刷新 %d 条 ==========", len(rows), refreshed)


def start_scheduler():
    scheduler.add_job(
        scheduled_check,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="token_check",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info("调度器已启动，每 %d 分钟巡检一次", CHECK_INTERVAL_MINUTES)


def stop_scheduler():
    scheduler.shutdown(wait=False)