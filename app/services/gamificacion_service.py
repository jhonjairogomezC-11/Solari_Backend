"""Reglas de negocio de gamificación: puntos (XP), logros, intereses y ranking.

Principios antifraude (exigidos):
- Los puntos solo se otorgan cuando la fundación confirma la asistencia (ASISTIO).
- Nunca por registrarse, iniciar sesión ni por postularse repetidamente.
- Cada logro se otorga una sola vez (restricción única + verificación).
- Todo movimiento queda registrado en `transacciones_puntos` (trazabilidad).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamificacion import (
    LOGRO_DIFICULTAD,
    LOGRO_PARTICIPACIONES,
    LOGRO_PUNTOS,
    LOGRO_URGENTE,
    TransaccionPuntos,
)
from app.models.notificacion import TIPO_LOGRO_DESBLOQUEADO, TIPO_XP_OBTENIDO
from app.models.postulacion import ESTADO_ASISTIO, Postulacion
from app.models.publicacion import Publicacion
from app.models.voluntario import Voluntario
from app.repositories.gamificacion_repo import GamificacionRepository
from app.services.notificacion_service import NotificacionService

# Puntos base por asistencia confirmada + por hora reconocida.
PUNTOS_POR_ASISTENCIA = 50
PUNTOS_POR_HORA = 5

# Niveles: son un reconocimiento visual calculado desde el XP total. NO desbloquean
# funcionalidades. (xp mínimo, nombre)
NIVELES: tuple[tuple[int, str], ...] = (
    (0, "Chispa"),
    (100, "Destello"),
    (300, "Amanecer"),
    (600, "Resplandor"),
    (1000, "Aurora"),
    (1800, "Sol naciente"),
    (3000, "Sol pleno"),
    (5000, "Supernova"),
)


def calcular_nivel(xp: int) -> dict:
    """Nivel (1..8) según el XP total y el progreso hacia el siguiente."""
    idx = 0
    for i, (minimo, _) in enumerate(NIVELES):
        if xp >= minimo:
            idx = i
    actual_min, nombre = NIVELES[idx]
    siguiente = NIVELES[idx + 1][0] if idx + 1 < len(NIVELES) else None
    return {
        "nivel": idx + 1,
        "nivel_nombre": nombre,
        "xp_nivel_actual": actual_min,
        "xp_siguiente_nivel": siguiente,
    }


class GamificacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GamificacionRepository(db)
        self.notif = NotificacionService(db)

    async def _saldo(self, voluntario_id: uuid.UUID):
        saldo = await self.repo.puntos_bloqueado(voluntario_id)
        if saldo is None:
            saldo = await self.repo.crear_saldo(voluntario_id)
        return saldo

    async def otorgar_por_asistencia(
        self, voluntario: Voluntario, postulacion: Postulacion, publicacion: Publicacion
    ) -> None:
        """Otorga puntos y evalúa logros tras confirmar asistencia.

        Idempotente respecto a la postulación: si ya existe una transacción para
        esta postulación, no vuelve a otorgar.
        """
        ya = (
            await self.db.execute(
                select(func.count())
                .select_from(TransaccionPuntos)
                .where(TransaccionPuntos.postulacion_id == postulacion.id)
            )
        ).scalar_one()
        if ya > 0:
            return

        horas = publicacion.horas_reconocidas or 0
        puntos_base = PUNTOS_POR_ASISTENCIA
        puntos_bonus = horas * PUNTOS_POR_HORA
        total = puntos_base + puntos_bonus

        saldo = await self._saldo(voluntario.id)
        saldo.saldo += total
        saldo.total_historico += total
        self.repo.registrar_transaccion(
            voluntario.id,
            total,
            f"Asistencia confirmada: «{publicacion.titulo}»",
            postulacion_id=postulacion.id,
            puntos_base=puntos_base,
            puntos_bonus=puntos_bonus,
        )

        # Actualiza estadísticas cacheadas del voluntario.
        voluntario.actividades_completadas = (voluntario.actividades_completadas or 0) + 1
        voluntario.horas_acumuladas = (voluntario.horas_acumuladas or 0) + horas

        await self.db.flush()

        # Notifica XP obtenido.
        await self.notif.notificar(
            voluntario.usuario_id,
            TIPO_XP_OBTENIDO,
            f"¡Ganaste {total} XP por tu participación en «{publicacion.titulo}»!",
            "postulacion",
            postulacion.id,
        )

        await self._evaluar_logros(voluntario)

    async def _evaluar_logros(self, voluntario: Voluntario) -> None:
        """Comprueba condiciones de logros y otorga los que correspondan (una vez)."""
        logros = await self.repo.logros_activos()
        if not logros:
            return
        obtenidos = await self.repo.ids_logros_obtenidos(voluntario.id)

        actividades = voluntario.actividades_completadas or 0
        saldo = await self.repo.puntos_de(voluntario.id)
        xp_total = saldo.total_historico if saldo else 0
        urgentes = await self._urgentes_asistidas(voluntario.id)
        dificiles = await self._dificiles_asistidas(voluntario.id)

        for logro in logros:
            if logro.id in obtenidos:
                continue
            cumple = False
            if logro.tipo == LOGRO_PARTICIPACIONES:
                cumple = actividades >= logro.umbral
            elif logro.tipo == LOGRO_PUNTOS:
                cumple = xp_total >= logro.umbral
            elif logro.tipo == LOGRO_URGENTE:
                cumple = urgentes >= logro.umbral
            elif logro.tipo == LOGRO_DIFICULTAD:
                cumple = dificiles >= logro.umbral

            if cumple:
                # Los logros reconocen la trayectoria; el XP solo proviene de la
                # asistencia confirmada (50 + 5 por hora), como define el documento.
                self.repo.otorgar_logro(voluntario.id, logro.id)
                await self.db.flush()
                await self.notif.notificar(
                    voluntario.usuario_id,
                    TIPO_LOGRO_DESBLOQUEADO,
                    f"Desbloqueaste el logro «{logro.nombre}».",
                    "logro",
                    None,
                )

    # ─────────────── Consultas (lectura) ───────────────

    async def resumen(self, voluntario: Voluntario) -> dict:
        saldo = await self.repo.puntos_de(voluntario.id)
        logros = await self.repo.logros_activos()
        obtenidos = await self.repo.ids_logros_obtenidos(voluntario.id)
        xp_total = saldo.total_historico if saldo else 0
        return {
            "xp_total": xp_total,
            "xp_saldo": saldo.saldo if saldo else 0,
            "horas_acumuladas": voluntario.horas_acumuladas or 0,
            "actividades_completadas": voluntario.actividades_completadas or 0,
            "logros_desbloqueados": len(obtenidos),
            "logros_totales": len(logros),
            **calcular_nivel(xp_total),
        }

    async def logros_con_estado(self, voluntario_id: uuid.UUID) -> list[dict]:
        logros = await self.repo.logros_activos()
        obtenidos = {
            vl.logro_id: vl.fecha_obtencion
            for vl in await self.repo.logros_obtenidos(voluntario_id)
        }
        salida = []
        for logro in logros:
            salida.append({
                "id": logro.id,
                "codigo": logro.codigo,
                "nombre": logro.nombre,
                "descripcion": logro.descripcion,
                "icono": logro.icono,
                "tipo": logro.tipo,
                "umbral": logro.umbral,
                "desbloqueado": logro.id in obtenidos,
                "fecha_obtencion": obtenidos.get(logro.id),
            })
        return salida

    async def historial_xp(self, voluntario_id: uuid.UUID) -> list:
        return await self.repo.transacciones(voluntario_id)

    async def ranking(self, voluntario_id: uuid.UUID, limite: int = 1000) -> dict:
        top_rows = await self.repo.ranking_top(limite)
        top = [
            {
                "posicion": pos,
                "voluntario_id": vol.id,
                "nombre": "",  # se completa abajo con el nombre del usuario
                "foto_perfil": vol.foto_perfil,
                "xp": xp,
                "nivel": calcular_nivel(xp)["nivel"],
                "_usuario_id": vol.usuario_id,
            }
            for (vol, xp, pos) in top_rows
        ]
        # Cargar nombres de usuario en lote.
        from app.models.usuario import Usuario

        if top:
            ids = [item["_usuario_id"] for item in top]
            rows = await self.db.execute(
                select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))
            )
            nombres = {r[0]: r[1] for r in rows.all()}
            for item in top:
                item["nombre"] = nombres.get(item["_usuario_id"], "Voluntario")
                del item["_usuario_id"]

        mi_pos, mi_xp, total = await self.repo.posicion_de(voluntario_id)
        return {
            "top": top,
            "mi_posicion": mi_pos,
            "mi_xp": mi_xp,
            "total_voluntarios": total,
            "en_top": 0 < mi_pos <= limite,
        }

    # ─────────────── Intereses ───────────────

    async def catalogo_intereses(self) -> list:
        return await self.repo.catalogo_intereses()

    async def intereses_de(self, voluntario_id: uuid.UUID) -> list[int]:
        return await self.repo.intereses_de(voluntario_id)

    async def guardar_intereses(
        self, voluntario_id: uuid.UUID, interes_ids: list[int]
    ) -> list[int]:
        from app.core.exceptions import AppError

        unicos = list(dict.fromkeys(interes_ids))  # elimina duplicados conservando orden
        validos = await self.repo.interes_ids_validos(unicos)
        invalidos = [i for i in unicos if i not in validos]
        if invalidos:
            raise AppError(f"Algunos intereses no existen: {invalidos}")
        await self.repo.reemplazar_intereses(voluntario_id, unicos)
        await self.db.commit()
        return unicos

    async def _urgentes_asistidas(self, voluntario_id: uuid.UUID) -> int:
        """Convocatorias marcadas como urgentes a las que el voluntario asistió."""
        stmt = (
            select(func.count())
            .select_from(Postulacion)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .where(
                Postulacion.voluntario_id == voluntario_id,
                Postulacion.estado == ESTADO_ASISTIO,
                Publicacion.urgente.is_(True),
            )
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def _dificiles_asistidas(self, voluntario_id: uuid.UUID) -> int:
        """Actividades de dificultad alta asistidas (columna `dificultad` existente)."""
        from sqlalchemy import text as _text

        stmt = _text(
            "SELECT count(*) FROM postulaciones p "
            "JOIN publicaciones pub ON pub.id = p.publicacion_id "
            "WHERE p.voluntario_id = :vid AND p.estado = 'ASISTIO' "
            "AND pub.dificultad IN ('DIFICIL', 'MUY_DIFICIL')"
        )
        res = await self.db.execute(stmt, {"vid": str(voluntario_id)})
        return res.scalar_one()
