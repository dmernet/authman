from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DB_PATH

CN_TZ = timezone(timedelta(hours=8))

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()

def now_cn() -> datetime:
    """返回当前北京时间（朴素，无 tzinfo），全局统一用它。"""
    return datetime.now(CN_TZ).replace(tzinfo=None)

utcnow = now_cn