"""Actividades recurrentes con autorización explícita cada tres convocatorias (R4)."""

from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.fundacion import Fundacion
from app.models.habilidades import MAX_HABILIDADES, MIN_HABILIDADES
from app.models.notificacion import TIPO_PROGRAMACION_PAUSADA
from app.models.programacion import (
    MAX_POR_CICLO,
    PROG_ACTIVA,
    PROG_PAUSADA,
    PROG_TERMINADA,
    UNIDAD_DIAS,
    UNIDAD_SEMANAS,
    ProgramacionRecurrente,
)
from app.models.publicacion import ESTADO_PUBLICADA, Publicacion
from app.repositories.publicacion_repo import PublicacionRepository
from app.schemas.programacion import (
    ConvocatoriaGenerada,
    ProgramacionCreate,
    ProgramacionOut,
)
from app.schemas.publicacion import PublicacionCreate
from app.services.habilidad_service import HabilidadService
from app.services.notificacion_service import NotificacionService

# Campos que calcula la programación; no se aceptan en la plantilla.
_CAMPOS_CALCULADOS = (
    "fecha_inicio", "fecha_fin", "hora_inicio", "hora_fin",
    "cupo_maximo", "fecha_limite_postulacion",
)


def _now() -> datetime:
    return datetime.now(UTC)


def sumar_meses(d: date, meses: int) -> date:
    mes = d.month - 1 + meses
    anio = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def siguiente_fecha(d: date, unidad: str, intervalo: int) -> date:
    """Fecha de la siguiente ocurrencia según la frecuencia configurada."""
    if unidad == UNIDAD_DIAS:
        return d + timedelta(days=intervalo)
    if unidad == UNIDAD_SEMANAS:
        return d + timedelta(weeks=intervalo)
    return sumar_meses(d, intervalo)


class ProgramacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pub_repo = PublicacionRepository(db)
        self.notif = NotificacionService(db)

    # ─────────────── Generación ───────────────

    def _publicacion_de(self, prog: ProgramacionRecurrente, inicio: date) -> PublicacionCreate:
        fin = inicio + timedelta(days=prog.duracion_dias - 1)
        try:
            return PublicacionCreate(
                **prog.plantilla,
                fecha_inicio=inicio,
                fecha_fin=fin,
                hora_inicio=prog.hora_inicio,
                hora_fin=prog.hora_fin,
                cupo_maximo=prog.cupo_maximo,
            )
        except ValidationError as exc:
            primero = exc.errors()[0]
            raise AppError(f"Plantilla no válida: {primero.get('msg', 'dato inválido')}", 422) from exc

    async def _generar_ciclo(self, prog: ProgramacionRecurrente, fundacion: Fundacion) -> None:
        """Genera hasta tres convocatorias consecutivas y deja la programación PAUSADA."""
        primera = prog.proxima_fecha
        ultima = primera
        for _ in range(MAX_POR_CICLO):
            inicio = prog.proxima_fecha
            data = self._publicacion_de(prog, inicio)
            payload = data.model_dump(exclude={"habilidades"})
            payload.update(
                fundacion_id=fundacion.id,
                estado=ESTADO_PUBLICADA,
                fecha_publicacion=_now(),
                programacion_id=prog.id,
            )
            await self.pub_repo.crear(payload, data.habilidades)
            ultima = inicio
            prog.proxima_fecha = siguiente_fecha(inicio, prog.unidad_intervalo, prog.intervalo)

        prog.total_generadas += MAX_POR_CICLO
        prog.ciclo_generadas = MAX_POR_CICLO
        # Se pausa ANTES de la cuarta: continuar requiere autorización explícita.
        prog.estado = PROG_PAUSADA
        prog.fecha_pausa = _now()
        prog.fecha_actualizacion = _now()
        await self.db.flush()
        await self.notif.notificar(
            fundacion.usuario_id,
            TIPO_PROGRAMACION_PAUSADA,
            (
                f"Tu programación «{prog.titulo}» generó {MAX_POR_CICLO} convocatorias "
                f"({primera:%d/%m/%Y} a {ultima:%d/%m/%Y}) y quedó en pausa. Autoriza "
                f"continuar para generar las siguientes; si no respondes, permanecerá pausada."
            ),
            "programacion",
            prog.id,
        )

    # ─────────────── Casos de uso ───────────────

    async def crear(self, fundacion: Fundacion, data: ProgramacionCreate) -> ProgramacionOut:
        if data.fecha_inicio < date.today():
            raise AppError("La fecha de inicio no puede ser anterior a hoy.", 422)
        plantilla = {k: v for k, v in data.plantilla.items() if k not in _CAMPOS_CALCULADOS}
        habilidades = plantilla.get("habilidades") or []
        await HabilidadService(self.db).validar_ids(
            habilidades, minimo=MIN_HABILIDADES, maximo=MAX_HABILIDADES, sujeto="La actividad"
        )
        titulo = str(plantilla.get("titulo") or "").strip()
        if len(titulo) < 3:
            raise AppError("La plantilla debe incluir un título de al menos 3 caracteres.", 422)

        prog = ProgramacionRecurrente(
            id=uuid.uuid4(),
            fundacion_id=fundacion.id,
            titulo=titulo[:200],
            plantilla=plantilla,
            unidad_intervalo=data.unidad_intervalo,
            intervalo=data.intervalo,
            fecha_inicio=data.fecha_inicio,
            duracion_dias=data.duracion_dias,
            hora_inicio=data.hora_inicio,
            hora_fin=data.hora_fin,
            cupo_maximo=data.cupo_maximo,
            estado=PROG_ACTIVA,
            proxima_fecha=data.fecha_inicio,
        )
        # Valida la plantilla completa antes de persistir nada.
        self._publicacion_de(prog, data.fecha_inicio)
        self.db.add(prog)
        await self.db.flush()
        await self._generar_ciclo(prog, fundacion)
        salida = await self._salida(prog)
        await self.db.commit()
        return salida

    async def _de_fundacion(
        self, programacion_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> ProgramacionRecurrente:
        prog = await self.db.get(ProgramacionRecurrente, programacion_id)
        if prog is None or prog.fundacion_id != fundacion_id:
            raise NotFoundError("Programación no encontrada.")
        return prog

    async def autorizar(
        self, programacion_id: uuid.UUID, fundacion: Fundacion
    ) -> ProgramacionOut:
        prog = await self._de_fundacion(programacion_id, fundacion.id)
        if prog.estado != PROG_PAUSADA:
            raise ConflictError("Solo se puede autorizar una programación en pausa.")
        # Si pasó tiempo en pausa, no se generan convocatorias en fechas ya vencidas.
        hoy = date.today()
        while prog.proxima_fecha < hoy:
            prog.proxima_fecha = siguiente_fecha(
                prog.proxima_fecha, prog.unidad_intervalo, prog.intervalo
            )
        prog.estado = PROG_ACTIVA
        await self._generar_ciclo(prog, fundacion)
        salida = await self._salida(prog)
        await self.db.commit()
        return salida

    async def finalizar(
        self, programacion_id: uuid.UUID, fundacion: Fundacion
    ) -> ProgramacionOut:
        prog = await self._de_fundacion(programacion_id, fundacion.id)
        if prog.estado == PROG_TERMINADA:
            raise ConflictError("La programación ya terminó.")
        prog.estado = PROG_TERMINADA
        prog.fecha_actualizacion = _now()
        salida = await self._salida(prog)
        await self.db.commit()
        return salida

    async def listar(self, fundacion_id: uuid.UUID) -> list[ProgramacionOut]:
        stmt = (
            select(ProgramacionRecurrente)
            .where(ProgramacionRecurrente.fundacion_id == fundacion_id)
            .order_by(ProgramacionRecurrente.fecha_creacion.desc())
        )
        progs = list((await self.db.execute(stmt)).scalars().all())
        return [await self._salida(p) for p in progs]

    async def _salida(self, prog: ProgramacionRecurrente) -> ProgramacionOut:
        pubs = (
            await self.db.execute(
                select(Publicacion)
                .where(Publicacion.programacion_id == prog.id)
                .order_by(Publicacion.fecha_inicio)
            )
        ).scalars().all()
        out = ProgramacionOut.model_validate(prog)
        out.convocatorias = [ConvocatoriaGenerada.model_validate(p) for p in pubs]
        return out
