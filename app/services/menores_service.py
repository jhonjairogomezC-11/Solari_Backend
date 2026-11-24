"""Autorización del acudiente para voluntarios menores de edad.

Edad mínima en Solari: 16 años (ver app/core/edad.py). Por eso aquí solo aplica a
voluntarios de 16 y 17 años.

Marco legal (Colombia): las personas menores de 18 años necesitan la autorización
de sus padres o representante legal (Código de Infancia y Adolescencia, Ley 1098
de 2006) y el tratamiento de sus datos exige la del representante (Ley 1581 de
2012, art. 7).

Reglas:
- La edad se calcula con la fecha actual de Bogotá (UTC-5, sin horario de verano).
- Un menor puede postularse, pero la organización no puede ACEPTARLO hasta que un
  administrador apruebe la autorización firmada por su acudiente.
- El archivo firmado se guarda en almacenamiento PRIVADO (solo el dueño y admin).
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, date, datetime, timedelta, timezone

from fastapi import UploadFile
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.edad import (  # noqa: F401  (re-exportados para quien los importe desde aquí)
    EDAD_MINIMA,
    MAYORIA_EDAD,
    calcular_edad,
    hoy_bogota,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.notificacion import TIPO_CUENTA_ACTUALIZADA
from app.models.usuario import Usuario
from app.models.voluntario import Voluntario
from app.schemas.menores import (
    AcudienteInput,
    AdminAutorizacionesPage,
    AdminAutorizacionOut,
    AutorizacionOut,
    ResolverAutorizacionInput,
)
from app.services.auditoria_service import AuditoriaService
from app.services.notificacion_service import NotificacionService
from app.services.storage_service import StorageService

AUT_NO_REQUERIDA = "NO_REQUERIDA"
AUT_PENDIENTE = "PENDIENTE"
AUT_APROBADA = "APROBADA"
AUT_RECHAZADA = "RECHAZADA"
ESTADOS_AUTORIZACION = (AUT_NO_REQUERIDA, AUT_PENDIENTE, AUT_APROBADA, AUT_RECHAZADA)

MSG_MENOR_SIN_AUTORIZACION = (
    "El voluntario es menor de edad y aún no tiene la autorización de su acudiente aprobada."
)

_TZ_BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")

_PARENTESCO_TEXTO = {
    "MADRE": "Madre",
    "PADRE": "Padre",
    "TUTOR_LEGAL": "Tutor(a) o representante legal",
    "OTRO": "Otro representante legal",
}
_TIPOS_DOCUMENTO = {
    "CC": "cédula de ciudadanía",
    "TI": "tarjeta de identidad",
    "CE": "cédula de extranjería",
    "PASAPORTE": "pasaporte",
}


# ─────────────── Reglas puras (sin base de datos) ───────────────


def es_menor(nacimiento: date | None, hoy: date | None = None) -> bool:
    if nacimiento is None:
        return False
    return calcular_edad(nacimiento, hoy) < MAYORIA_EDAD


def estado_autorizacion(
    nacimiento: date | None, estado: str | None, hoy: date | None = None
) -> str | None:
    """Estado efectivo: NO_REQUERIDA si es mayor; None si el menor aún no la envía."""
    if not es_menor(nacimiento, hoy):
        return AUT_NO_REQUERIDA
    if estado in (AUT_PENDIENTE, AUT_APROBADA, AUT_RECHAZADA):
        return estado
    return None


def puede_ser_aceptado(
    nacimiento: date | None, estado: str | None, hoy: date | None = None
) -> bool:
    return not es_menor(nacimiento, hoy) or estado == AUT_APROBADA


def validar_aceptacion_menor(
    nacimiento: date | None, estado: str | None, hoy: date | None = None
) -> None:
    """Lanza ConflictError si se intenta aceptar a un menor sin autorización aprobada."""
    if not puede_ser_aceptado(nacimiento, estado, hoy):
        raise ConflictError(MSG_MENOR_SIN_AUTORIZACION)


# ─────────────── Formato PDF ───────────────


def _latin1(texto: str) -> str:
    return texto.encode("latin-1", "replace").decode("latin-1")


def _fecha_larga(d: date) -> str:
    meses = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
        "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def generar_formato_pdf(
    *,
    nombre: str,
    tipo_documento: str,
    numero_documento: str,
    fecha_nacimiento: date,
    acudiente_nombre: str | None = None,
    acudiente_documento: str | None = None,
    acudiente_telefono: str | None = None,
    acudiente_parentesco: str | None = None,
    hoy: date | None = None,
) -> bytes:
    """Formato de autorización con los datos del menor y espacios para la firma."""
    hoy = hoy or hoy_bogota()
    linea = "_" * 38
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_title(_latin1("Autorización del acudiente - Solari"))
    pdf.set_author("Solari")
    pdf.set_creator("Solari")
    pdf.add_page()
    ancho = pdf.w - 40

    def parrafo(texto: str, size: int = 10, estilo: str = "", alto: float = 5.2) -> None:
        pdf.set_font("helvetica", style=estilo, size=size)
        pdf.multi_cell(ancho, alto, _latin1(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def campo(etiqueta: str, valor: str | None) -> None:
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(62, 8, _latin1(etiqueta))
        pdf.set_font("helvetica", size=10)
        pdf.cell(ancho - 62, 8, _latin1(valor or linea), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("helvetica", style="B", size=18)
    pdf.set_text_color(234, 88, 12)
    pdf.cell(ancho, 9, "Solari", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(30, 30, 30)
    parrafo("Autorización del acudiente para la participación de un menor de edad "
            "en actividades de voluntariado", size=13, estilo="B", alto=6.5)
    pdf.ln(3)

    parrafo("1. Datos del menor de edad", size=11, estilo="B")
    campo("Nombre completo:", nombre)
    campo("Documento:", f"{_TIPOS_DOCUMENTO.get(tipo_documento, tipo_documento)} n.º {numero_documento}")
    campo("Fecha de nacimiento:", _fecha_larga(fecha_nacimiento))
    campo("Edad:", f"{calcular_edad(fecha_nacimiento, hoy)} años")
    pdf.ln(2)

    parrafo("2. Datos del acudiente (madre, padre o representante legal)", size=11, estilo="B")
    campo("Nombre completo:", acudiente_nombre)
    campo("Documento de identidad:", acudiente_documento)
    campo("Parentesco:", _PARENTESCO_TEXTO.get(acudiente_parentesco or "", None))
    campo("Teléfono:", acudiente_telefono)
    pdf.ln(2)

    parrafo("3. Autorización", size=11, estilo="B")
    parrafo(
        "Yo, el acudiente identificado arriba, en ejercicio de la patria potestad o de la "
        "representación legal del menor, declaro que:"
    )
    for punto in (
        "a) Autorizo al menor a registrarse en la plataforma Solari y a participar en las "
        "actividades de voluntariado que elija, siempre que la organización las acepte y sean "
        "adecuadas para su edad.",
        "b) Conozco que cada organización es responsable de las condiciones de seguridad y "
        "supervisión de sus actividades, y que puedo revocar esta autorización en cualquier "
        "momento.",
        "c) Autorizo el tratamiento de los datos personales del menor y de los míos para "
        "gestionar su participación, conforme a la Ley 1581 de 2012 y la política de "
        "tratamiento de datos de Solari, respetando el interés superior del menor (Ley 1098 "
        "de 2006). Sé que puedo conocer, actualizar, rectificar y suprimir estos datos.",
    ):
        parrafo(punto)
        pdf.ln(1)
    pdf.ln(6)

    y = pdf.get_y()
    mitad = ancho / 2
    pdf.set_font("helvetica", size=10)
    pdf.line(20, y + 12, 20 + mitad - 8, y + 12)
    pdf.line(20 + mitad + 8, y + 12, 20 + ancho, y + 12)
    pdf.set_xy(20, y + 13)
    pdf.cell(mitad - 8, 5, "Firma del acudiente")
    pdf.set_xy(20 + mitad + 8, y + 13)
    pdf.cell(mitad - 8, 5, "Firma del menor (opcional)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    campo("Ciudad y fecha:", None)
    pdf.ln(4)
    pdf.set_text_color(110, 110, 110)
    parrafo(
        f"Formato generado por Solari el {_fecha_larga(hoy)}. Imprímelo, pide a tu acudiente "
        "que lo firme y súbelo escaneado o en foto desde tu perfil, junto con una copia de su "
        "documento si es posible. Un administrador lo revisará.",
        size=8, alto=4,
    )
    return bytes(pdf.output())


# ─────────────── Servicio ───────────────


def _now() -> datetime:
    return datetime.now(UTC)


class MenoresService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageService(get_settings())

    # ── Voluntario ──

    @staticmethod
    def resumen(vol: Voluntario) -> AutorizacionOut:
        menor = es_menor(vol.fecha_nacimiento)
        return AutorizacionOut(
            es_menor=menor,
            edad=calcular_edad(vol.fecha_nacimiento),
            requerida=menor,
            estado=estado_autorizacion(vol.fecha_nacimiento, vol.autorizacion_estado),
            acudiente_nombre=vol.acudiente_nombre,
            acudiente_documento=vol.acudiente_documento,
            acudiente_telefono=vol.acudiente_telefono,
            acudiente_parentesco=vol.acudiente_parentesco,
            archivo=vol.autorizacion_acudiente,
            fecha=vol.autorizacion_fecha,
            nota=vol.autorizacion_nota,
        )

    @staticmethod
    def _exigir_menor(vol: Voluntario) -> None:
        if not es_menor(vol.fecha_nacimiento):
            raise ConflictError("Eres mayor de edad: no necesitas la autorización de un acudiente.")

    async def guardar_acudiente(self, vol: Voluntario, data: AcudienteInput) -> AutorizacionOut:
        self._exigir_menor(vol)
        if data.acudiente_documento == (vol.numero_documento or "").upper():
            raise ConflictError("El documento del acudiente no puede ser el mismo del voluntario.")
        cambia_persona = (
            vol.acudiente_nombre is not None
            and (
                data.acudiente_nombre.casefold() != vol.acudiente_nombre.casefold()
                or data.acudiente_documento != vol.acudiente_documento
            )
        )
        vol.acudiente_nombre = data.acudiente_nombre
        vol.acudiente_documento = data.acudiente_documento
        vol.acudiente_telefono = data.acudiente_telefono
        vol.acudiente_parentesco = data.acudiente_parentesco
        # Una autorización firmada por otra persona deja de ser válida.
        if cambia_persona and vol.autorizacion_estado in (AUT_PENDIENTE, AUT_APROBADA):
            self.storage.eliminar_privado(vol.autorizacion_acudiente)
            vol.autorizacion_acudiente = None
            vol.autorizacion_estado = None
            vol.autorizacion_fecha = _now()
            vol.autorizacion_nota = (
                "Cambiaste los datos del acudiente: sube una nueva autorización firmada."
            )
        await self.db.commit()
        await self.db.refresh(vol)
        return self.resumen(vol)

    async def subir_autorizacion(self, vol: Voluntario, file: UploadFile) -> AutorizacionOut:
        self._exigir_menor(vol)
        if not (vol.acudiente_nombre and vol.acudiente_documento and vol.acudiente_telefono):
            raise ConflictError("Primero guarda los datos de tu acudiente.")
        if vol.autorizacion_estado == AUT_APROBADA:
            raise ConflictError("Tu autorización ya fue aprobada; no necesitas subirla de nuevo.")
        anterior = vol.autorizacion_acudiente
        vol.autorizacion_acudiente = await self.storage.guardar_documento(file, "documentos")
        vol.autorizacion_estado = AUT_PENDIENTE
        vol.autorizacion_fecha = _now()
        vol.autorizacion_nota = None
        await self.db.commit()
        self.storage.eliminar_privado(anterior)
        await self.db.refresh(vol)
        return self.resumen(vol)

    async def formato_pdf(self, vol: Voluntario) -> bytes:
        self._exigir_menor(vol)
        nombre = (await self.db.get(Usuario, vol.usuario_id)).nombre
        return generar_formato_pdf(
            nombre=nombre,
            tipo_documento=vol.tipo_documento,
            numero_documento=vol.numero_documento,
            fecha_nacimiento=vol.fecha_nacimiento,
            acudiente_nombre=vol.acudiente_nombre,
            acudiente_documento=vol.acudiente_documento,
            acudiente_telefono=vol.acudiente_telefono,
            acudiente_parentesco=vol.acudiente_parentesco,
        )

    # ── Administración ──

    async def listar(
        self, estado: str | None, page: int, per_page: int
    ) -> AdminAutorizacionesPage:
        condiciones = [Voluntario.autorizacion_acudiente.is_not(None)]
        if estado:
            condiciones.append(Voluntario.autorizacion_estado == estado)
        total = (
            await self.db.execute(
                select(func.count()).select_from(Voluntario).where(*condiciones)
            )
        ).scalar_one()
        filas = (
            await self.db.execute(
                select(Voluntario, Usuario.nombre, Usuario.email)
                .join(Usuario, Usuario.id == Voluntario.usuario_id)
                .where(*condiciones)
                .order_by(Voluntario.autorizacion_fecha.asc().nulls_last())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        ).all()
        data = [
            AdminAutorizacionOut(
                voluntario_id=v.id,
                usuario_id=v.usuario_id,
                nombre=nombre,
                email=email,
                edad=calcular_edad(v.fecha_nacimiento),
                fecha_nacimiento=v.fecha_nacimiento,
                tipo_documento=v.tipo_documento,
                numero_documento=v.numero_documento,
                acudiente_nombre=v.acudiente_nombre,
                acudiente_documento=v.acudiente_documento,
                acudiente_telefono=v.acudiente_telefono,
                acudiente_parentesco=v.acudiente_parentesco,
                archivo=v.autorizacion_acudiente,
                estado=v.autorizacion_estado,
                fecha=v.autorizacion_fecha,
                nota=v.autorizacion_nota,
            )
            for v, nombre, email in filas
        ]
        return AdminAutorizacionesPage(
            data=data, total=total, page=page, per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    async def resolver(
        self, admin: Usuario, voluntario_id: uuid.UUID, data: ResolverAutorizacionInput
    ) -> AutorizacionOut:
        vol = (
            await self.db.execute(
                select(Voluntario).where(Voluntario.id == voluntario_id).with_for_update()
            )
        ).scalar_one_or_none()
        if vol is None:
            raise NotFoundError("Voluntario no encontrado.")
        if vol.autorizacion_estado != AUT_PENDIENTE or not vol.autorizacion_acudiente:
            raise ConflictError("Esta autorización no está pendiente de revisión.")
        nombre = (await self.db.get(Usuario, vol.usuario_id)).nombre

        anterior = vol.autorizacion_estado
        vol.autorizacion_estado = data.decision
        vol.autorizacion_nota = data.nota
        vol.autorizacion_fecha = _now()
        await AuditoriaService(self.db).registrar(
            admin.id, "AUTORIZACION_MENOR_RESUELTA", objeto_tipo="voluntario",
            objeto_id=vol.id, descripcion=f"Autorización del acudiente de {nombre}",
            anterior={"estado": anterior}, nuevo={"estado": data.decision}, motivo=data.nota,
        )
        if data.decision == AUT_APROBADA:
            mensaje = (
                "Aprobamos la autorización de tu acudiente. Ya puedes ser aceptado en "
                "convocatorias de voluntariado."
            )
        else:
            mensaje = (
                "La autorización de tu acudiente no fue aprobada. Revisa la nota en tu perfil "
                f"y súbela de nuevo. Motivo: {data.nota}"
            )
        await NotificacionService(self.db).notificar(
            vol.usuario_id, TIPO_CUENTA_ACTUALIZADA, mensaje, "voluntario", vol.id
        )
        await self.db.commit()
        await self.db.refresh(vol)
        return self.resumen(vol)
