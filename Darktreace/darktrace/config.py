import os
import re
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _int_env(name, default, minimum=1, maximum=100000):
    try:
        return max(minimum, min(maximum, int(os.getenv(name, default))))
    except (TypeError, ValueError):
        return default


def build_config(test_config=None):
    database_name = os.getenv("MYSQL_DATABASE", "darktrace")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise ValueError("MYSQL_DATABASE must contain only letters, numbers, or underscores.")
    database_url = URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "root"),
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=_int_env("MYSQL_PORT", 3306, 1, 65535),
        database=database_name,
        query={"charset": "utf8mb4"},
    )
    config = {
        "SECRET_KEY": os.getenv("APP_SECRET_KEY") or secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=8),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"},
        "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", "root").strip().lower(),
        "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", "root"),
        "RISK_THRESHOLD": _int_env("RISK_THRESHOLD", 60, 1, 100),
        "TEMP_BLOCK_MINUTES": _int_env("TEMP_BLOCK_MINUTES", 15, 1, 1440),
        "FAILED_LOGIN_LIMIT": _int_env("FAILED_LOGIN_LIMIT", 5, 2, 100),
        "FAILED_LOGIN_WINDOW_MINUTES": _int_env("FAILED_LOGIN_WINDOW_MINUTES", 15, 1, 1440),
        "DEBUG": os.getenv("DEBUG", "0").lower() in {"1", "true", "yes"},
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "localhost"),
        "MYSQL_PORT": _int_env("MYSQL_PORT", 3306, 1, 65535),
        "MYSQL_USER": os.getenv("MYSQL_USER", "root"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", "root"),
        "MYSQL_DATABASE": database_name,
    }
    if test_config:
        config.update(test_config)
    return config