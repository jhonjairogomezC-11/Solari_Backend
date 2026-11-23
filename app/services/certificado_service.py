"""Certificados de participación en PDF y su verificación pública.

El código de verificación es determinista: HMAC-SHA256 del id de la postulación
con el secreto de la aplicación (JWT_SECRET). No se guarda en la base; para
verificar se recalcula y se compara en tiempo constante.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.postulacion import ESTADO_ASISTIO
from app.models.voluntario import Voluntario
from app.repositories.certificado_repo import CertificadoRepository, FilaCertificado
from app.schemas.certificado import VerificacionCertificadoOut

# Colores (RGB)
_NARANJA = (249, 115, 22)  # Solari #f97316
_NARANJA_SUAVE = (255, 237, 213)
_TINTA = (31, 41, 55)
_GRIS = (107, 114, 128)

_TIPOS_DOCUMENTO = {
    "CC": "cédula de ciudadanía",
    "TI": "tarjeta de identidad",
    "CE": "cédula de extranjería",
    "PASAPORTE": "pasaporte",
}

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_CODIGO_LIMPIO = re.compile(r"[^0-9A-F]")


# ─────────────── Funciones puras (sin BD) ───────────────

def codigo_verificacion(secreto: str, postulacion_id: uuid.UUID | str) -> str:
    """Código `XXXX-XXXX-XXXX`: 12 primeros hex (mayúsculas) del HMAC-SHA256."""
    digest = hmac.new(
        secreto.encode("utf-8"), str(postulacion_id).encode("utf-8"), hashlib.sha256
    ).hexdigest()[:12].upper()
    return f"{digest[0:4]}-{digest[4:8]}-{digest[8:12]}"


def codigo_es_valido(secreto: str, postulacion_id: uuid.UUID | str, codigo: str) -> bool:
    """Compara en tiempo constante; tolera minúsculas, espacios y guiones."""
    normalizado = _CODIGO_LIMPIO.sub("", codigo.upper())
    esperado = codigo_verificacion(secreto, postulacion_id).replace("-", "")
    return hmac.compare_digest(normalizado, esperado)


def fecha_larga(d: date) -> str:
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def nombre_publico(nombre_completo: str) -> str:
    """Primer nombre + inicial del último apellido: «Ana María Pérez» → «Ana P.»."""
    partes = nombre_completo.split()
    if not partes:
        return ""
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1][0].upper()}."


@dataclass(frozen=True)
class DatosCertificado:
    postulacion_id: uuid.UUID
    voluntario_nombre: str
    actividad: str
    organizacion: str
    fecha_inicio: date
    fecha_fin: date
    horas: int
    fecha_emision: date
    codigo: str
    tipo_documento: str | None = None
    numero_documento: str | None = None


def _latin1(texto: str) -> str:
    """Las fuentes base del PDF usan latin-1 (cubre tildes y ñ); el resto se reemplaza."""
    return texto.encode("latin-1", "replace").decode("latin-1")


def _rango_fechas(inicio: date, fin: date) -> str:
    if inicio == fin:
        return f"el {fecha_larga(inicio)}"
    return f"del {fecha_larga(inicio)} al {fecha_larga(fin)}"


def generar_pdf(datos: DatosCertificado) -> bytes:
    """Genera el certificado (A4 horizontal) y devuelve los bytes del PDF."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(25, 20, 25)
    pdf.set_title(_latin1("Certificado de participación - Solari"))
    pdf.set_author("Solari")
    pdf.set_creator("Solari")
    pdf.add_page()

    ancho, alto = pdf.w, pdf.h  # 297 x 210
    util = ancho - 50

    # Marco
    pdf.set_draw_color(*_NARANJA)
    pdf.set_line_width(1.6)
    pdf.rect(10, 10, ancho - 20, alto - 20)
    pdf.set_line_width(0.3)
    pdf.rect(14, 14, ancho - 28, alto - 28)

    # Encabezado: marca y franja
    pdf.set_fill_color(*_NARANJA)
    pdf.rect(14, 14, ancho - 28, 4, style="F")
    pdf.set_xy(25, 26)
    pdf.set_font("helvetica", style="B", size=22)
    pdf.set_text_color(*_NARANJA)
    pdf.cell(60, 10, "Solari")
    pdf.set_xy(ancho - 25 - 100, 28)
    pdf.set_font("helvetica", size=9)
    pdf.set_text_color(*_GRIS)
    pdf.cell(100, 6, _latin1("Plataforma de voluntariado"), align="R")

    # Título
    pdf.set_xy(25, 48)
    pdf.set_font("helvetica", style="B", size=32)
    pdf.set_text_color(*_TINTA)
    pdf.cell(util, 14, _latin1("Certificado de participación"), align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*_NARANJA)
    pdf.set_line_width(1.2)
    pdf.line(ancho / 2 - 30, 66, ancho / 2 + 30, 66)

    # Destinatario
    pdf.set_xy(25, 74)
    pdf.set_font("helvetica", size=13)
    pdf.set_text_color(*_GRIS)
    pdf.cell(util, 8, _latin1("Solari certifica que"), align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    nombre = _latin1(datos.voluntario_nombre)
    tamano = 26
    pdf.set_font("helvetica", style="B", size=tamano)
    while tamano > 14 and pdf.get_string_width(nombre) > util:
        tamano -= 2
        pdf.set_font("helvetica", style="B", size=tamano)
    pdf.set_text_color(*_TINTA)
    pdf.cell(util, 14, nombre, align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if datos.tipo_documento and datos.numero_documento:
        tipo = _TIPOS_DOCUMENTO.get(datos.tipo_documento, datos.tipo_documento)
        pdf.set_font("helvetica", size=11)
        pdf.set_text_color(*_GRIS)
        pdf.cell(util, 7, _latin1(f"identificado(a) con {tipo} n.º {datos.numero_documento}"),
                 align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Cuerpo
    horas = ""
    if datos.horas > 0:
        unidad = "hora" if datos.horas == 1 else "horas"
        horas = f", con {datos.horas} {unidad} de voluntariado reconocidas"
    cuerpo = (
        f"participó como voluntario(a) en la convocatoria «{datos.actividad}», "
        f"organizada por {datos.organizacion}, realizada "
        f"{_rango_fechas(datos.fecha_inicio, datos.fecha_fin)}{horas}."
    )
    pdf.set_xy(40, pdf.get_y() + 6)
    pdf.set_font("helvetica", size=13 if len(cuerpo) <= 260 else 11)
    pdf.set_text_color(*_TINTA)
    pdf.multi_cell(ancho - 80, 7.5 if len(cuerpo) <= 260 else 6, _latin1(cuerpo), align="C")

    # Recuadro de horas (se omite si el texto es tan largo que no cabe; las horas
    # ya figuran en el cuerpo).
    caja_y = max(pdf.get_y() + 5, 140)
    if datos.horas > 0 and caja_y + 16 <= 165:
        pdf.set_fill_color(*_NARANJA_SUAVE)
        caja_x = ancho / 2 - 30
        pdf.rect(caja_x, caja_y, 60, 16, style="F")
        pdf.set_xy(caja_x, caja_y + 1.5)
        pdf.set_font("helvetica", style="B", size=16)
        pdf.set_text_color(*_NARANJA)
        pdf.cell(60, 8, f"{datos.horas} h", align="C", new_x=XPos.LEFT, new_y=YPos.NEXT)
        pdf.set_font("helvetica", size=8)
        pdf.set_text_color(*_GRIS)
        pdf.cell(60, 5, "horas reconocidas", align="C")

    # Pie: fecha de emisión y verificación
    pdf.set_draw_color(*_NARANJA_SUAVE)
    pdf.set_line_width(0.4)
    pdf.line(25, 168, ancho - 25, 168)

    pdf.set_xy(25, 171)
    pdf.set_font("helvetica", size=9)
    pdf.set_text_color(*_GRIS)
    pdf.cell(120, 5, _latin1("Fecha de emisión"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", style="B", size=11)
    pdf.set_text_color(*_TINTA)
    pdf.cell(120, 6, _latin1(fecha_larga(datos.fecha_emision)))

    pdf.set_xy(ancho - 25 - 120, 171)
    pdf.set_font("helvetica", size=9)
    pdf.set_text_color(*_GRIS)
    pdf.cell(120, 5, _latin1("Código de verificación"), align="R",
             new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font("courier", style="B", size=13)
    pdf.set_text_color(*_NARANJA)
    pdf.cell(120, 6, datos.codigo, align="R")

    pdf.set_xy(25, 184)
    pdf.set_font("helvetica", size=7.5)
    pdf.set_text_color(*_GRIS)
    pdf.cell(
        util, 4,
        _latin1(
            "Verifica la autenticidad de este certificado en Solari con el identificador "
            f"de participación {datos.postulacion_id} y el código de verificación."
        ),
        align="C",
    )

    return bytes(pdf.output())


# ─────────────── Servicio ───────────────

def _fecha_emision(fila: FilaCertificado) -> date:
    confirmacion = fila.postulacion.fecha_confirmacion
    return confirmacion.date() if confirmacion else date.today()


def _certificable(fila: FilaCertificado) -> bool:
    return fila.postulacion.estado == ESTADO_ASISTIO and bool(fila.publicacion.otorga_certificado)


class CertificadoService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.repo = CertificadoRepository(db)
        self.settings = settings

    async def certificado_pdf(
        self, postulacion_id: uuid.UUID, voluntario: Voluntario
    ) -> tuple[bytes, str]:
        """PDF del certificado del voluntario dueño de la postulación y su nombre de archivo."""
        fila = await self.repo.datos_postulacion(postulacion_id)
        # 404 también si no es el dueño: no se revela que la postulación existe.
        if fila is None or fila.postulacion.voluntario_id != voluntario.id:
            raise NotFoundError("Postulación no encontrada.")
        if not fila.publicacion.otorga_certificado:
            raise ConflictError("Esta convocatoria no otorga certificado.")
        if fila.postulacion.estado != ESTADO_ASISTIO:
            raise ConflictError(
                "El certificado está disponible cuando la organización confirma tu asistencia."
            )

        codigo = codigo_verificacion(self.settings.jwt_secret, fila.postulacion.id)
        datos = DatosCertificado(
            postulacion_id=fila.postulacion.id,
            voluntario_nombre=fila.usuario.nombre,
            tipo_documento=fila.voluntario.tipo_documento,
            numero_documento=fila.voluntario.numero_documento,
            actividad=fila.publicacion.titulo,
            organizacion=fila.fundacion.nombre,
            fecha_inicio=fila.publicacion.fecha_inicio,
            fecha_fin=fila.publicacion.fecha_fin,
            horas=fila.publicacion.horas_reconocidas or 0,
            fecha_emision=_fecha_emision(fila),
            codigo=codigo,
        )
        corto = str(fila.postulacion.id).split("-")[0]
        return generar_pdf(datos), f"certificado-solari-{corto}.pdf"

    async def verificar(self, postulacion: str, codigo: str) -> VerificacionCertificadoOut:
        invalido = VerificacionCertificadoOut(valido=False)
        try:
            postulacion_id = uuid.UUID(postulacion)
        except ValueError:
            return invalido
        if not codigo_es_valido(self.settings.jwt_secret, postulacion_id, codigo):
            return invalido
        fila = await self.repo.datos_postulacion(postulacion_id)
        if fila is None or not _certificable(fila):
            return invalido
        return VerificacionCertificadoOut(
            valido=True,
            voluntario=nombre_publico(fila.usuario.nombre),
            actividad=fila.publicacion.titulo,
            organizacion=fila.fundacion.nombre,
            horas=fila.publicacion.horas_reconocidas or 0,
            fecha=_fecha_emision(fila),
        )
