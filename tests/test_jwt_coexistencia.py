"""Verifica la compatibilidad de JWT entre Laravel (jwt-auth) y el backend Python.

Simula un token emitido por Laravel con los claims de jwt-auth (incluido `prv`
= sha1('App\\Models\\Usuario')) y confirma que el decoder de Python lo acepta.
También confirma que un token emitido por Python contiene el mismo `prv`.
"""

from __future__ import annotations

import hashlib
import time
import uuid

import jwt

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token

SECRET = "secreto-compartido-con-laravel-suficientemente-largo"


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        jwt_secret=SECRET,
        jwt_provider_model="App\\Models\\Usuario",
    )


def _prv() -> str:
    return hashlib.sha1(b"App\\Models\\Usuario").hexdigest()  # noqa: S324


def test_python_acepta_token_estilo_laravel():
    s = _settings()
    now = int(time.time())
    token_laravel = jwt.encode(
        {
            "iss": "http://localhost:8000/api/v1/auth/login",
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
            "sub": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "prv": _prv(),
            "rol": "VOLUNTARIO",
            "estado": "ACTIVO",
        },
        SECRET,
        algorithm="HS256",
    )
    claims = decode_access_token(s, token_laravel)
    assert claims["prv"] == _prv()
    assert claims["rol"] == "VOLUNTARIO"


def test_token_python_tiene_prv_compatible_con_laravel():
    s = _settings()
    token, _ = create_access_token(s, subject="u-1", rol="FUNDACION", estado="ACTIVO")
    # Decodificado con la misma lógica que usaría Laravel (verificando prv).
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert claims["prv"] == _prv()
    assert claims["sub"] == "u-1"
