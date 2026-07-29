from __future__ import annotations

import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Medical Interaction Assistant")
    environment: str = os.getenv("APP_ENV", "development")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    rxlabelguard_base_url: str = os.getenv("RXLABELGUARD_BASE_URL", "").strip()
    rxlabelguard_query_path: str = os.getenv("RXLABELGUARD_QUERY_PATH", "/labels/search").strip()
    rxlabelguard_api_key: str = os.getenv("RXLABELGUARD_API_KEY", "").strip()
    rxlabelguard_api_key_header: str = os.getenv("RXLABELGUARD_API_KEY_HEADER", "Authorization").strip()
    rxlabelguard_api_key_prefix: str = os.getenv("RXLABELGUARD_API_KEY_PREFIX", "Bearer").strip()


settings = Settings()
