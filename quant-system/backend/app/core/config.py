"""应用配置模块.

通过 pydantic-settings 从环境变量 / .env 文件加载配置，
并提供量化系统默认参数（回测、因子、ML 等），与项目根目录的
``config/settings.yaml`` 保持语义一致。
"""

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录：quant-system/ (backend/ 的父目录)
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """全局配置.

    所有字段均可通过环境变量（大小写不敏感）或 ``.env`` 文件覆盖。
    """

    # ---------- FastAPI ----------
    APP_NAME: str = "Quant Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ---------- 认证 & 安全 ----------
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 默认 24 小时

    # ---------- 数据库 ----------
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'db' / 'quant.sqlite.db'}"

    # ---------- Redis ----------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---------- Celery ----------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ---------- 数据路径 ----------
    DATA_DIR: str = str(BASE_DIR / "data")
    CACHE_DIR: str = str(BASE_DIR / "data" / "cache")

    # ---------- 日志 ----------
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(BASE_DIR / "logs")

    # ---------- CORS ----------
    # 允许的前端来源，逗号分隔
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # ---------- 回测默认参数（对应 config/settings.yaml::backtest） ----------
    BACKTEST_INITIAL_CAPITAL: float = 1_000_000.0
    BACKTEST_COMMISSION: float = 0.001
    BACKTEST_SLIPPAGE: float = 0.0005

    # ---------- 因子默认参数（对应 config/settings.yaml::factor） ----------
    FACTOR_FORWARD_PERIOD: int = 20
    FACTOR_N_LAYERS: int = 5
    FACTOR_ICIR_THRESHOLD: float = 0.5
    FACTOR_MAX_DECAY_PERIOD: int = 120

    # ---------- ML 默认参数（对应 config/settings.yaml::ml） ----------
    ML_TRAIN_MONTHS: int = 24
    ML_VAL_MONTHS: int = 6
    ML_FORWARD_PERIOD: int = 20
    ML_N_MAD: float = 3.0
    ML_NUM_BOOST_ROUND: int = 500
    ML_EARLY_STOPPING: int = 50
    ML_OPTUNA_TRIALS: int = 50
    ML_MODEL_DIR: str = str(BASE_DIR / "data" / "models")

    # ---------- Pydantic v2 配置 ----------
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        """支持以逗号分隔的字符串形式配置 CORS 来源."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()


def get_settings() -> Settings:
    """返回配置单例（便于在依赖注入中使用，也方便测试覆盖）."""
    return settings
