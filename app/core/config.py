"""Configuración central cargada desde variables de entorno (.env).

Usa pydantic-settings para validar y tipar la configuración al arrancar.
Si falta un valor crítico, la aplicación falla rápido con un error claro.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_name: str = "Solari"
    app_env: str = "local"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Base de datos
    database_url: str = Field(
        default="postgresql+psycopg://postgres:admin@127.0.0.1:5432/voluntapp"
    )

    # JWT (compatible con Laravel jwt-auth)
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_minutes: int = 20160
    jwt_issuer: str = "http://localhost:8000/api/v1/auth/login"
    jwt_provider_model: str = "App\\Models\\Usuario"

    # CORS
    cors_origins: str = ""

    # Rate limiting
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "10/hour"
    rate_limit_forgot_password: str = "3/hour"  # noqa: S105 - no es una contraseña
    rate_limit_reset_password: str = "5/hour"  # noqa: S105 - no es una contraseña

    # Correo
    mail_backend: str = "console"
    mail_host: str = "127.0.0.1"
    mail_port: int = 2525
    mail_username: str = ""
    mail_password: str = ""
    mail_use_tls: bool = False
    mail_from_address: str = "noreply@solari.co"
    mail_from_name: str = "Solari"
    frontend_reset_url: str = "http://localhost:5173/reset-password"
    frontend_verify_url: str = "http://localhost:5173/verify-email"

    # Google OIDC
    google_client_id: str = ""
    google_allowed_audiences: str = ""

    # Contraseñas
    password_min_length: int = 8

    # Subida de archivos (fotos de perfil y documentos de verificación)
    upload_dir: str = "uploads"
    # Documentos de identidad y de verificación: NUNCA se sirven de forma pública.
    private_upload_dir: str = "private_uploads"
    upload_max_mb: int = 5
    upload_public_base: str = "http://localhost:9000/uploads"

    # Recordatorios de actividad (tarea de fondo cada hora). Se desactiva también
    # cuando APP_ENV es "testing" o "ci".
    reminders_enabled: bool = True

    @field_validator("jwt_secret")
    @classmethod
    def _non_empty_secret(cls, v: str) -> str:
        if not v or v.strip() == "" or v.startswith("cambia-esto"):
            raise ValueError(
                "JWT_SECRET no está configurado. Copia el mismo secreto del .env de Laravel."
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_audiences_list(self) -> list[str]:
        explicit = [a.strip() for a in self.google_allowed_audiences.split(",") if a.strip()]
        if explicit:
            return explicit
        return [self.google_client_id] if self.google_client_id else []

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
