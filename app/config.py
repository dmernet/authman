from pathlib import Path
import os

# 基础路径
# BASE_DIR = Path(__file__).resolve().parent.parent
# DB_PATH = BASE_DIR / "tokens.db"
DB_PATH = os.getenv("DB_PATH", "/data/tokens.db")

# 巡检参数
CHECK_INTERVAL_MINUTES = 10
REFRESH_AHEAD_HOURS = 2

# 后台
ADMIN_TITLE = "AuthMan"
ADMIN_BASE_URL = "/admin"
ADMIN_SECRET = "please-change-me"