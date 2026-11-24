"""Punto de entrada de la aplicación FastAPI (Solari backend)."""

from __future__ import annotations

import asyncio
import logging
import sys

# En Windows, psycopg 3 en modo async requiere SelectorEventLoop (el default
# ProactorEventLoop no es compatible). Debe fijarse antes de crear el loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pathlib import Path  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.v1 import admin as admin_router
from app.api.v1 import admin_gestion as admin_gestion_router
from app.api.v1 import archivos as archivos_router
from app.api.v1 import auth as auth_router
from app.api.v1 import calendario as calendario_router
from app.api.v1 import catalogos as catalogos_router
from app.api.v1 import certificados as certificados_router
from app.api.v1 import cuenta as cuenta_router
from app.api.v1 import favoritos as favoritos_router
from app.api.v1 import gamificacion as gamificacion_router
from app.api.v1 import habilidades as habilidades_router
from app.api.v1 import health as health_router
from app.api.v1 import legal as legal_router
from app.api.v1 import menores as menores_router
from app.api.v1 import mensajes_postulacion as mensajes_postulacion_router
from app.api.v1 import notificaciones as notificaciones_router
from app.api.v1 import ofrecimientos as ofrecimientos_router
from app.api.v1 import organizaciones as organizaciones_router
from app.api.v1 import perfil as perfil_router
from app.api.v1 import postulaciones as postulaciones_router
from app.api.v1 import programaciones as programaciones_router
from app.api.v1 import publicaciones as publicaciones_router
from app.api.v1 import seguridad as seguridad_router
from app.api.v1 import soporte as soporte_router
from app.core.config import get_settings
from app.core.tareas import lifespan_tareas
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.services.storage_service import CARPETAS_PUBLICAS

logging.basicConfig(level=logging.INFO)


class PublicStaticFiles(StaticFiles):
    """StaticFiles que solo sirve las carpetas públicas y rechaza cualquier otra."""

    async def get_response(self, path: str, scope):  # type: ignore[no-untyped-def]
        from starlette.exceptions import HTTPException

        primera = path.replace("\\", "/").lstrip("/").split("/")[0]
        if primera not in CARPETAS_PUBLICAS:
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="Backend de autenticación de Solari (migración a Python).",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan_tareas,
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
            allow_headers=["Authorization", "Content-Type", "Accept", "X-Refresh-Token"],
        )

    register_exception_handlers(app)

    # Servir SOLO imágenes públicas (fotos, logos, galerías, fotos de publicaciones).
    # Los documentos de identidad y de verificación son privados: se entregan solo
    # por /archivos/privado, con autenticación y control de propiedad (R10).
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    Path(settings.private_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", PublicStaticFiles(directory=str(upload_path)), name="uploads")

    prefix = settings.api_v1_prefix
    app.include_router(health_router.router, prefix=prefix)
    app.include_router(auth_router.router, prefix=prefix)
    app.include_router(legal_router.router, prefix=prefix)
    app.include_router(catalogos_router.router, prefix=prefix)
    app.include_router(calendario_router.router, prefix=prefix)
    app.include_router(publicaciones_router.router, prefix=prefix)
    app.include_router(postulaciones_router.router, prefix=prefix)
    app.include_router(certificados_router.router, prefix=prefix)
    app.include_router(notificaciones_router.router, prefix=prefix)
    app.include_router(mensajes_postulacion_router.router, prefix=prefix)
    app.include_router(perfil_router.router, prefix=prefix)
    app.include_router(menores_router.router, prefix=prefix)
    app.include_router(favoritos_router.router, prefix=prefix)
    app.include_router(gamificacion_router.router, prefix=prefix)
    app.include_router(soporte_router.router, prefix=prefix)
    app.include_router(seguridad_router.router, prefix=prefix)
    app.include_router(cuenta_router.router, prefix=prefix)
    app.include_router(habilidades_router.router, prefix=prefix)
    app.include_router(programaciones_router.router, prefix=prefix)
    app.include_router(ofrecimientos_router.router, prefix=prefix)
    app.include_router(organizaciones_router.router, prefix=prefix)
    app.include_router(archivos_router.router, prefix=prefix)
    app.include_router(admin_router.router, prefix=prefix)
    app.include_router(admin_gestion_router.router, prefix=prefix)

    return app


app = create_app()
