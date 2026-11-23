"""Pruebas unitarias (sin base de datos) de las reglas del documento de grado."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.ofrecimiento import OfrecimientoCreate
from app.schemas.perfil import FundacionPerfilInput
from app.services.coincidencia import (
    calcular_coincidencia,
    contiene_datos_personales,
    contiene_lenguaje_ofensivo,
    textos_relacionados,
)
from app.services.gamificacion_service import calcular_nivel
from app.services.organizacion_service import motivo_moderacion
from app.services.postulacion_service import msg_rechazada
from app.services.programacion_service import siguiente_fecha, sumar_meses
from app.services.recomendacion_service import es_compatible_con_disponibilidad


# ── Coincidencia de habilidades (sección 4.4) ──
def test_coincidencia_ejemplo_del_documento():
    voluntario = {1, 2, 3, 4, 5}  # perros, gatos, baño, limpieza, jardinería
    assert calcular_coincidencia({3, 4, 1}, voluntario) == 100  # baño, limpieza, perros
    assert calcular_coincidencia({5, 90, 91}, voluntario) == 33  # jardinería + 2 que no tiene
    assert calcular_coincidencia({90, 91, 92}, voluntario) == 0  # enfermería, psicología...


def test_coincidencia_sin_requeridas_es_cero():
    assert calcular_coincidencia([], {1, 2}) == 0


# ── Intereses vs áreas de impacto (tolerante a tildes y plurales) ──
@pytest.mark.parametrize(
    ("area", "interes"),
    [
        ("Educacion", "Educación"),
        ("Tecnologia", "Tecnología"),
        ("Deportes", "Deporte"),
        ("Inclusion Social", "Inclusión social"),
        ("Salud", "Salud y bienestar"),
        ("Medio Ambiente", "Ambiental"),
        ("Cultura", "Cultura y arte"),
    ],
)
def test_interes_se_relaciona_con_area(area, interes):
    assert textos_relacionados(area, interes)


def test_interes_no_relacionado():
    assert not textos_relacionados("Salud", "Tecnología")


# ── Niveles: reconocimiento visual, sin desbloqueos (sección 4.9) ──
def test_niveles():
    assert calcular_nivel(0)["nivel"] == 1
    assert calcular_nivel(99)["nivel_nombre"] == "Chispa"
    assert calcular_nivel(100)["nivel"] == 2
    ultimo = calcular_nivel(999_999)
    assert ultimo["nivel"] == 8 and ultimo["xp_siguiente_nivel"] is None


# ── Recurrencia (R4) ──
def test_siguiente_fecha_dias_semanas_meses():
    assert siguiente_fecha(date(2026, 12, 1), "DIAS", 3) == date(2026, 12, 4)
    assert siguiente_fecha(date(2026, 12, 1), "SEMANAS", 2) == date(2026, 12, 15)
    assert siguiente_fecha(date(2026, 1, 31), "MESES", 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 11, 15), 2) == date(2027, 1, 15)


# ── Moderación y privacidad ──
def test_deteccion_datos_personales():
    assert contiene_datos_personales("escríbeme a ana@correo.com")
    assert contiene_datos_personales("llámame al 300 123 4567")
    assert contiene_datos_personales("mira https://sitio.com")
    assert not contiene_datos_personales("Nos vemos el sábado a las 9")


def test_deteccion_lenguaje_ofensivo_y_motivo():
    assert contiene_lenguaje_ofensivo("son unos estúpidos")
    assert motivo_moderacion("Excelente experiencia, muy bien organizada.") is None
    assert motivo_moderacion("son unos idiotas") is not None
    assert motivo_moderacion("contáctame 3001234567") is not None


def test_plantilla_de_rechazo_es_respetuosa():
    texto = msg_rechazada("Jornada", None)
    assert "Gracias por tu interés" in texto and "Valoramos el tiempo" in texto


# ── Disponibilidad ──
class _Pub:
    def __init__(self, inicio: date, fin: date):
        self.fecha_inicio, self.fecha_fin = inicio, fin


def test_compatibilidad_con_disponibilidad():
    sabado = _Pub(date(2026, 12, 5), date(2026, 12, 5))
    lunes = _Pub(date(2026, 12, 7), date(2026, 12, 7))
    assert es_compatible_con_disponibilidad(sabado, "FINES_DE_SEMANA")
    assert not es_compatible_con_disponibilidad(sabado, "ENTRE_SEMANA")
    assert es_compatible_con_disponibilidad(lunes, "ENTRE_SEMANA")
    assert not es_compatible_con_disponibilidad(lunes, "FINES_DE_SEMANA")
    assert es_compatible_con_disponibilidad(sabado, "FLEXIBLE")


# ── Organizaciones sin constitución legal (R13) ──
_BASE_ORG = dict(
    nombre_fundacion="Refugio Patitas",
    representante_legal="Ana Pérez",
    telefono_contacto="3001234567",
    direccion="Calle 1 # 2-3",
    municipio_id=1,
    descripcion="Refugio independiente de animales.",
)


def test_organizacion_sin_constitucion_no_exige_nit():
    org = FundacionPerfilInput(**_BASE_ORG, tipo_organizacion="REFUGIO", constituida_legalmente=False)
    assert org.nit is None and org.documento_legal is None


def test_organizacion_constituida_exige_nit_y_documento():
    with pytest.raises(ValidationError):
        FundacionPerfilInput(**_BASE_ORG, constituida_legalmente=True)
    ok = FundacionPerfilInput(
        **_BASE_ORG, nit="900123456-7", documento_legal="Certificado de existencia"
    )
    assert ok.nit == "900123456-7"


# ── Objetos y servicios gratuitos (R1) ──
_BASE_OBJ = dict(
    tipo="OBJETO", categoria="Libros y material educativo", cantidad_total=5,
    estado_producto="USADO_BUEN_ESTADO", modalidad_entrega="A_CONVENIR", municipio_id=1,
)


def test_ofrecimiento_gratuito_rechaza_precios():
    with pytest.raises(ValidationError):
        OfrecimientoCreate(**_BASE_OBJ, titulo="Libros a buen precio", descripcion="Vendo 5 libros infantiles")
    with pytest.raises(ValidationError):
        OfrecimientoCreate(**_BASE_OBJ, titulo="Libros infantiles", descripcion="Cada uno $ 5000 pesos")


def test_ofrecimiento_gratuito_valido():
    o = OfrecimientoCreate(
        **_BASE_OBJ, titulo="Libros infantiles", descripcion="Cinco libros en buen estado, sin costo."
    )
    assert o.cantidad_total == 5


def test_servicio_requiere_habilidades():
    with pytest.raises(ValidationError):
        OfrecimientoCreate(
            tipo="SERVICIO", titulo="Pintura de fachada", descripcion="Pinto fachadas de forma gratuita.",
            categoria="Pintura", modalidad_entrega="PRESENCIAL", municipio_id=1,
        )
