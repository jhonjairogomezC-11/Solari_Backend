"""Objetos y servicios voluntarios: publicación gratuita, solicitudes de interés y
mensajería básica.

Reglas del documento de grado:
- R1: son gratuitos; la plataforma no procesa pagos ni compraventa.
- R9: la entrega o el servicio se completa solo cuando AMBAS partes lo confirman.
- Control de cantidades: si se ofrecen cinco libros y una organización pide tres y
  otra dos, ambas se atienden sin exceder las cinco unidades (bloqueo de fila).
- La mensajería no expone datos personales: se muestran solo primer nombre y nombre
  de la organización, y se rechazan mensajes con correos, teléfonos o enlaces.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, date, datetime

from fastapi import UploadFile
from sqlalchemy import func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models.catalogo import Habilidad, Municipio
from app.models.fundacion import Fundacion
from app.models.notificacion import (
    TIPO_INTERES_ACTUALIZADO,
    TIPO_INTERES_RECIBIDO,
    TIPO_NUEVO_MENSAJE,
    Notificacion,
)
from app.models.ofrecimiento import (
    OF_AGOTADO,
    OF_DISPONIBLE,
    OF_ENTREGADO,
    OF_FINALIZADO,
    OF_PAUSADO,
    OF_RESERVADO,
    OF_SERVICIO_COMPLETADO,
    SI_ACEPTADA,
    SI_ACTIVAS,
    SI_CANCELADA,
    SI_COMPLETADA,
    SI_EN_COORDINACION,
    SI_PENDIENTE,
    SI_RECHAZADA,
    SI_RESERVAN_CANTIDAD,
    TIPO_SERVICIO,
    MensajeInteres,
    Ofrecimiento,
    SolicitudInteres,
    ofrecimiento_habilidades,
)
from app.models.usuario import ROL_FUNDACION, ROL_VOLUNTARIO, Usuario
from app.models.voluntario import Voluntario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.catalogo import HabilidadOut
from app.schemas.ofrecimiento import (
    CategoriasOfrecimiento,
    MensajeInput,
    MensajeOut,
    OfrecimientoCreate,
    OfrecimientoOut,
    OfrecimientoPage,
    OfrecimientoUpdate,
    SolicitudInteresCreate,
    SolicitudInteresOut,
)
from app.services.coincidencia import contiene_datos_personales
from app.services.habilidad_service import HabilidadService
from app.services.notificacion_service import NotificacionService
from app.services.storage_service import StorageService

MAX_IMAGENES = 5


def _now() -> datetime:
    return datetime.now(UTC)


def primer_nombre(nombre: str) -> str:
    return nombre.strip().split(" ")[0] if nombre.strip() else "Voluntario"


class OfrecimientoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notif = NotificacionService(db)
        self.storage = StorageService(get_settings())

    # ─────────────── Catálogos ───────────────

    @staticmethod
    def categorias() -> CategoriasOfrecimiento:
        from app.models.ofrecimiento import (
            CATEGORIAS_OBJETO,
            CATEGORIAS_SERVICIO,
            ESTADOS_PRODUCTO,
            MODALIDADES_ENTREGA,
            MODALIDADES_SERVICIO,
        )

        return CategoriasOfrecimiento(
            objetos=list(CATEGORIAS_OBJETO),
            servicios=list(CATEGORIAS_SERVICIO),
            estados_producto=list(ESTADOS_PRODUCTO),
            modalidades_entrega=list(MODALIDADES_ENTREGA),
            modalidades_servicio=list(MODALIDADES_SERVICIO),
        )

    # ─────────────── Serialización ───────────────

    async def _salida(
        self,
        ofs: list[Ofrecimiento],
        *,
        voluntario_id: uuid.UUID | None = None,
        fundacion_id: uuid.UUID | None = None,
    ) -> list[OfrecimientoOut]:
        if not ofs:
            return []
        ids = [o.id for o in ofs]
        solicitados: set[uuid.UUID] = set()
        if fundacion_id is not None:
            solicitados = set(
                (
                    await self.db.execute(
                        select(SolicitudInteres.ofrecimiento_id).where(
                            SolicitudInteres.ofrecimiento_id.in_(ids),
                            SolicitudInteres.fundacion_id == fundacion_id,
                            SolicitudInteres.estado.in_(SI_ACTIVAS),
                        )
                    )
                )
                .scalars()
                .all()
            )
        nombres = {
            vid: nombre
            for vid, nombre in (
                await self.db.execute(
                    select(Voluntario.id, Usuario.nombre)
                    .join(Usuario, Usuario.id == Voluntario.usuario_id)
                    .where(Voluntario.id.in_({o.voluntario_id for o in ofs}))
                )
            ).all()
        }
        municipios = {
            m_id: nombre
            for m_id, nombre in (
                await self.db.execute(
                    select(Municipio.id, Municipio.nombre).where(
                        Municipio.id.in_({o.municipio_id for o in ofs if o.municipio_id})
                    )
                )
            ).all()
        }
        habs: dict[uuid.UUID, list[Habilidad]] = {}
        for oid, h in (
            await self.db.execute(
                select(ofrecimiento_habilidades.c.ofrecimiento_id, Habilidad)
                .join(Habilidad, Habilidad.id == ofrecimiento_habilidades.c.habilidad_id)
                .where(ofrecimiento_habilidades.c.ofrecimiento_id.in_(ids))
            )
        ).all():
            habs.setdefault(oid, []).append(h)
        pendientes: dict[uuid.UUID, int] = {}
        if voluntario_id is not None:
            pendientes = dict(
                (
                    await self.db.execute(
                        select(SolicitudInteres.ofrecimiento_id, func.count())
                        .where(
                            SolicitudInteres.ofrecimiento_id.in_(ids),
                            SolicitudInteres.estado == SI_PENDIENTE,
                        )
                        .group_by(SolicitudInteres.ofrecimiento_id)
                    )
                ).all()
            )

        salida: list[OfrecimientoOut] = []
        for o in ofs:
            out = OfrecimientoOut.model_validate(o)
            out.municipio = municipios.get(o.municipio_id) if o.municipio_id else None
            out.voluntario_nombre = primer_nombre(nombres.get(o.voluntario_id, ""))
            out.habilidades = [HabilidadOut.model_validate(h) for h in habs.get(o.id, [])]
            out.es_mio = voluntario_id is not None and o.voluntario_id == voluntario_id
            out.ya_solicitado = o.id in solicitados
            if out.es_mio:
                out.solicitudes_pendientes = pendientes.get(o.id, 0)
            salida.append(out)
        return salida

    # ─────────────── Voluntario: gestión de sus publicaciones ───────────────

    async def crear(self, voluntario: Voluntario, data: OfrecimientoCreate) -> OfrecimientoOut:
        if data.habilidades:
            await HabilidadService(self.db).validar_ids(
                data.habilidades, minimo=1, maximo=10, sujeto="El servicio"
            )
        of = Ofrecimiento(
            id=uuid.uuid4(),
            voluntario_id=voluntario.id,
            tipo=data.tipo,
            titulo=data.titulo,
            descripcion=data.descripcion,
            categoria=data.categoria,
            cantidad_total=data.cantidad_total,
            cantidad_disponible=data.cantidad_total,
            estado_producto=data.estado_producto,
            modalidad_entrega=data.modalidad_entrega,
            municipio_id=data.municipio_id,
            fecha_vencimiento=data.fecha_vencimiento,
            disponibilidad=data.disponibilidad,
            alcance=data.alcance,
            condiciones=data.condiciones,
            imagenes=[],
            estado=OF_DISPONIBLE,
        )
        self.db.add(of)
        await self.db.flush()
        for hid in dict.fromkeys(data.habilidades):
            await self.db.execute(
                insert(ofrecimiento_habilidades).values(ofrecimiento_id=of.id, habilidad_id=hid)
            )
        salida = (await self._salida([of], voluntario_id=voluntario.id))[0]
        await self.db.commit()
        return salida

    async def _propio(self, voluntario: Voluntario, ofrecimiento_id: uuid.UUID) -> Ofrecimiento:
        stmt = (
            select(Ofrecimiento)
            .where(Ofrecimiento.id == ofrecimiento_id)
            .with_for_update()
        )
        of = (await self.db.execute(stmt)).scalar_one_or_none()
        if of is None or of.voluntario_id != voluntario.id:
            raise NotFoundError("Publicación no encontrada.")
        return of

    async def _recalcular_estado(self, of: Ofrecimiento) -> None:
        """Deriva el estado de la publicación a partir de sus solicitudes."""
        if of.estado in (OF_PAUSADO, OF_FINALIZADO):
            return
        filas = (
            await self.db.execute(
                select(SolicitudInteres.estado, func.coalesce(func.sum(SolicitudInteres.cantidad), 0))
                .where(SolicitudInteres.ofrecimiento_id == of.id)
                .group_by(SolicitudInteres.estado)
            )
        ).all()
        por_estado = {e: int(c) for e, c in filas}
        completadas = por_estado.get(SI_COMPLETADA, 0)
        activas = por_estado.get(SI_ACEPTADA, 0) + por_estado.get(SI_EN_COORDINACION, 0)
        if of.tipo == TIPO_SERVICIO:
            if completadas > 0:
                of.estado = OF_SERVICIO_COMPLETADO
            elif activas > 0:
                of.estado = OF_RESERVADO
            else:
                of.estado = OF_DISPONIBLE
        elif of.cantidad_disponible > 0:
            of.estado = OF_DISPONIBLE
        elif activas > 0:
            of.estado = OF_RESERVADO
        elif completadas >= of.cantidad_total:
            of.estado = OF_ENTREGADO
        else:
            of.estado = OF_AGOTADO
        of.fecha_actualizacion = _now()

    async def actualizar(
        self, voluntario: Voluntario, ofrecimiento_id: uuid.UUID, data: OfrecimientoUpdate
    ) -> OfrecimientoOut:
        of = await self._propio(voluntario, ofrecimiento_id)
        if of.estado == OF_FINALIZADO:
            raise ConflictError("Una publicación finalizada no se puede editar.")
        campos = data.model_dump(exclude_unset=True)
        if "cantidad_total" in campos and campos["cantidad_total"] is not None:
            if of.tipo == TIPO_SERVICIO:
                raise ConflictError("Un servicio no tiene cantidad.")
            reservada = of.cantidad_total - of.cantidad_disponible
            if campos["cantidad_total"] < reservada:
                raise ConflictError(
                    f"Ya hay {reservada} unidad(es) comprometida(s); la cantidad no puede ser menor."
                )
            of.cantidad_disponible = campos["cantidad_total"] - reservada
        for k, v in campos.items():
            setattr(of, k, v)
        await self._recalcular_estado(of)
        salida = (await self._salida([of], voluntario_id=voluntario.id))[0]
        await self.db.commit()
        return salida

    async def cambiar_estado(
        self, voluntario: Voluntario, ofrecimiento_id: uuid.UUID, accion: str
    ) -> OfrecimientoOut:
        of = await self._propio(voluntario, ofrecimiento_id)
        if of.estado == OF_FINALIZADO:
            raise ConflictError("La publicación ya está finalizada.")
        if accion == "PAUSAR":
            if of.estado != OF_DISPONIBLE:
                raise ConflictError("Solo se puede pausar una publicación disponible.")
            of.estado = OF_PAUSADO
        elif accion == "REANUDAR":
            if of.estado != OF_PAUSADO:
                raise ConflictError("La publicación no está en pausa.")
            of.estado = OF_DISPONIBLE
            await self._recalcular_estado(of)
        elif accion == "FINALIZAR":
            en_curso = (
                await self.db.execute(
                    select(func.count())
                    .select_from(SolicitudInteres)
                    .where(
                        SolicitudInteres.ofrecimiento_id == of.id,
                        SolicitudInteres.estado.in_((SI_ACEPTADA, SI_EN_COORDINACION)),
                    )
                )
            ).scalar_one()
            if en_curso:
                raise ConflictError(
                    "Hay solicitudes en curso. Complétalas o cancélalas antes de finalizar."
                )
            pendientes = (
                await self.db.execute(
                    select(SolicitudInteres).where(
                        SolicitudInteres.ofrecimiento_id == of.id,
                        SolicitudInteres.estado == SI_PENDIENTE,
                    )
                )
            ).scalars().all()
            for sol in pendientes:
                sol.estado = SI_CANCELADA
                sol.fecha_actualizacion = _now()
                fund = await self.db.get(Fundacion, sol.fundacion_id)
                if fund:
                    await self.notif.notificar(
                        fund.usuario_id, TIPO_INTERES_ACTUALIZADO,
                        f"La publicación «{of.titulo}» fue finalizada; tu solicitud se cerró.",
                        "ofrecimiento", of.id,
                    )
            of.estado = OF_FINALIZADO
        else:
            raise AppError("Acción no válida.", 422)
        of.fecha_actualizacion = _now()
        salida = (await self._salida([of], voluntario_id=voluntario.id))[0]
        await self.db.commit()
        return salida

    async def subir_imagen(
        self, voluntario: Voluntario, ofrecimiento_id: uuid.UUID, archivo: UploadFile
    ) -> OfrecimientoOut:
        of = await self._propio(voluntario, ofrecimiento_id)
        if len(of.imagenes or []) >= MAX_IMAGENES:
            raise ConflictError(f"Máximo {MAX_IMAGENES} fotografías por publicación.")
        url = await self.storage.guardar_imagen(archivo, "ofrecimientos")
        of.imagenes = [*(of.imagenes or []), url]
        of.fecha_actualizacion = _now()
        salida = (await self._salida([of], voluntario_id=voluntario.id))[0]
        await self.db.commit()
        return salida

    async def mis_ofrecimientos(self, voluntario: Voluntario) -> list[OfrecimientoOut]:
        stmt = (
            select(Ofrecimiento)
            .where(Ofrecimiento.voluntario_id == voluntario.id)
            .order_by(Ofrecimiento.fecha_creacion.desc())
        )
        ofs = list((await self.db.execute(stmt)).scalars().all())
        return await self._salida(ofs, voluntario_id=voluntario.id)

    # ─────────────── Exploración (organizaciones) ───────────────

    async def explorar(
        self,
        *,
        tipo: str | None,
        categoria: str | None,
        municipio_id: int | None,
        buscar: str | None,
        page: int,
        per_page: int,
        voluntario_id: uuid.UUID | None = None,
        fundacion_id: uuid.UUID | None = None,
    ) -> OfrecimientoPage:
        condiciones = [
            Ofrecimiento.estado == OF_DISPONIBLE,
            or_(Ofrecimiento.fecha_vencimiento.is_(None), Ofrecimiento.fecha_vencimiento >= date.today()),
        ]
        if tipo:
            condiciones.append(Ofrecimiento.tipo == tipo)
        if categoria:
            condiciones.append(Ofrecimiento.categoria == categoria)
        if municipio_id:
            condiciones.append(Ofrecimiento.municipio_id == municipio_id)
        if buscar:
            termino = f"%{buscar}%"
            condiciones.append(
                or_(Ofrecimiento.titulo.ilike(termino), Ofrecimiento.descripcion.ilike(termino))
            )
        total = (
            await self.db.execute(select(func.count()).select_from(Ofrecimiento).where(*condiciones))
        ).scalar_one()
        stmt = (
            select(Ofrecimiento)
            .where(*condiciones)
            .order_by(Ofrecimiento.fecha_creacion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        ofs = list((await self.db.execute(stmt)).scalars().all())
        return OfrecimientoPage(
            data=await self._salida(ofs, voluntario_id=voluntario_id, fundacion_id=fundacion_id),
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if per_page else 1,
        )

    async def detalle(
        self,
        ofrecimiento_id: uuid.UUID,
        voluntario_id: uuid.UUID | None,
        fundacion_id: uuid.UUID | None = None,
    ) -> OfrecimientoOut:
        of = await self.db.get(Ofrecimiento, ofrecimiento_id)
        if of is None:
            raise NotFoundError("Publicación no encontrada.")
        es_dueno = voluntario_id is not None and of.voluntario_id == voluntario_id
        if not es_dueno and of.estado in (OF_PAUSADO, OF_FINALIZADO):
            raise NotFoundError("Publicación no encontrada.")
        return (
            await self._salida([of], voluntario_id=voluntario_id, fundacion_id=fundacion_id)
        )[0]

    # ─────────────── Solicitudes de interés ───────────────

    async def solicitar(
        self, fundacion: Fundacion, ofrecimiento_id: uuid.UUID, data: SolicitudInteresCreate
    ) -> SolicitudInteresOut:
        of = (
            await self.db.execute(
                select(Ofrecimiento).where(Ofrecimiento.id == ofrecimiento_id).with_for_update()
            )
        ).scalar_one_or_none()
        if of is None or of.estado in (OF_PAUSADO, OF_FINALIZADO):
            raise NotFoundError("Publicación no encontrada.")
        if of.estado != OF_DISPONIBLE:
            raise ConflictError("Esta publicación ya no está disponible.")
        if of.fecha_vencimiento and of.fecha_vencimiento < date.today():
            raise ConflictError("Esta publicación ya venció.")
        cantidad = 1 if of.tipo == TIPO_SERVICIO else data.cantidad
        if cantidad > of.cantidad_disponible:
            raise ConflictError(f"Solo hay {of.cantidad_disponible} unidad(es) disponible(s).")
        existente = (
            await self.db.execute(
                select(SolicitudInteres.id).where(
                    SolicitudInteres.ofrecimiento_id == of.id,
                    SolicitudInteres.fundacion_id == fundacion.id,
                    SolicitudInteres.estado.in_(SI_ACTIVAS),
                )
            )
        ).first()
        if existente:
            raise ConflictError("Ya tienes una solicitud en curso para esta publicación.")

        sol = SolicitudInteres(
            id=uuid.uuid4(),
            ofrecimiento_id=of.id,
            fundacion_id=fundacion.id,
            cantidad=cantidad,
            mensaje=data.mensaje,
            estado=SI_PENDIENTE,
        )
        self.db.add(sol)
        await self.db.flush()
        vol = await self.db.get(Voluntario, of.voluntario_id)
        if vol:
            await self.notif.notificar(
                vol.usuario_id, TIPO_INTERES_RECIBIDO,
                f"«{fundacion.nombre}» está interesada en «{of.titulo}».",
                "solicitud_interes", sol.id,
            )
        salida = (await self._solicitudes_out([sol]))[0]
        await self.db.commit()
        return salida

    async def _solicitudes_out(
        self, sols: list[SolicitudInteres], *, voluntario_id: uuid.UUID | None = None
    ) -> list[SolicitudInteresOut]:
        if not sols:
            return []
        of_ids = {s.ofrecimiento_id for s in sols}
        ofs = {
            o.id: o
            for o in (
                await self.db.execute(select(Ofrecimiento).where(Ofrecimiento.id.in_(of_ids)))
            ).scalars().all()
        }
        funds = {
            f.id: f
            for f in (
                await self.db.execute(
                    select(Fundacion).where(Fundacion.id.in_({s.fundacion_id for s in sols}))
                )
            ).scalars().all()
        }
        nombres = {
            vid: nombre
            for vid, nombre in (
                await self.db.execute(
                    select(Voluntario.id, Usuario.nombre)
                    .join(Usuario, Usuario.id == Voluntario.usuario_id)
                    .where(Voluntario.id.in_({o.voluntario_id for o in ofs.values()}))
                )
            ).all()
        }
        salida: list[SolicitudInteresOut] = []
        for s in sols:
            o = ofs[s.ofrecimiento_id]
            salida.append(
                SolicitudInteresOut(
                    id=s.id,
                    ofrecimiento_id=o.id,
                    ofrecimiento_titulo=o.titulo,
                    ofrecimiento_tipo=o.tipo,
                    fundacion_id=s.fundacion_id,
                    fundacion_nombre=funds[s.fundacion_id].nombre,
                    voluntario_nombre=primer_nombre(nombres.get(o.voluntario_id, "")),
                    cantidad=s.cantidad,
                    mensaje=s.mensaje,
                    estado=s.estado,
                    confirmada_voluntario=s.confirmada_voluntario,
                    confirmada_fundacion=s.confirmada_fundacion,
                    fecha_creacion=s.fecha_creacion,
                    fecha_actualizacion=s.fecha_actualizacion,
                    fecha_completada=s.fecha_completada,
                    soy_voluntario=voluntario_id is not None and o.voluntario_id == voluntario_id,
                )
            )
        return salida

    async def mis_solicitudes(self, usuario: Usuario) -> list[SolicitudInteresOut]:
        repo = UsuarioRepository(self.db)
        if usuario.rol == ROL_VOLUNTARIO:
            vol = await repo.voluntario_por_usuario(usuario.id)
            if vol is None:
                return []
            stmt = (
                select(SolicitudInteres)
                .join(Ofrecimiento, Ofrecimiento.id == SolicitudInteres.ofrecimiento_id)
                .where(Ofrecimiento.voluntario_id == vol.id)
                .order_by(SolicitudInteres.fecha_actualizacion.desc())
            )
            vid = vol.id
        elif usuario.rol == ROL_FUNDACION:
            fund = await repo.fundacion_por_usuario(usuario.id)
            if fund is None:
                return []
            stmt = (
                select(SolicitudInteres)
                .where(SolicitudInteres.fundacion_id == fund.id)
                .order_by(SolicitudInteres.fecha_actualizacion.desc())
            )
            vid = None
        else:
            return []
        sols = list((await self.db.execute(stmt)).scalars().all())
        return await self._solicitudes_out(sols, voluntario_id=vid)

    async def _participante(
        self, usuario: Usuario, solicitud_id: uuid.UUID, *, bloquear: bool = False
    ) -> tuple[SolicitudInteres, Ofrecimiento, str]:
        """Devuelve (solicitud, ofrecimiento, rol) si el usuario es parte; si no, 404."""
        sol = await self.db.get(SolicitudInteres, solicitud_id)
        if sol is None:
            raise NotFoundError("Solicitud no encontrada.")
        if bloquear:
            of = (
                await self.db.execute(
                    select(Ofrecimiento).where(Ofrecimiento.id == sol.ofrecimiento_id).with_for_update()
                )
            ).scalar_one()
        else:
            of = await self.db.get(Ofrecimiento, sol.ofrecimiento_id)
        repo = UsuarioRepository(self.db)
        if usuario.rol == ROL_VOLUNTARIO:
            vol = await repo.voluntario_por_usuario(usuario.id)
            if vol is not None and vol.id == of.voluntario_id:
                return sol, of, ROL_VOLUNTARIO
        elif usuario.rol == ROL_FUNDACION:
            fund = await repo.fundacion_por_usuario(usuario.id)
            if fund is not None and fund.id == sol.fundacion_id:
                return sol, of, ROL_FUNDACION
        raise NotFoundError("Solicitud no encontrada.")

    async def _usuario_contraparte(
        self, sol: SolicitudInteres, of: Ofrecimiento, rol_actor: str
    ) -> tuple[uuid.UUID | None, str]:
        """(usuario_id de la otra parte, nombre visible de quien actúa)."""
        if rol_actor == ROL_VOLUNTARIO:
            fund = await self.db.get(Fundacion, sol.fundacion_id)
            vol = await self.db.get(Voluntario, of.voluntario_id)
            nombre = primer_nombre((await self.db.get(Usuario, vol.usuario_id)).nombre) if vol else "El voluntario"
            return (fund.usuario_id if fund else None), nombre
        vol = await self.db.get(Voluntario, of.voluntario_id)
        fund = await self.db.get(Fundacion, sol.fundacion_id)
        return (vol.usuario_id if vol else None), (fund.nombre if fund else "La organización")

    async def responder(
        self, usuario: Usuario, solicitud_id: uuid.UUID, decision: str
    ) -> SolicitudInteresOut:
        sol, of, rol = await self._participante(usuario, solicitud_id, bloquear=True)
        if rol != ROL_VOLUNTARIO:
            raise ForbiddenError("Solo quien publicó puede aceptar o rechazar.")
        if sol.estado != SI_PENDIENTE:
            raise ConflictError("Esta solicitud ya fue respondida.")
        destino, nombre = await self._usuario_contraparte(sol, of, rol)
        if decision == "ACEPTAR":
            if of.estado in (OF_PAUSADO, OF_FINALIZADO):
                raise ConflictError("La publicación no está activa.")
            if sol.cantidad > of.cantidad_disponible:
                raise ConflictError(
                    f"Solo quedan {of.cantidad_disponible} unidad(es) disponible(s)."
                )
            of.cantidad_disponible -= sol.cantidad
            sol.estado = SI_ACEPTADA
            msg = f"{nombre} aceptó tu solicitud de «{of.titulo}». Coordinen por mensajes."
        else:
            sol.estado = SI_RECHAZADA
            msg = f"Tu solicitud de «{of.titulo}» no pudo ser atendida. ¡Gracias por tu interés!"
        sol.fecha_actualizacion = _now()
        await self.db.flush()
        await self._recalcular_estado(of)
        if destino:
            await self.notif.notificar(destino, TIPO_INTERES_ACTUALIZADO, msg, "solicitud_interes", sol.id)
        salida = (await self._solicitudes_out([sol], voluntario_id=of.voluntario_id))[0]
        await self.db.commit()
        return salida

    async def confirmar(self, usuario: Usuario, solicitud_id: uuid.UUID) -> SolicitudInteresOut:
        """R9: se completa solo cuando ambas partes confirman."""
        sol, of, rol = await self._participante(usuario, solicitud_id, bloquear=True)
        if sol.estado not in (SI_ACEPTADA, SI_EN_COORDINACION):
            raise ConflictError("Solo se puede confirmar una solicitud aceptada.")
        if rol == ROL_VOLUNTARIO:
            if sol.confirmada_voluntario:
                raise ConflictError("Ya confirmaste esta entrega.")
            sol.confirmada_voluntario = True
        else:
            if sol.confirmada_fundacion:
                raise ConflictError("Ya confirmaste esta entrega.")
            sol.confirmada_fundacion = True
        destino, nombre = await self._usuario_contraparte(sol, of, rol)
        if sol.confirmada_voluntario and sol.confirmada_fundacion:
            sol.estado = SI_COMPLETADA
            sol.fecha_completada = _now()
            msg = f"La entrega de «{of.titulo}» quedó completada. ¡Gracias!"
        else:
            msg = f"{nombre} confirmó la entrega de «{of.titulo}». Falta tu confirmación."
        sol.fecha_actualizacion = _now()
        await self.db.flush()
        await self._recalcular_estado(of)
        if destino:
            await self.notif.notificar(destino, TIPO_INTERES_ACTUALIZADO, msg, "solicitud_interes", sol.id)
        if sol.estado == SI_COMPLETADA:
            # Avisa también a quien confirmó en último lugar.
            await self.notif.notificar(
                usuario.id, TIPO_INTERES_ACTUALIZADO, msg, "solicitud_interes", sol.id
            )
        salida = (await self._solicitudes_out([sol], voluntario_id=of.voluntario_id))[0]
        await self.db.commit()
        return salida

    async def cancelar(self, usuario: Usuario, solicitud_id: uuid.UUID) -> SolicitudInteresOut:
        sol, of, rol = await self._participante(usuario, solicitud_id, bloquear=True)
        if sol.estado not in SI_ACTIVAS:
            raise ConflictError("Esta solicitud ya no se puede cancelar.")
        if sol.estado in SI_RESERVAN_CANTIDAD:
            of.cantidad_disponible = min(of.cantidad_total, of.cantidad_disponible + sol.cantidad)
        sol.estado = SI_CANCELADA
        sol.fecha_actualizacion = _now()
        await self.db.flush()
        await self._recalcular_estado(of)
        destino, nombre = await self._usuario_contraparte(sol, of, rol)
        if destino:
            await self.notif.notificar(
                destino, TIPO_INTERES_ACTUALIZADO,
                f"{nombre} canceló la solicitud de «{of.titulo}».", "solicitud_interes", sol.id,
            )
        salida = (await self._solicitudes_out([sol], voluntario_id=of.voluntario_id))[0]
        await self.db.commit()
        return salida

    # ─────────────── Mensajería ───────────────

    async def mensajes(self, usuario: Usuario, solicitud_id: uuid.UUID) -> list[MensajeOut]:
        sol, of, rol = await self._participante(usuario, solicitud_id)
        vol = await self.db.get(Voluntario, of.voluntario_id)
        fund = await self.db.get(Fundacion, sol.fundacion_id)
        vol_usuario = await self.db.get(Usuario, vol.usuario_id) if vol else None
        filas = (
            await self.db.execute(
                select(MensajeInteres)
                .where(MensajeInteres.solicitud_id == sol.id)
                .order_by(MensajeInteres.fecha_creacion)
            )
        ).scalars().all()
        salida: list[MensajeOut] = []
        for m in filas:
            es_vol = vol is not None and m.autor_id == vol.usuario_id
            salida.append(
                MensajeOut(
                    id=m.id,
                    autor_rol=ROL_VOLUNTARIO if es_vol else ROL_FUNDACION,
                    autor_nombre=(
                        primer_nombre(vol_usuario.nombre) if es_vol and vol_usuario
                        else (fund.nombre if fund else "Organización")
                    ),
                    mensaje=m.mensaje,
                    fecha_creacion=m.fecha_creacion,
                    es_mio=m.autor_id == usuario.id,
                )
            )
        return salida

    async def enviar_mensaje(
        self, usuario: Usuario, solicitud_id: uuid.UUID, data: MensajeInput
    ) -> list[MensajeOut]:
        sol, of, rol = await self._participante(usuario, solicitud_id)
        if sol.estado in (SI_RECHAZADA, SI_CANCELADA):
            raise ConflictError("Esta conversación está cerrada.")
        if contiene_datos_personales(data.mensaje):
            raise AppError(
                "Por seguridad no compartas correos, teléfonos ni enlaces. "
                "Coordinen la entrega dentro de la plataforma.",
                422,
            )
        self.db.add(MensajeInteres(solicitud_id=sol.id, autor_id=usuario.id, mensaje=data.mensaje))
        if sol.estado == SI_ACEPTADA:
            sol.estado = SI_EN_COORDINACION
        sol.fecha_actualizacion = _now()
        await self.db.flush()
        destino, nombre = await self._usuario_contraparte(sol, of, rol)
        if destino:
            # Evita notificaciones duplicadas: una sola sin leer por conversación.
            ya = (
                await self.db.execute(
                    select(Notificacion.id).where(
                        Notificacion.usuario_id == destino,
                        Notificacion.tipo == TIPO_NUEVO_MENSAJE,
                        Notificacion.objeto_id == sol.id,
                        Notificacion.leida.is_(False),
                    )
                )
            ).first()
            if not ya:
                await self.notif.notificar(
                    destino, TIPO_NUEVO_MENSAJE,
                    f"{nombre} te escribió sobre «{of.titulo}».", "solicitud_interes", sol.id,
                )
        await self.db.commit()
        return await self.mensajes(usuario, solicitud_id)
