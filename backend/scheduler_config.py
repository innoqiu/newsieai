# scheduler_config.py
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# --- 1. 你的路径逻辑 (直接复用) ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH_ENV = os.getenv("DATABASE_PATH")
if DB_PATH_ENV:
    DB_PATH = Path(DB_PATH_ENV)
else:
    DB_PATH = BASE_DIR / "data" / "newsieai.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- 2. 转换为 SQLAlchemy URL ---
db_url = f"sqlite:///{DB_PATH}"

# --- 3. 初始化调度器 ---
jobstores = {
    'default': SQLAlchemyJobStore(url=db_url)
}
executors = {
    'default': ThreadPoolExecutor(10)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

# 实例化调度器 (注意：这里不启动 start，只做配置)
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)