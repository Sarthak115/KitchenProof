"""Runtime configuration, read once from environment variables."""

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Gemini
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    gemini_fallback_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
    )
    use_vertex: bool = field(default_factory=lambda: _bool("GOOGLE_GENAI_USE_VERTEXAI", False))
    gcp_project: str | None = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT"))
    gcp_location: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
    gemini_api_key: str | None = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
    # Set to false to never call Gemini (offline dev / tests): demo samples use cached results.
    gemini_enabled: bool = field(default_factory=lambda: _bool("GEMINI_ENABLED", True))

    # Storage + data
    storage_bucket: str | None = field(default_factory=lambda: os.getenv("STORAGE_BUCKET"))
    # "firestore" on Cloud Run; "memory" for local dev and tests.
    datastore: str = field(default_factory=lambda: os.getenv("DATASTORE", "firestore"))
    local_media_dir: str = field(default_factory=lambda: os.getenv("LOCAL_MEDIA_DIR", "local_media"))

    # Demo + secrets
    demo_mode: bool = field(default_factory=lambda: _bool("DEMO_MODE", True))
    scheduler_secret: str | None = field(default_factory=lambda: os.getenv("SCHEDULER_SECRET"))
    admin_secret: str | None = field(default_factory=lambda: os.getenv("ADMIN_SECRET"))

    # Business rules (§5)
    start_window_min: int = field(default_factory=lambda: int(os.getenv("START_WINDOW_MIN", "10")))
    finish_window_min: int = field(default_factory=lambda: int(os.getenv("FINISH_WINDOW_MIN", "4")))
    customer_checks_per_day: int = field(
        default_factory=lambda: int(os.getenv("CUSTOMER_CHECKS_PER_DAY", "3"))
    )
    customer_cooldown_days: int = field(
        default_factory=lambda: int(os.getenv("CUSTOMER_COOLDOWN_DAYS", "7"))
    )


settings = Settings()
