"""Objetos y servicios voluntarios (ofrecimientos gratuitos).

Regla R1: son siempre gratuitos. No existe ningún campo de precio ni de pago.
Regla R9: la entrega o el servicio se completa solo si ambas partes confirman.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TIPO_OBJETO = "OBJETO"
TIPO_SERVICIO = "SERVICIO"
TIPOS_OFRECIMIENTO = (TIPO_OBJETO, TIPO_SERVICIO)

# Ciclo de vida de la publicación.
OF_DISPONIBLE = "DISPONIBLE"
OF_RESERVADO = "RESERVADO"
OF_ENTREGADO = "ENTREGADO"
OF_SERVICIO_COMPLETADO = "SERVICIO_COMPLETADO"
OF_AGOTADO = "AGOTADO"
OF_PAUSADO = "PAUSADO"
OF_FINALIZADO = "FINALIZADO"
ESTADOS_OFRECIMIENTO = (
    OF_DISPONIBLE, OF_RESERVADO, OF_ENTREGADO, OF_SERVICIO_COMPLETADO,
    OF_AGOTADO, OF_PAUSADO, OF_FINALIZADO,
)

# Ciclo de vida de la solicitud de interés.
SI_PENDIENTE = "PENDIENTE"
SI_ACEPTADA = "ACEPTADA"
SI_EN_COORDINACION = "EN_COORDINACION"
SI_COMPLETADA = "COMPLETADA"
SI_RECHAZADA = "RECHAZADA"
SI_CANCELADA = "CANCELADA"
SI_ACTIVAS = (SI_PENDIENTE, SI_ACEPTADA, SI_EN_COORDINACION)
SI_RESERVAN_CANTIDAD = (SI_ACEPTADA, SI_EN_COORDINACION, SI_COMPLETADA)

CATEGORIAS_OBJETO = (
    "Alimentos", "Alimento para animales", "Libros y material educativo",
    "Ropa y calzado", "Herramientas", "Higiene y salud", "Muebles y hogar",
    "Tecnología", "Juguetes", "Otros",
)
CATEGORIAS_SERVICIO = (
    "Pintura", "Electricidad", "Plomería y construcción", "Diseño gráfico",
    "Tutorías y enseñanza", "Asesoría legal o contable", "Veterinaria",
    "Salud y bienestar", "Tecnología y soporte", "Comunicación y fotografía", "Otros",
)
ESTADOS_PRODUCTO = ("NUEVO", "COMO_NUEVO", "USADO_BUEN_ESTADO", "USADO")
MODALIDADES_ENTREGA = ("RECOGER_EN_LUGAR", "ENTREGA_POR_VOLUNTARIO", "A_CONVENIR")
MODALIDADES_SERVICIO = ("PRESENCIAL", "REMOTO")

ofrecimiento_habilidades = Table(
    "ofrecimiento_habilidades",
    Base.metadata,
    Column(
        "ofrecimiento_id",
        UUID(as_uuid=True),
        ForeignKey("ofrecimientos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "habilidad_id",
        Integer,
        ForeignKey("habilidades.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Ofrecimiento(Base):
    __tablename__ = "ofrecimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(60))
    cantidad_total: Mapped[int] = mapped_column(Integer, default=1)
    cantidad_disponible: Mapped[int] = mapped_column(Integer, default=1)
    estado_producto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    modalidad_entrega: Mapped[str | None] = mapped_column(String(30), nullable=True)
    municipio_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("municipios.id", ondelete="SET NULL"), nullable=True
    )
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    disponibilidad: Mapped[str | None] = mapped_column(Text, nullable=True)
    alcance: Mapped[str | None] = mapped_column(Text, nullable=True)
    condiciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagenes: Mapped[list] = mapped_column(JSONB, default=list)
    estado: Mapped[str] = mapped_column(String(30), default=OF_DISPONIBLE)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class SolicitudInteres(Base):
    __tablename__ = "solicitudes_interes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ofrecimiento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ofrecimientos.id", ondelete="CASCADE")
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default=SI_PENDIENTE)
    confirmada_voluntario: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmada_fundacion: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
    fecha_completada: Mapped[datetime | None] = mapped_column(nullable=True)


class MensajeInteres(Base):
    """Canal básico de mensajería asociado a una solicitud de interés."""

    __tablename__ = "mensajes_interes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("solicitudes_interes.id", ondelete="CASCADE")
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    mensaje: Mapped[str] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
