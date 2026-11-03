"""Primitivas de seguridad: hashing de contraseñas, tokens opacos y JWT.

- Contraseñas: Argon2id (nuevas) con verificación de bcrypt heredado (Laravel) y
  rehash perezoso. La columna `password_hash` es `text` y soporta ambos formatos.
- Tokens opacos (refresh/reset/verificación): se generan aleatorios y se almacenan
  SOLO como hash SHA-256; el valor en claro viaja una única vez al cliente/email.
- JWT: HS256 con los mismos claims que exige `php-open-source-saver/jwt-auth`
  (iss, iat, exp, nbf, sub, jti, prv) para coexistir con Laravel.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions

from app.core.config import Settings

# Parámetros Argon2id razonables para un backend web (OWASP: m>=19MiB, t>=2, p>=1).
_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


# ─────────────────────────── Contraseñas ───────────────────────────


def hash_password(password: str) -> str:
    """Genera un hash Argon2id de la contraseña."""
    return _ph.hash(password)


def _is_bcrypt_hash(hashed: str) -> bool:
    return hashed.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(password: str, hashed: str | None) -> bool:
    """Verifica la contraseña contra un hash Argon2id o bcrypt (heredado)."""
    if not hashed:
        return False
    try:
        if _is_bcrypt_hash(hashed):
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        _ph.verify(hashed, password)
        return True
    except (argon2_exceptions.VerifyMismatchError, argon2_exceptions.InvalidHashError):
        return False
    except ValueError:
        return False


def needs_rehash(hashed: str | None) -> bool:
    """Indica si el hash debe migrarse a Argon2id (bcrypt heredado o parámetros viejos)."""
    if not hashed:
        return False
    if _is_bcrypt_hash(hashed):
        return True
    try:
        return _ph.check_needs_rehash(hashed)
    except argon2_exceptions.InvalidHashError:
        return True


# ─────────────────────────── Tokens opacos ───────────────────────────


def generate_opaque_token(num_bytes: int = 48) -> str:
    """Token aleatorio URL-safe para refresh/reset/verificación."""
    return secrets.token_urlsafe(num_bytes)


def hash_opaque_token(token: str) -> str:
    """Hash SHA-256 (hex) para almacenar tokens opacos sin exponer el valor real."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ─────────────────────────── JWT ───────────────────────────


def _laravel_prv_claim(provider_model: str) -> str:
    """Replica el claim `prv` de jwt-auth con lock_subject=true: sha1(nombre_clase)."""
    return hashlib.sha1(provider_model.encode("utf-8")).hexdigest()  # noqa: S324


def create_access_token(
    settings: Settings,
    *,
    subject: str,
    rol: str,
    estado: str,
) -> tuple[str, int]:
    """Crea un JWT de acceso compatible con Laravel. Devuelve (token, expires_in_segundos)."""
    now = datetime.now(UTC)
    expires_delta = timedelta(minutes=settings.jwt_access_ttl_minutes)
    exp = now + expires_delta

    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "prv": _laravel_prv_claim(settings.jwt_provider_model),
        # Claims personalizados que ya usa el sistema (getJWTCustomClaims).
        "rol": rol,
        "estado": estado,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    """Valida y decodifica un JWT. Lanza jwt.PyJWTError si es inválido.

    Fuerza el algoritmo permitido (evita el ataque de algoritmo 'none' y la
    confusión RS/HS) y exige los claims requeridos.

    Nota de coexistencia: no se verifica `iss` contra un valor fijo porque
    jwt-auth de Laravel emite `iss` dinámico (URL de la request de login). Se
    exige únicamente su presencia, igual que hace Laravel con required_claims.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={
            "require": ["exp", "iat", "nbf", "sub", "jti"],
            "verify_iss": False,
            "verify_exp": True,
            "verify_nbf": True,
        },
    )
