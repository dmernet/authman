import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin import setup_admin
from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.config import ADMIN_TITLE
from app.database import Base, engine
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


# 建表
from app import models  # noqa: F401  确保模型注册
Base.metadata.create_all(engine)

app = FastAPI(title=ADMIN_TITLE, lifespan=lifespan)

# 业务路由
app.include_router(public_router)
app.include_router(auth_router)

# 后台
setup_admin(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)