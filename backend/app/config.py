from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str

    # New Supabase backend key style
    supabase_secret_key: str | None = None

    # Legacy fallback, only if needed
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "shop-images"

    railbound_guild_id: int = 1462489358908129354
    staff_discord_ids: str = ""
    cors_origins: str = "http://localhost:5173"
    discord_staff_webhook_url: str = ""
    discord_bot_token: str = ""

    discord_oauth_client_id: str = ""
    discord_oauth_client_secret: str = ""
    discord_oauth_redirect_uri: str = "http://localhost:8000/api/auth/discord/callback"
    frontend_url: str = "http://localhost:5173"
    auth_session_secret: str = "dev-change-me"
    allow_dev_login: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def supabase_admin_key(self) -> str:
        key = self.supabase_secret_key or self.supabase_service_role_key

        if not key:
            raise ValueError(
                "Missing Supabase backend key. Set SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY in backend/.env."
            )

        return key

    @property
    def staff_ids(self) -> set[int]:
        out: set[int] = set()

        for part in self.staff_discord_ids.split(","):
            part = part.strip()
            if part.isdigit():
                out.add(int(part))

        return out

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()