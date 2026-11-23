from app.models.admin_accion import AdminAccion, AdminPerfil, HistorialEstadoVoluntario
from app.models.catalogo import AreaImpacto, Departamento, Habilidad, Municipio
from app.models.cuenta import AuditoriaPerfil, PreferenciasNotificacion
from app.models.habilidades import VoluntarioHabilidad
from app.models.ofrecimiento import Ofrecimiento, MensajeInteres, SolicitudInteres
from app.models.organizacion import (
    FundacionDocumento,
    FundacionGaleria,
    ResenaOrganizacion,
)
from app.models.programacion import ProgramacionRecurrente
from app.models.favorito import VoluntarioFavorito
from app.models.fundacion import Fundacion
from app.models.gamificacion import (
    Interes,
    Logro,
    PublicacionImagen,
    TransaccionPuntos,
    VoluntarioInteres,
    VoluntarioLogro,
    VoluntarioPuntos,
)
from app.models.legal import (
    DocumentoLegal,
    DocumentoLegalVersion,
    UsuarioAceptacionLegal,
)
from app.models.notificacion import Notificacion
from app.models.postulacion import Postulacion, PostulacionHistorial
from app.models.publicacion import Publicacion
from app.models.soporte import (
    SolicitudCuenta,
    TicketMensaje,
    TicketSoporte,
)
from app.models.tokens import (
    RecuperacionPassword,
    RefreshToken,
    VerificacionEmail,
)
from app.models.usuario import Usuario
from app.models.voluntario import Voluntario

__all__ = [
    "Usuario",
    "Voluntario",
    "Fundacion",
    "AreaImpacto",
    "Departamento",
    "Habilidad",
    "Municipio",
    "Publicacion",
    "Postulacion",
    "Notificacion",
    "VoluntarioFavorito",
    "RefreshToken",
    "RecuperacionPassword",
    "VerificacionEmail",
    "DocumentoLegal",
    "DocumentoLegalVersion",
    "UsuarioAceptacionLegal",
    # Gamificación e intereses
    "Interes",
    "VoluntarioInteres",
    "Logro",
    "VoluntarioLogro",
    "VoluntarioPuntos",
    "TransaccionPuntos",
    "PublicacionImagen",
    # Soporte
    "TicketSoporte",
    "TicketMensaje",
    "SolicitudCuenta",
    # Cuenta
    "PreferenciasNotificacion",
    "AuditoriaPerfil",
    # Ampliación alineada al documento de grado
    "AdminAccion",
    "AdminPerfil",
    "HistorialEstadoVoluntario",
    "VoluntarioHabilidad",
    "Ofrecimiento",
    "SolicitudInteres",
    "MensajeInteres",
    "FundacionDocumento",
    "FundacionGaleria",
    "ResenaOrganizacion",
    "ProgramacionRecurrente",
    "PostulacionHistorial",
]
