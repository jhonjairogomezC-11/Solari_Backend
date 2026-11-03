"""Base declarativa de SQLAlchemy para todos los modelos."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base de los modelos ORM."""
