"""Pruebas unitarias (sin BD) del código de verificación y la generación del PDF."""

from __future__ import annotations

import re
import uuid
from datetime import date

from app.services.certificado_service import (
    DatosCertificado,
    codigo_es_valido,
    codigo_verificacion,
    generar_pdf,
    nombre_publico,
)

SECRETO = "secreto-de-prueba-suficientemente-largo-123"
PID = uuid.UUID("3f2b8c1e-9a4d-4e6f-8b2a-1c3d5e7f9a0b")


def test_codigo_formato_y_determinismo():
    codigo = codigo_verificacion(SECRETO, PID)
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}", codigo)
    assert codigo == codigo_verificacion(SECRETO, str(PID))


def test_codigo_depende_del_secreto_y_la_postulacion():
    base = codigo_verificacion(SECRETO, PID)
    assert base != codigo_verificacion("otro-secreto-distinto-1234567890", PID)
    assert base != codigo_verificacion(SECRETO, uuid.uuid4())


def test_codigo_es_valido_tolera_formato():
    codigo = codigo_verificacion(SECRETO, PID)
    assert codigo_es_valido(SECRETO, PID, codigo)
    assert codigo_es_valido(SECRETO, PID, codigo.lower().replace("-", " "))
    assert not codigo_es_valido(SECRETO, PID, "0000-0000-0000")
    assert not codigo_es_valido(SECRETO, PID, "")


def test_nombre_publico():
    assert nombre_publico("Ana María Pérez Gómez") == "Ana G."
    assert nombre_publico("Iñaki") == "Iñaki"
    assert nombre_publico("  ") == ""


def test_generar_pdf_con_tildes():
    datos = DatosCertificado(
        postulacion_id=PID,
        voluntario_nombre="José Peña Muñoz",
        tipo_documento="CC",
        numero_documento="1020304050",
        actividad="Jornada de reforestación en Usaquén",
        organizacion="Fundación Árboles de Bogotá",
        fecha_inicio=date(2025, 3, 8),
        fecha_fin=date(2025, 3, 9),
        horas=6,
        fecha_emision=date(2025, 3, 10),
        codigo=codigo_verificacion(SECRETO, PID),
    )
    pdf = generar_pdf(datos)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_generar_pdf_sin_documento_ni_horas_y_caracteres_fuera_de_latin1():
    datos = DatosCertificado(
        postulacion_id=PID,
        voluntario_nombre="Ana 🌞 Ruiz",
        actividad="Taller — virtual",
        organizacion="Colectivo Sol",
        fecha_inicio=date(2025, 1, 15),
        fecha_fin=date(2025, 1, 15),
        horas=0,
        fecha_emision=date(2025, 1, 16),
        codigo="ABCD-EF01-2345",
    )
    assert generar_pdf(datos).startswith(b"%PDF")


def test_generar_pdf_textos_largos():
    datos = DatosCertificado(
        postulacion_id=PID,
        voluntario_nombre="María de los Ángeles Rodríguez Castañeda Villamizar Ospina",
        tipo_documento="PASAPORTE",
        numero_documento="AB1234567",
        actividad="Acompañamiento " * 13,
        organizacion="Organización comunitaria " * 5,
        fecha_inicio=date(2025, 5, 1),
        fecha_fin=date(2025, 6, 30),
        horas=1,
        fecha_emision=date(2025, 7, 1),
        codigo=codigo_verificacion(SECRETO, PID),
    )
    assert generar_pdf(datos).startswith(b"%PDF")
