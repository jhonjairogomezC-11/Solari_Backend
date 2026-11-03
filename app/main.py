"""Punto de entrada de la aplicación FastAPI (Solary backend)."""

from __future__ import annotations

import asyncio
import logging
import sys

# En Windows, psycopg 3 en modo async requiere SelectorEventLoop (el default
# ProactorEventLoop no es compatible). Debe fijarse antes de crear el loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.v1 import auth as auth_router
from app.api.v1 import catalogos as catalogos_router
from app.api.v1 import health as health_router
from app.api.v1 import legal as legal_router
from app.api.v1 import notificaciones as notificaciones_router
from app.api.v1 import perfil as perfil_router
from app.api.v1 import postulaciones as postulaciones_router
from app.api.v1 import publicaciones as publicaciones_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="Backend de autenticación de Solary (migración a Python).",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"message": "Demasiadas solicitudes. Intenta de nuevo más tarde."},
        )

    # CORS explícito (nunca "*" con credenciales).
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept"],
        )

    register_exception_handlers(app)

    prefix = settings.api_v1_prefix
    app.include_router(health_router.router, prefix=prefix)
    app.include_router(auth_router.router, prefix=prefix)
    app.include_router(legal_router.router, prefix=prefix)
    app.include_router(catalogos_router.router, prefix=prefix)
    app.include_router(publicaciones_router.router, prefix=prefix)
    app.include_router(postulaciones_router.router, prefix=prefix)
    app.include_router(notificaciones_router.router, prefix=prefix)
    app.include_router(perfil_router.router, prefix=prefix)

    return app


app = create_app()
