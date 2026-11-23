"""Esquemas Pydantic v2 de autenticación.

El contrato de respuesta (UsuarioOut, TokenResponse) reproduce EXACTAMENTE las
claves JSON que la app móvil Flutter ya consume, para no romper la compatibilidad.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.config import get_settings

_settings = get_settings()

ROLES_REGISTRABLES = {"VOLUNTARIO", "FUNDACION"}
TIPOS_DOCUMENTO = {"CC", "TI", "CE", "PASAPORTE"}
GENEROS = {"MASCULINO", "FEMENINO", "OTRO"}
DISPONIBILIDADES = {"ENTRE_SEMANA", "FINES_DE_SEMANA", "FLEXIBLE"}


def _validar_fortaleza_password(v: str) -> str:
    """Política de contraseñas en el backend (no se confía solo en el cliente)."""
    if len(v) < _settings.password_min_length:
        raise ValueError(
            f"La contraseña debe tener al menos {_settings.password_min_length} caracteres."
        )
    if not any(c.islower() for c in v):
        raise ValueError("La contraseña debe incluir al menos una letra minúscula.")
    if not any(c.isupper() for c in v):
        raise ValueError("La contraseña debe incluir al menos una letra mayúscula.")
    if not any(c.isdigit() for c in v):
        raise ValueError("La contraseña debe incluir al menos un número.")
    return v


# ─────────────────────────── Salida ───────────────────────────


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    email: str
    rol: str
    estado: str | None = None
    telefono: str | None = None
    email_verificado: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: object) -> str:
        return str(v)


class TokenResponse(BaseModel):
    """Respuesta de login/register/refresh con las claves exactas del móvil."""

    usuario: UsuarioOut | None = None
    token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - etiqueta estándar OAuth, no un secreto
    expires_in: int


class RefreshResponse(BaseModel):
    token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - etiqueta estándar OAuth, no un secreto
    expires_in: int


class MessageResponse(BaseModel):
    message: str


# ─────────────────────────── Entrada ───────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AceptacionLegalInput(BaseModel):
    """El cliente indica qué documento acepta; el backend fija versión y fecha."""

    codigo: str
    aceptado: bool = True


class RegisterVoluntarioRequest(BaseModel):
    # Bloquea asignación masiva de campos peligrosos (estado, provider, email_verificado).
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str
    password_confirmation: str
    telefono: str | None = Field(default=None, max_length=20)
    # `rol` se acepta por compatibilidad con el cliente móvil pero se IGNORA: el
    # backend fija el rol según el endpoint. Nunca se usa para conceder privilegios.
    rol: str | None = None

    # Datos de perfil de voluntario (crea cuenta + perfil en una transacción).
    tipo_documento: str
    numero_documento: str = Field(min_length=3, max_length=30)
    fecha_nacimiento: date
    genero: str
    municipio_id: int
    disponibilidad: str
    experiencia: str | None = None

    aceptaciones: list[AceptacionLegalInput] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _password_fuerte(cls, v: str) -> str:
        return _validar_fortaleza_password(v)

    @field_validator("tipo_documento")
    @classmethod
    def _tipo_doc(cls, v: str) -> str:
        if v not in TIPOS_DOCUMENTO:
            raise ValueError(f"tipo_documento inválido. Valores: {sorted(TIPOS_DOCUMENTO)}")
        return v

    @field_validator("genero")
    @classmethod
    def _genero(cls, v: str) -> str:
        if v not in GENEROS:
            raise ValueError(f"genero inválido. Valores: {sorted(GENEROS)}")
        return v

    @field_validator("disponibilidad")
    @classmethod
    def _disp(cls, v: str) -> str:
        if v not in DISPONIBILIDADES:
            raise ValueError(f"disponibilidad inválida. Valores: {sorted(DISPONIBILIDADES)}")
        return v

    def passwords_coinciden(self) -> bool:
        return self.password == self.password_confirmation


class RegisterFundacionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str
    password_confirmation: str
    telefono: str | None = Field(default=None, max_length=20)
    # `rol` aceptado por compatibilidad móvil pero ignorado (ver nota en voluntario).
    rol: str | None = None

    # Datos de perfil de la organización. Si no está constituida legalmente (refugio
    # independiente, colectivo) NIT y documento legal son opcionales (R13).
    nombre_fundacion: str = Field(min_length=1, max_length=150)
    tipo_organizacion: str = "FUNDACION"
    constituida_legalmente: bool = True
    nit: str | None = Field(default=None, max_length=20)
    representante_legal: str = Field(min_length=1, max_length=150)
    correo_institucional: EmailStr | None = None
    telefono_contacto: str = Field(max_length=20)
    direccion: str = Field(min_length=1, max_length=200)
    municipio_id: int
    descripcion: str = Field(min_length=1)
    documento_legal: str | None = None
    pagina_web: str | None = Field(default=None, max_length=255)

    aceptaciones: list[AceptacionLegalInput] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def _password_fuerte(cls, v: str) -> str:
        return _validar_fortaleza_password(v)

    @field_validator("tipo_organizacion")
    @classmethod
    def _tipo_org(cls, v: str) -> str:
        validos = ("FUNDACION", "REFUGIO", "COLECTIVO", "INICIATIVA_CIUDADANA", "OTRA")
        if v not in validos:
            raise ValueError(f"tipo_organizacion inválido. Valores: {validos}")
        return v

    @field_validator("nit", "documento_legal", mode="before")
    @classmethod
    def _vacio_a_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("nit")
    @classmethod
    def _nit_formato(cls, v: str | None) -> str | None:
        import re

        if v is not None and not re.fullmatch(r"\d{7,10}-\d", v):
            raise ValueError(
                "El NIT debe tener el formato 000000000-0 (7 a 10 dígitos y dígito verificador)."
            )
        return v

    @model_validator(mode="after")
    def _constituida_requiere_documentos(self) -> RegisterFundacionRequest:
        if self.constituida_legalmente and not (self.nit and self.documento_legal):
            raise ValueError(
                "Una organización constituida legalmente debe indicar NIT y documento legal."
            )
        return self

    def passwords_coinciden(self) -> bool:
        return self.password == self.password_confirmation


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str
    password_confirmation: str

    @field_validator("password")
    @classmethod
    def _password_fuerte(cls, v: str) -> str:
        return _validar_fortaleza_password(v)

    def passwords_coinciden(self) -> bool:
        return self.password == self.password_confirmation


class GoogleLoginRequest(BaseModel):
    """Intercambio de id_token de Google. rol solo se usa si la cuenta es nueva."""

    id_token: str = Field(min_length=1)
    rol: str | None = None

    @field_validator("rol")
    @classmethod
    def _rol(cls, v: str | None) -> str | None:
        if v is not None and v not in ROLES_REGISTRABLES:
            raise ValueError(f"rol inválido. Valores: {sorted(ROLES_REGISTRABLES)}")
        return v
