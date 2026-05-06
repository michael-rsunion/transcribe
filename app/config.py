"""Single source of truth para configuracion. NUNCA acceder a os.environ fuera de aqui."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    GEMINI_API_KEY: str = Field(min_length=10)
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_INLINE_AUDIO_BYTES: int = 20_000_000

    # Auth
    BASIC_AUTH_USER: str = Field(min_length=1)
    BASIC_AUTH_PASS: str = Field(min_length=24)
    HMAC_LOG_SECRET: str = Field(min_length=32)

    # Limits
    MAX_VIDEO_DURATION_SEC: int = 600
    MAX_DOWNLOAD_SIZE_MB: int = 100
    YT_DLP_SOCKET_TIMEOUT_SEC: int = 30
    FFMPEG_TIMEOUT_SEC: int = 30
    GEMINI_TIMEOUT_SEC: int = 45
    TOTAL_REQUEST_TIMEOUT_SEC: int = 90
    MAX_BODY_BYTES: int = 4096

    # Rate limits
    RATE_LIMIT_PER_MIN: int = 10
    RATE_LIMIT_PER_DAY: int = 100
    RATE_LIMIT_FAILED_AUTH_PER_HOUR: int = 5

    # Filesystem
    TMPFS_BASE_DIR: str = "/tmp/transcribe"  # noqa: S108

    # Concurrency
    MAX_CONCURRENT_REQUESTS: int = 2


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
