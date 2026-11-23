"""Excepciones de dominio y manejadores centralizados.

Los manejadores garantizan respuestas JSON consistentes y NUNCA exponen trazas
internas, SQL ni detalles sensibles al cliente.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("solari.errors")

# Código de validación (evita la constante deprecada de starlette en 3.16).
HTTP_422 = 422


class AppError(Exception):
    """Error de aplicación con mensaje seguro para el cliente."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, message: str = "No autenticado."):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = "No tienes permisos para esta acción."):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso no encontrado."):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflicto con el estado actual del recurso."):
        super().__init__(message, status.HTTP_409_CONFLICT)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Formato compatible con el patrón Laravel: {message, errors: {campo: [..]}}
        errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            field = ".".join(loc) or "general"
            errors.setdefault(field, []).append(err.get("msg", "Valor inválido."))
        return JSONResponse(
            status_code=HTTP_422,
            content={"message": "Los datos enviados no son válidos.", "errors": errors},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        # Se registra el detalle en el servidor, pero el cliente recibe algo genérico.
        logger.error("Error de base de datos", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "El servicio no está disponible temporalmente."},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Error no controlado", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Ocurrió un error interno."},
        )
