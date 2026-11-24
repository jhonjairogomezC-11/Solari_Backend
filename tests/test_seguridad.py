"""Pruebas unitarias (sin BD) de seguridad de cuenta: token MFA, TOTP, códigos de
respaldo, cifrado del secreto y resumen de user agent."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest

from app.core import mfa
from app.core.config import Settings
from app.core.security import decode_access_token

SECRET = "secreto-de-prueba-suficientemente-largo-123"


def _settings(secret: str = SECRET) -> Settings:
    return Settings(jwt_secret=secret)  # type: ignore[call-arg]


# ─────────────── Token MFA ───────────────


def test_mfa_token_tiene_typ_mfa_y_expira_en_5_minutos():
    s = _settings()
    token = mfa.crear_mfa_token(s, "user-123")
    claims = jwt.decode(
        token, mfa.derivar_clave(s, b"solari:mfa:login-token"), algorithms=["HS256"]
    )
    assert claims["typ"] == "mfa"
    assert claims["sub"] == "user-123"
    assert claims["exp"] - claims["iat"] == 300
    assert mfa.decodificar_mfa_token(s, token) == "user-123"


def test_mfa_token_expirado_es_rechazado():
    s = _settings()
    hace_10_min = datetime.now(UTC) - timedelta(minutes=10)
    token = mfa.crear_mfa_token(s, "user-123", ahora=hace_10_min)
    with pytest.raises(jwt.ExpiredSignatureError):
        mfa.decodificar_mfa_token(s, token)


def test_mfa_token_no_sirve_como_access_token():
    s = _settings()
    token = mfa.crear_mfa_token(s, "user-123")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(s, token)
    # Tampoco valida con el secreto compartido con Laravel.
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, SECRET, algorithms=["HS256"])


def test_token_sin_typ_mfa_es_rechazado():
    s = _settings()
    clave = mfa.derivar_clave(s, b"solari:mfa:login-token")
    now = int(time.time())
    token = jwt.encode(
        {"typ": "access", "sub": "u", "iat": now, "nbf": now, "exp": now + 60, "jti": "x"},
        clave,
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        mfa.decodificar_mfa_token(s, token)


def test_mfa_token_de_otro_secreto_es_rechazado():
    token = mfa.crear_mfa_token(_settings(), "user-123")
    with pytest.raises(jwt.InvalidSignatureError):
        mfa.decodificar_mfa_token(_settings("otro-secreto-distinto-suficientemente-largo"), token)


# ─────────────── TOTP ───────────────


def test_totp_valido_y_ventana_de_un_paso():
    secreto = mfa.generar_secreto()
    totp = pyotp.TOTP(secreto)
    ahora = time.time()
    actual = totp.at(ahora)
    assert mfa.verificar_totp(secreto, actual, ahora=ahora) is not None
    # Un paso antes/después se acepta (valid_window=1), dos pasos no.
    assert mfa.verificar_totp(secreto, totp.at(ahora - 30), ahora=ahora) is not None
    assert mfa.verificar_totp(secreto, totp.at(ahora + 30), ahora=ahora) is not None
    viejo = totp.at(ahora - 90)
    if viejo not in {actual, totp.at(ahora - 30), totp.at(ahora + 30)}:
        assert mfa.verificar_totp(secreto, viejo, ahora=ahora) is None


def test_totp_coincide_con_pyotp_verify():
    secreto = mfa.generar_secreto()
    totp = pyotp.TOTP(secreto)
    codigo = totp.now()
    assert totp.verify(codigo, valid_window=1)
    assert mfa.verificar_totp(secreto, codigo) is not None


def test_totp_rechaza_formato_invalido_y_codigo_erroneo():
    secreto = mfa.generar_secreto()
    assert mfa.verificar_totp(secreto, "abcdef") is None
    assert mfa.verificar_totp(secreto, "12345") is None
    codigo = pyotp.TOTP(secreto).now()
    erroneo = f"{(int(codigo) + 1) % 1_000_000:06d}"
    ahora = time.time()
    validos = {pyotp.TOTP(secreto).at(ahora + d) for d in (-30, 0, 30)}
    if erroneo not in validos:
        assert mfa.verificar_totp(secreto, erroneo, ahora=ahora) is None


def test_totp_anti_replay():
    secreto = mfa.generar_secreto()
    ahora = time.time()
    codigo = pyotp.TOTP(secreto).at(ahora)
    paso = mfa.verificar_totp(secreto, codigo, ahora=ahora)
    assert paso is not None
    # El mismo código (mismo paso) no puede reutilizarse.
    assert mfa.verificar_totp(secreto, codigo, ultimo_paso=paso, ahora=ahora) is None


def test_totp_acepta_espacios():
    secreto = mfa.generar_secreto()
    codigo = pyotp.TOTP(secreto).now()
    assert mfa.verificar_totp(secreto, f"{codigo[:3]} {codigo[3:]}") is not None


def test_otpauth_uri_y_qr_svg():
    secreto = mfa.generar_secreto()
    uri = mfa.otpauth_uri(secreto, "ana@example.com")
    assert uri.startswith("otpauth://totp/")
    assert "issuer=Solari" in uri
    assert f"secret={secreto}" in uri
    qr = mfa.qr_svg_data_uri(uri)
    assert qr.startswith("data:image/svg+xml")


# ─────────────── Cifrado del secreto ───────────────


def test_secreto_se_cifra_y_descifra():
    s = _settings()
    secreto = mfa.generar_secreto()
    cifrado = mfa.cifrar_secreto(s, secreto)
    assert secreto not in cifrado
    assert mfa.descifrar_secreto(s, cifrado) == secreto
    with pytest.raises(mfa.MfaSecretError):
        mfa.descifrar_secreto(_settings("otro-secreto-distinto-suficientemente-largo"), cifrado)


# ─────────────── Códigos de respaldo ───────────────


def test_codigos_respaldo_formato_y_unicidad():
    codigos = mfa.generar_codigos_respaldo()
    assert len(codigos) == 8
    assert len(set(codigos)) == 8
    for c in codigos:
        assert len(c) == 11 and c[5] == "-"


def test_codigo_respaldo_hash_normaliza():
    c = "ABCDE-FGHJK"
    h = mfa.hash_codigo_respaldo(c)
    assert len(h) == 64
    assert c not in h
    assert mfa.hash_codigo_respaldo("abcde fghjk") == h
    assert mfa.hash_codigo_respaldo("ABCDEFGHJK") == h


def test_codigo_respaldo_se_consume_una_sola_vez():
    codigos = mfa.generar_codigos_respaldo()
    hashes = [mfa.hash_codigo_respaldo(c) for c in codigos]
    restantes = mfa.consumir_codigo_respaldo(hashes, codigos[3].lower())
    assert restantes is not None
    assert len(restantes) == 7
    assert mfa.hash_codigo_respaldo(codigos[3]) not in restantes
    # Segundo uso del mismo código: rechazado.
    assert mfa.consumir_codigo_respaldo(restantes, codigos[3]) is None
    # Código inexistente o lista vacía: rechazado.
    assert mfa.consumir_codigo_respaldo(restantes, "ZZZZZ-ZZZZZ") is None
    assert mfa.consumir_codigo_respaldo(None, codigos[0]) is None
    assert mfa.consumir_codigo_respaldo(restantes, "") is None


# ─────────────── User agent ───────────────


@pytest.mark.parametrize(
    ("ua", "esperado"),
    [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
            "Chrome en Windows",
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Edge en Windows",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Safari en iOS",
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Firefox en macOS",
        ),
        (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Mobile Safari/537.36",
            "Chrome en Android",
        ),
        ("Dart/3.5 (dart:io)", "App móvil Solari"),
        ("curl/8.0", "Dispositivo desconocido"),
        (None, "Dispositivo desconocido"),
        ("", "Dispositivo desconocido"),
    ],
)
def test_resumen_user_agent(ua, esperado):
    assert mfa.resumen_user_agent(ua) == esperado


def test_truncar_user_agent():
    assert mfa.truncar("x" * 300, 255) == "x" * 255
    assert mfa.truncar(None, 255) is None
    assert mfa.truncar("   ", 255) is None


def test_fecha_bogota_usa_utc_menos_5():
    dt = datetime(2026, 11, 29, 20, 5, tzinfo=UTC)
    assert mfa.fecha_bogota(dt) == "29/11/2026 a las 3:05 p. m."
    dt2 = datetime(2026, 11, 29, 5, 0, tzinfo=UTC)
    assert mfa.fecha_bogota(dt2) == "29/11/2026 a las 12:00 a. m."
