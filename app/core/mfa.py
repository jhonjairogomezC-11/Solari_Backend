"""Primitivas de seguridad de cuenta: TOTP, códigos de respaldo, token MFA y resumen de UA.

Funciones puras (sin BD) para poder probarlas de forma aislada.

Decisiones de seguridad:
- Claves derivadas con HKDF-SHA256 a partir de `settings.jwt_secret`, con un `info`
  distinto por propósito. Así el token MFA NO se firma con la misma clave que el
  access JWT y nunca puede ser aceptado como token de acceso (ni por Python ni por
  Laravel), y el cifrado del secreto TOTP usa otra clave independiente.
- El secreto TOTP se guarda cifrado con Fernet (AES-128-CBC + HMAC-SHA256).
- Los códigos de respaldo son aleatorios de ~50 bits y se guardan solo como hash
  SHA-256; se consumen al usarse.
- Verificación TOTP con ventana ±1 paso (30 s) y protección anti-replay: un paso ya
  aceptado no puede reutilizarse.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import jwt
import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import Settings

MFA_TOKEN_TTL_SECONDS = 300
MFA_TOKEN_TYP = "mfa"  # noqa: S105 - etiqueta del tipo de token, no un secreto
MFA_ISSUER = "Solari"
NUM_CODIGOS_RESPALDO = 8
TOTP_VALID_WINDOW = 1

# Colombia no usa horario de verano: UTC-5 fijo (evita depender de tzdata en Windows).
ZONA_BOGOTA = timezone(timedelta(hours=-5), "COT")

_HKDF_SALT = b"solari-seguridad-cuenta-v1"
_INFO_FERNET = b"solari:mfa:secret-encryption"
_INFO_MFA_TOKEN = b"solari:mfa:login-token"

# Sin caracteres ambiguos (0/O, 1/I/L).
_ALFABETO_RESPALDO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class MfaSecretError(Exception):
    """El secreto cifrado no pudo descifrarse (p. ej. cambió JWT_SECRET)."""


# ─────────────────────────── Derivación de claves ───────────────────────────


def derivar_clave(settings: Settings, info: bytes, length: int = 32) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=_HKDF_SALT, info=info)
    return hkdf.derive(settings.jwt_secret.encode("utf-8"))


def _fernet(settings: Settings) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(derivar_clave(settings, _INFO_FERNET)))


def cifrar_secreto(settings: Settings, secreto: str) -> str:
    return _fernet(settings).encrypt(secreto.encode("utf-8")).decode("ascii")


def descifrar_secreto(settings: Settings, cifrado: str) -> str:
    try:
        return _fernet(settings).decrypt(cifrado.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise MfaSecretError("No fue posible descifrar el secreto MFA.") from exc


# ─────────────────────────── TOTP ───────────────────────────


def generar_secreto() -> str:
    return pyotp.random_base32()  # 32 caracteres base32 = 160 bits


def otpauth_uri(secreto: str, email: str) -> str:
    return pyotp.TOTP(secreto).provisioning_uri(name=email, issuer_name=MFA_ISSUER)


def qr_svg_data_uri(uri: str) -> str:
    qr = segno.make(uri, error="m")
    return qr.svg_data_uri(scale=5, border=2, dark="#111827", light="#ffffff")


def normalizar_codigo_totp(codigo: str) -> str:
    return re.sub(r"[\s-]", "", codigo or "")


def es_formato_totp(codigo: str) -> bool:
    return re.fullmatch(r"\d{6}", normalizar_codigo_totp(codigo)) is not None


def verificar_totp(
    secreto: str,
    codigo: str,
    *,
    ultimo_paso: int | None = None,
    ahora: float | None = None,
    ventana: int = TOTP_VALID_WINDOW,
) -> int | None:
    """Verifica un código TOTP. Devuelve el paso temporal aceptado o None.

    Equivale a `pyotp.TOTP.verify(codigo, valid_window=1)` pero además rechaza pasos
    iguales o anteriores a `ultimo_paso` (anti-replay).
    """
    codigo = normalizar_codigo_totp(codigo)
    if not re.fullmatch(r"\d{6}", codigo):
        return None
    totp = pyotp.TOTP(secreto)
    t = time.time() if ahora is None else ahora
    paso_actual = int(t // totp.interval)
    for delta in range(-ventana, ventana + 1):
        paso = paso_actual + delta
        if ultimo_paso is not None and paso <= ultimo_paso:
            continue
        if hmac.compare_digest(totp.generate_otp(paso), codigo):
            return paso
    return None


# ─────────────────────────── Códigos de respaldo ───────────────────────────


def generar_codigos_respaldo(n: int = NUM_CODIGOS_RESPALDO) -> list[str]:
    codigos = []
    for _ in range(n):
        raw = "".join(secrets.choice(_ALFABETO_RESPALDO) for _ in range(10))
        codigos.append(f"{raw[:5]}-{raw[5:]}")
    return codigos


def normalizar_codigo_respaldo(codigo: str) -> str:
    return re.sub(r"[\s-]", "", codigo or "").upper()


def hash_codigo_respaldo(codigo: str) -> str:
    return hashlib.sha256(normalizar_codigo_respaldo(codigo).encode("utf-8")).hexdigest()


def consumir_codigo_respaldo(hashes_guardados: list[str] | None, codigo: str) -> list[str] | None:
    """Si `codigo` coincide con algún hash, devuelve la lista sin ese hash; si no, None."""
    if not hashes_guardados or not normalizar_codigo_respaldo(codigo):
        return None
    candidato = hash_codigo_respaldo(codigo)
    encontrado: int | None = None
    # Recorre toda la lista (sin salida temprana) y compara en tiempo constante.
    for i, h in enumerate(hashes_guardados):
        if hmac.compare_digest(h, candidato) and encontrado is None:
            encontrado = i
    if encontrado is None:
        return None
    return [h for i, h in enumerate(hashes_guardados) if i != encontrado]


# ─────────────────────────── Token del segundo paso ───────────────────────────


def crear_mfa_token(settings: Settings, usuario_id: str, *, ahora: datetime | None = None) -> str:
    now = ahora or datetime.now(UTC)
    payload: dict[str, Any] = {
        "typ": MFA_TOKEN_TYP,
        "sub": str(usuario_id),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=MFA_TOKEN_TTL_SECONDS)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, derivar_clave(settings, _INFO_MFA_TOKEN), algorithm="HS256")


def decodificar_mfa_token(settings: Settings, token: str) -> str:
    """Valida el token MFA y devuelve el `sub`. Lanza jwt.PyJWTError si no es válido."""
    payload = jwt.decode(
        token,
        derivar_clave(settings, _INFO_MFA_TOKEN),
        algorithms=["HS256"],
        options={"require": ["exp", "iat", "nbf", "sub", "jti", "typ"]},
    )
    if payload.get("typ") != MFA_TOKEN_TYP:
        raise jwt.InvalidTokenError("Tipo de token inválido.")
    return str(payload["sub"])


# ─────────────────────────── User agent ───────────────────────────


def truncar(valor: str | None, maximo: int) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor[:maximo] if valor else None


def _navegador(ua: str) -> str | None:
    if "Dart/" in ua or "dart:io" in ua:
        return "App móvil Solari"
    reglas = (
        ("Edg", "Edge"),
        ("OPR/", "Opera"),
        ("Opera", "Opera"),
        ("SamsungBrowser", "Samsung Internet"),
        ("FxiOS", "Firefox"),
        ("Firefox/", "Firefox"),
        ("CriOS", "Chrome"),
        ("Chrome/", "Chrome"),
        ("Chromium/", "Chromium"),
    )
    for marca, nombre in reglas:
        if marca in ua:
            return nombre
    if "Safari/" in ua and "Version/" in ua:
        return "Safari"
    return None


def _sistema(ua: str) -> str | None:
    if "Windows" in ua:
        return "Windows"
    if "iPad" in ua:
        return "iPadOS"
    if "iPhone" in ua or "iPod" in ua:
        return "iOS"
    if "Android" in ua:
        return "Android"
    if "CrOS" in ua:
        return "ChromeOS"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "macOS"
    if "Linux" in ua:
        return "Linux"
    return None


def resumen_user_agent(ua: str | None) -> str:
    """Resumen legible: 'Chrome en Windows', 'Safari en iOS', etc."""
    if not ua or not ua.strip():
        return "Dispositivo desconocido"
    nav = _navegador(ua)
    so = _sistema(ua)
    if nav and so:
        return f"{nav} en {so}"
    if nav:
        return nav
    if so:
        return f"Navegador en {so}"
    return "Dispositivo desconocido"


def fecha_bogota(dt: datetime | None = None) -> str:
    """Fecha y hora en Bogotá: '29/11/2026 a las 3:45 p. m.'."""
    dt = (dt or datetime.now(UTC)).astimezone(ZONA_BOGOTA)
    hora = dt.hour % 12 or 12
    sufijo = "a. m." if dt.hour < 12 else "p. m."
    return f"{dt:%d/%m/%Y} a las {hora}:{dt:%M} {sufijo}"
