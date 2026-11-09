"""Gestión del perfil de dominio (voluntario / fundación) del usuario autenticado."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
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
            # Crear: validar que el documento no esté en uso por otro.
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
            self.db.add(perfil)
        else:
            # Actualizar: el documento solo cambia si no colisiona.
            if (
                data.numero_documento != existente.numero_documento
                and await self.repo.existe_numero_documento(data.numero_documento)
            ):
                raise ConflictError("Ese número de documento ya está registrado.")
            existente.tipo_documento = data.tipo_documento
            existente.numero_documento = data.numero_documento
            existente.fecha_nacimiento = data.fecha_nacimiento
            existente.genero = data.genero
            existente.municipio_id = data.municipio_id
            existente.disponibilidad = data.disponibilidad
            existente.experiencia = data.experiencia
            perfil = existente

        await self.db.flush()
        salida = VoluntarioPerfilOut.model_validate(perfil)
        await self.db.commit()
        return salida

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
            if await self.repo.existe_nit(data.nit):
                raise ConflictError("Ese NIT ya está registrado.")
            perfil = Fundacion(
                usuario_id=usuario.id,
                nombre=data.nombre_fundacion,
                nit=data.nit,
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
            if data.nit != existente.nit and await self.repo.existe_nit(data.nit):
                raise ConflictError("Ese NIT ya está registrado.")
            existente.nombre = data.nombre_fundacion
            existente.nit = data.nit
            existente.representante_legal = data.representante_legal
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
        url = await self.storage.guardar_documento(file, "documentos")
        perfil.documento_identidad = url
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
