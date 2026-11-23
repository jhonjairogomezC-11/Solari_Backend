"""Modelos de catálogos (solo lectura): áreas, habilidades, municipios, departamentos."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Departamento(Base):
    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)

    municipios: Mapped[list[Municipio]] = relationship(back_populates="departamento")


class Municipio(Base):
    __tablename__ = "municipios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100))
    departamento_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departamentos.id", ondelete="RESTRICT")
    )

    departamento: Mapped[Departamento] = relationship(back_populates="municipios")


class AreaImpacto(Base):
    __tablename__ = "areas_impacto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class Habilidad(Base):
    __tablename__ = "habilidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    # Categoría temática del catálogo (cuidado animal, salud y bienestar, etc.).
    categoria: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Distingue habilidades profesionales/técnicas de las generales o de apoyo.
    es_profesional: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
