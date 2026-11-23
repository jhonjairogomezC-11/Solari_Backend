"""Utilidades puras (sin acceso a datos) de coincidencia y normalización de texto.

Al ser funciones puras se prueban de forma aislada, sin base de datos.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_STOPWORDS = {"y", "de", "la", "el", "los", "las", "del", "en", "para", "con", "por"}


def calcular_coincidencia(requeridas: Iterable[int], poseidas: Iterable[int]) -> int:
    """Porcentaje (0-100) de habilidades requeridas que el voluntario posee.

    coincidencia = (habilidades coincidentes / habilidades requeridas) x 100

    La coincidencia ordena las oportunidades pero nunca las excluye (regla R2).
    Si la actividad no exige habilidades, devuelve 0.
    """
    req = set(requeridas)
    if not req:
        return 0
    return round(len(req & set(poseidas)) * 100 / len(req))


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar nombres de catálogos."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.lower().strip()


def raices(texto: str) -> set[str]:
    """Raíces de 5 letras de las palabras significativas ('Educación' -> 'educa').

    Permite relacionar 'Educación'/'Educacion'/'Educativo' o 'Deporte'/'Deportes'
    sin depender de que los catálogos se escriban igual.
    """
    palabras = re.findall(r"[a-z]+", normalizar(texto))
    return {p[:5] for p in palabras if len(p) >= 4 and p not in _STOPWORDS}


def textos_relacionados(a: str, b: str) -> bool:
    return bool(raices(a) & raices(b))


# Detección básica de datos personales y lenguaje ofensivo (moderación).
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_RE_TELEFONO = re.compile(r"(?:\+?\d[\s().-]*){7,}")
_RE_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_OFENSIVAS = (
    "idiota", "estupid", "imbecil", "malparid", "hijueputa", "gonorrea",
    "hijo de puta", "mierda", "basura de", "ladrones", "estafadores",
)


def contiene_datos_personales(texto: str) -> bool:
    return bool(_RE_EMAIL.search(texto) or _RE_TELEFONO.search(texto) or _RE_URL.search(texto))


def contiene_lenguaje_ofensivo(texto: str) -> bool:
    t = normalizar(texto)
    return any(p in t for p in _OFENSIVAS)
