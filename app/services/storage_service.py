"""Almacenamiento local de archivos subidos (fotos y documentos).

Seguridad:
- Valida el tipo real por los primeros bytes (magic numbers), no solo por extensión.
- Limita el tamaño máximo.
- Genera un nombre aleatorio (nunca usa el nombre del cliente) para evitar
  path traversal y colisiones.
- Guarda en subcarpetas por categoría.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError

# Firmas (magic bytes) de los formatos permitidos.
_IMAGE_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # WEBP: 'RIFF'....'WEBP'
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}
_PDF_SIGNATURE = b"%PDF-"

# Carpetas servidas públicamente (imágenes de perfil, logos, galerías...).
CARPETAS_PUBLICAS = ("fotos", "logos", "ofrecimientos", "galeria", "convocatorias")
# Carpetas privadas: solo accesibles mediante el endpoint autenticado.
CARPETAS_PRIVADAS = ("documentos", "verificacion")
PRIVADO_PREFIJO = "/archivos/privado"


def _detect_image_ext(head: bytes) -> str | None:
    for sig, ext in _IMAGE_SIGNATURES.items():
        if head.startswith(sig):
            if ext == "webp" and head[8:12] != b"WEBP":
                continue
            return ext
    return None


class StorageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base = Path(settings.upload_dir)
        self.max_bytes = settings.upload_max_mb * 1024 * 1024

    async def _read_validated(self, file: UploadFile) -> bytes:
        contenido = await file.read()
        if len(contenido) == 0:
            raise AppError("El archivo está vacío.")
        if len(contenido) > self.max_bytes:
            raise AppError(
                f"El archivo supera el máximo de {self.settings.upload_max_mb} MB."
            )
        return contenido

    def _guardar(self, carpeta: str, contenido: bytes, ext: str) -> str:
        destino_dir = self.base / carpeta
        destino_dir.mkdir(parents=True, exist_ok=True)
        nombre = f"{secrets.token_urlsafe(16)}.{ext}"
        (destino_dir / nombre).write_bytes(contenido)
        # Ruta pública relativa servida por la app.
        return f"{self.settings.upload_public_base}/{carpeta}/{nombre}"

    async def guardar_imagen(self, file: UploadFile, carpeta: str) -> str:
        contenido = await self._read_validated(file)
        ext = _detect_image_ext(contenido[:16])
        if ext is None:
            raise AppError("Formato de imagen no válido. Usa JPG, PNG, WEBP o GIF.")
        return self._guardar(carpeta, contenido, ext)

    async def guardar_documento(self, file: UploadFile, carpeta: str) -> str:
        """Acepta imágenes o PDF y los guarda en almacenamiento PRIVADO.

        Devuelve la ruta de la API que entrega el archivo solo a su dueño o a un
        administrador (`/archivos/privado/<carpeta>/<nombre>`); nunca una URL pública.
        """
        contenido = await self._read_validated(file)
        head = contenido[:16]
        ext = _detect_image_ext(head)
        if ext is None and head.startswith(_PDF_SIGNATURE):
            ext = "pdf"
        if ext is None:
            raise AppError("Formato no válido. Usa una imagen (JPG, PNG) o un PDF.")
        destino_dir = Path(self.settings.private_upload_dir) / carpeta
        destino_dir.mkdir(parents=True, exist_ok=True)
        nombre = f"{secrets.token_urlsafe(16)}.{ext}"
        (destino_dir / nombre).write_bytes(contenido)
        return f"{PRIVADO_PREFIJO}/{carpeta}/{nombre}"

    def ruta_privada(self, carpeta: str, nombre: str) -> Path:
        return Path(self.settings.private_upload_dir) / carpeta / nombre

    def eliminar_privado(self, referencia: str | None) -> None:
        """Borra un archivo privado a partir de su referencia de API (mejor esfuerzo)."""
        if not referencia or not referencia.startswith(PRIVADO_PREFIJO + "/"):
            return
        partes = referencia.removeprefix(PRIVADO_PREFIJO + "/").split("/")
        if len(partes) == 2 and partes[0] in CARPETAS_PRIVADAS:
            self.ruta_privada(partes[0], partes[1]).unlink(missing_ok=True)
