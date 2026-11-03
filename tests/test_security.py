"""Pruebas unitarias de seguridad: hashing y JWT (sin base de datos)."""

from __future__ import annotations

import bcrypt
import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    needs_rehash,
    verify_password,
)


def _settings() -> Settings:
    return Settings(jwt_secret="secreto-de-prueba-suficientemente-largo-123")  # type: ignore[call-arg]


def test_argon2_hash_y_verificacion():
    h = hash_password("Clave123Segura")
    assert h.startswith("$argon2")
    assert verify_password("Clave123Segura", h)
    assert not verify_password("otra", h)


def test_password_vacio_o_none_no_valida():
    assert not verify_password("algo", None)
    assert not verify_password("algo", "")


def test_bcrypt_heredado_se_verifica_y_requiere_rehash():
    # Simula un hash creado por Laravel (bcrypt).
    bcrypt_hash = bcrypt.hashpw(b"Clave123Segura", bcrypt.gensalt(rounds=10)).decode()
    assert verify_password("Clave123Segura", bcrypt_hash)
    assert needs_rehash(bcrypt_hash) is True
    # Un hash argon2 fresco no requiere rehash.
    assert needs_rehash(hash_password("Clave123Segura")) is False


def test_tokens_opacos_se_hashean():
    raw = generate_opaque_token()
    assert len(raw) > 20
    h = hash_opaque_token(raw)
    assert len(h) == 64
    assert h == hash_opaque_token(raw)  # determinista
    assert h != raw  # el hash no es el valor en claro


def test_jwt_contiene_claims_compatibles_con_laravel():
    s = _settings()
    token, expires_in = create_access_token(
        s, subject="abc-123", rol="VOLUNTARIO", estado="ACTIVO"
    )
    assert expires_in == s.jwt_access_ttl_minutes * 60
    claims = decode_access_token(s, token)
    for required in ("iss", "iat", "exp", "nbf", "sub", "jti", "prv"):
        assert required in claims
    assert claims["sub"] == "abc-123"
    assert claims["rol"] == "VOLUNTARIO"
    assert claims["estado"] == "ACTIVO"


def test_jwt_rechaza_algoritmo_none():
    s = _settings()
    # Token firmado con 'none' debe ser rechazado.
    malicioso = jwt.encode({"sub": "x"}, key="", algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(s, malicioso)


def test_jwt_rechaza_firma_con_otro_secreto():
    s = _settings()
    otro = jwt.encode(
        {"sub": "x", "iss": "i", "iat": 0, "nbf": 0, "exp": 9999999999, "jti": "1"},
        "secreto-distinto",
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(s, otro)
