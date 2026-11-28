"""Gestión del perfil de dominio (voluntario / fundación) del usuario autenticado."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.edad import validar_fecha_nacimiento
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models.fundacion import ESTADO_PENDIENTE, Fundacion
from app.models.usuario import ROL_FUNDACION, ROL_VOLUNTARIO, Usuario
from app.models.voluntario import Voluntario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.perfil import (
    FundacionPerfilInput,
    FundacionPerfilOut,
    VoluntarioPerfilInput,
    VoluntarioPerfilOut,
)
from app.services.storage_service import StorageService


class PerfilService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UsuarioRepository(db)
        self.storage = StorageService(get_settings())

    async def estado(self, usuario: Usuario) -> bool:
        """Devuelve True si el usuario ya tiene su perfil de dominio."""
        if usuario.rol == ROL_VOLUNTARIO:
            return await self.repo.voluntario_por_usuario(usuario.id) is not None
        if usuario.rol == ROL_FUNDACION:
            return await self.repo.fundacion_por_usuario(usuario.id) is not None
        return True  # admin no requiere perfil

    # ─────────────── Voluntario ───────────────

    async def obtener_voluntario(self, usuario: Usuario) -> Voluntario | None:
        if usuario.rol != ROL_VOLUNTARIO:
            raise ForbiddenError("Solo los voluntarios tienen este perfil.")
        return await self.repo.voluntario_por_usuario(usuario.id)

    async def guardar_voluntario(
        self, usuario: Usuario, data: VoluntarioPerfilInput
    ) -> VoluntarioPerfilOut:
        if usuario.rol != ROL_VOLUNTARIO:
            raise ForbiddenError("Solo los voluntarios pueden completar este perfil.")

        existente = await self.repo.voluntario_por_usuario(usuario.id)

        if existente is None:
            # Crear: edad mínima de 16 años (ver app/core/edad.py).
            try:
                validar_fecha_nacimiento(data.fecha_nacimiento)
            except ValueError as exc:
                raise AppError(str(exc), 422) from exc
            # Validar que el documento no esté en uso por otro.
            if await self.repo.existe_numero_documento(data.numero_documento):
                raise ConflictError("Ese número de documento ya está registrado.")
            perfil = Voluntario(
                usuario_id=usuario.id,
                tipo_documento=data.tipo_documento,
                numero_documento=data.numero_documento,
                fecha_nacimiento=data.fecha_nacimiento,
                genero=data.genero,
                municipio_id=data.municipio_id,
                disponibilidad=data.disponibilidad,
                experiencia=data.experiencia,
            )
            self._aplicar_editables(perfil, data)
            self.db.add(perfil)
        else:
            # Actualizar: los campos de identidad son INMUTABLES. Si el cliente
            # envía valores distintos, se rechaza para evitar cambios silenciosos.
            if (
                data.numero_documento != existente.numero_documento
                or data.tipo_documento != existente.tipo_documento
                or data.fecha_nacimiento != existente.fecha_nacimiento
                or data.genero != existente.genero
            ):
                raise ForbiddenError(
                    "Los datos de identidad (documento, fecha de nacimiento y género) "
                    "no se pueden modificar desde el perfil. Solicita una corrección "
                    "al equipo de soporte."
                )
            existente.municipio_id = data.municipio_id
            existente.disponibilidad = data.disponibilidad
            existente.experiencia = data.experiencia
            self._aplicar_editables(existente, data)
            perfil = existente

        await self.db.flush()
        salida = VoluntarioPerfilOut.model_validate(perfil)
        await self.db.commit()
        return salida

    @staticmethod
    def _aplicar_editables(perfil: Voluntario, data: VoluntarioPerfilInput) -> None:
        """Copia los campos editables ampliados del perfil."""
        perfil.direccion = data.direccion
        perfil.descripcion = data.descripcion
        perfil.telefono_contacto = data.telefono_contacto
        perfil.nivel_educativo = data.nivel_educativo
        perfil.profesion = data.profesion
        perfil.idiomas = data.idiomas
        perfil.preferencia_modalidad = data.preferencia_modalidad
        perfil.contacto_emergencia_nombre = data.contacto_emergencia_nombre
        perfil.contacto_emergencia_telefono = data.contacto_emergencia_telefono

    # ─────────────── Fundación ───────────────

    async def obtener_fundacion(self, usuario: Usuario) -> Fundacion | None:
        if usuario.rol != ROL_FUNDACION:
            raise ForbiddenError("Solo las fundaciones tienen este perfil.")
        return await self.repo.fundacion_por_usuario(usuario.id)

    async def guardar_fundacion(
        self, usuario: Usuario, data: FundacionPerfilInput
    ) -> FundacionPerfilOut:
        if usuario.rol != ROL_FUNDACION:
            raise ForbiddenError("Solo las fundaciones pueden completar este perfil.")

        existente = await self.repo.fundacion_por_usuario(usuario.id)

        if existente is None:
            if data.nit and await self.repo.existe_nit(data.nit):
                raise ConflictError("Ese NIT ya está registrado.")
            perfil = Fundacion(
                usuario_id=usuario.id,
                nombre=data.nombre_fundacion,
                nit=data.nit,
                tipo_organizacion=data.tipo_organizacion,
                constituida_legalmente=data.constituida_legalmente,
                representante_legal=data.representante_legal,
                correo_institucional=data.correo_institucional,
                telefono=data.telefono_contacto,
                direccion=data.direccion,
                municipio_id=data.municipio_id,
                descripcion=data.descripcion,
                documento_legal=data.documento_legal,
                pagina_web=data.pagina_web,
                estado_verificacion=ESTADO_PENDIENTE,
            )
            self.db.add(perfil)
        else:
            # Datos legales/de identidad INMUTABLES desde el perfil.
            if (
                data.nombre_fundacion != existente.nombre
                or (data.nit or None) != (existente.nit or None)
                or data.tipo_organizacion != existente.tipo_organizacion
                or data.constituida_legalmente != existente.constituida_legalmente
                or data.representante_legal != existente.representante_legal
                or (data.documento_legal or None) != (existente.documento_legal or None)
            ):
                raise ForbiddenError(
                    "El nombre, tipo de organización, NIT, representante legal y documento "
                    "legal no se pueden modificar desde el perfil. Solicita una corrección "
                    "al equipo de soporte."
                )
            existente.correo_institucional = data.correo_institucional
            existente.telefono = data.telefono_contacto
            existente.direccion = data.direccion
            existente.municipio_id = data.municipio_id
            existente.descripcion = data.descripcion
            existente.documento_legal = data.documento_legal
            existente.pagina_web = data.pagina_web
            perfil = existente

        await self.db.flush()
        salida = FundacionPerfilOut.model_validate(perfil)
        await self.db.commit()
        return salida

    # ─────────────── Subida de archivos ───────────────

    async def subir_foto_voluntario(self, usuario: Usuario, file: UploadFile) -> str:
        if usuario.rol != ROL_VOLUNTARIO:
            raise ForbiddenError("Solo los voluntarios pueden subir foto de perfil aquí.")
        perfil = await self.repo.voluntario_por_usuario(usuario.id)
        if perfil is None:
            raise NotFoundError("Primero completa tu perfil de voluntario.")
        url = await self.storage.guardar_imagen(file, "fotos")
        perfil.foto_perfil = url
        await self.db.commit()
        return url

    async def subir_documento_voluntario(self, usuario: Usuario, file: UploadFile) -> str:
        """Sube el documento de identidad para verificación (queda pendiente de revisión)."""
        if usuario.rol != ROL_VOLUNTARIO:
            raise ForbiddenError("Solo los voluntarios pueden subir su documento aquí.")
        perfil = await self.repo.voluntario_por_usuario(usuario.id)
        if perfil is None:
            raise NotFoundError("Primero completa tu perfil de voluntario.")
        # Almacenamiento PRIVADO: solo el dueño y los administradores pueden verlo.
        anterior = perfil.documento_identidad
        url = await self.storage.guardar_documento(file, "documentos")
        perfil.documento_identidad = url
        self.storage.eliminar_privado(anterior)
        # Al subir un nuevo documento, la verificación vuelve a quedar pendiente.
        perfil.esta_verificado = False
        await self.db.commit()
        return url

    async def subir_logo_fundacion(self, usuario: Usuario, file: UploadFile) -> str:
        if usuario.rol != ROL_FUNDACION:
            raise ForbiddenError("Solo las fundaciones pueden subir su logo.")
        perfil = await self.repo.fundacion_por_usuario(usuario.id)
        if perfil is None:
            raise NotFoundError("Primero completa el perfil de tu fundación.")
        url = await self.storage.guardar_imagen(file, "logos")
        perfil.logo = url
        await self.db.commit()
        return url

    async def subir_banner_fundacion(self, usuario: Usuario, file: UploadFile) -> str:
        if usuario.rol != ROL_FUNDACION:
            raise ForbiddenError("Solo las fundaciones pueden subir su banner.")
        perfil = await self.repo.fundacion_por_usuario(usuario.id)
        if perfil is None:
            raise NotFoundError("Primero completa el perfil de tu fundación.")
        url = await self.storage.guardar_imagen(file, "banners")
        perfil.imagen_banner = url
        await self.db.commit()
        return url
