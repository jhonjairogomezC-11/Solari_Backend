"""Pruebas sin base de datos: ticket SSE, formato de eventos y reglas del chat."""

from __future__ import annotations

import json
import time
import uuid

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    create_sse_ticket,
    decode_access_token,
    decode_sse_ticket,
)
from app.schemas.mensaje_postulacion import MensajePostulacionInput
from app.services.coincidencia import contiene_datos_personales
from app.services.mensaje_postulacion_service import ESTADOS_CHAT_VISIBLE, puede_escribir
from app.services.notificacion_stream import formatear_evento, latido

SECRET = "secreto-de-pruebas-sse-suficientemente-largo"


def _settings() -> Settings:
    return Settings(jwt_secret=SECRET)  # type: ignore[call-arg]


# ── Ticket SSE ──

def test_ticket_se_crea_y_verifica():
    s = _settings()
    uid = str(uuid.uuid4())
    ticket, ttl = create_sse_ticket(s, subject=uid)
    assert ttl == 60
    payload = decode_sse_ticket(s, ticket)
    assert payload["sub"] == uid
    assert payload["typ"] == "sse"
    assert payload["exp"] - payload["iat"] == 60


def test_ticket_rechaza_token_de_acceso():
    s = _settings()
    token, _ = create_access_token(s, subject="u-1", rol="VOLUNTARIO", estado="ACTIVO")
    with pytest.raises(jwt.PyJWTError):
        decode_sse_ticket(s, token)


def test_ticket_rechaza_typ_distinto():
    now = int(time.time())
    otro = jwt.encode(
        {"typ": "refresh", "sub": "u-1", "iat": now, "exp": now + 60}, SECRET, algorithm="HS256"
    )
    with pytest.raises(jwt.PyJWTError):
        decode_sse_ticket(_settings(), otro)


def test_ticket_vencido():
    s = _settings()
    ticket, _ = create_sse_ticket(s, subject="u-1", ttl_seconds=-5)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_sse_ticket(s, ticket)


def test_ticket_con_otra_firma():
    ticket, _ = create_sse_ticket(
        Settings(jwt_secret="otro-secreto-distinto-y-largo-para-pruebas"),  # type: ignore[call-arg]
        subject="u-1",
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_sse_ticket(_settings(), ticket)


def test_ticket_no_sirve_como_token_de_acceso():
    s = _settings()
    ticket, _ = create_sse_ticket(s, subject="u-1")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(s, ticket)


# ── Formato SSE ──

def test_formato_evento_sse():
    texto = formatear_evento("notificacion", {"no_leidas": 3, "ultima": {"mensaje": "Hola ñ"}})
    assert texto.startswith("event: notificacion\ndata: ")
    assert texto.endswith("\n\n")
    linea = texto.split("\n")[1].removeprefix("data: ")
    assert json.loads(linea) == {"no_leidas": 3, "ultima": {"mensaje": "Hola ñ"}}


def test_latido_es_comentario():
    assert latido().startswith(":")
    assert latido().endswith("\n\n")


# ── Reglas del chat ──

@pytest.mark.parametrize("estado", ["ACEPTADO", "EN_REVISION", "LISTA_ESPERA"])
def test_estados_con_escritura(estado):
    assert puede_escribir(estado)
    assert estado in ESTADOS_CHAT_VISIBLE


@pytest.mark.parametrize(
    "estado",
    ["PENDIENTE", "ASISTIO", "NO_ASISTIO", "RETIRADO", "RECHAZADO", "CANCELADO_FUNDACION"],
)
def test_estados_solo_lectura(estado):
    assert not puede_escribir(estado)


def test_mensaje_largo_y_vacio_rechazados():
    with pytest.raises(ValueError):
        MensajePostulacionInput(mensaje="x" * 1001)
    with pytest.raises(ValueError):
        MensajePostulacionInput(mensaje="   ")
    assert MensajePostulacionInput(mensaje="  hola  ").mensaje == "hola"


def test_filtro_datos_personales_en_chat():
    assert contiene_datos_personales("mi correo es a@b.co")
    assert not contiene_datos_personales("Llego a las 8 con guantes")
