"""Pruebas de integración de las reglas del documento de grado (BD real).

Cada prueba indica la regla o sección del documento que verifica.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError
from app.core.security import create_access_token
from app.models.admin_accion import AdminAccion, AdminPerfil
from app.models.gamificacion import VoluntarioLogro, VoluntarioPuntos
from app.models.notificacion import Notificacion
from app.models.organizacion import FundacionDocumento
from app.models.postulacion import Postulacion
from app.models.soporte import SolicitudCuenta
from app.models.usuario import Usuario
from app.schemas.admin_gestion import AdminResolverSolicitud
from app.schemas.ofrecimiento import (
    MensajeInput,
    OfrecimientoCreate,
    SolicitudInteresCreate,
)
from app.schemas.organizacion import PerfilPublicoUpdate, ResenaCreate
from app.schemas.perfil import FundacionPerfilInput
from app.schemas.postulacion import (
    ConfirmarAsistencia,
    PostulacionCreate,
    PostulacionResponder,
)
from app.schemas.programacion import ProgramacionCreate
from app.schemas.publicacion import PublicacionCreate, PublicacionUpdate
from app.services.admin_gestion_service import AdminGestionService
from app.services.admin_service import AdminService
from app.services.cuenta_service import CuentaService
from app.services.habilidad_service import HabilidadService
from app.services.ofrecimiento_service import OfrecimientoService
from app.services.organizacion_service import OrganizacionService
from app.services.perfil_service import PerfilService
from app.services.postulacion_service import PostulacionService
from app.services.programacion_service import ProgramacionService
from app.services.publicacion_service import PublicacionService
from app.services.soporte_service import SoporteService
from tests.integration.conftest import _usuario


async def _participar(db, f, pub, v, calificacion: int = 5) -> Postulacion:
    """Postula, acepta y confirma asistencia (participación verificada)."""
    svc = PostulacionService(db)
    p = await svc.postular(v, PostulacionCreate(publicacion_id=pub.id))
    await svc.responder(p.id, f, PostulacionResponder(estado="ACEPTADO"))
    return await svc.confirmar_asistencia(
        p.id, f, ConfirmarAsistencia(asistio=True, calificacion=calificacion)
    )


async def _acciones(db, admin: Usuario) -> list[str]:
    """Tipos de acción auditados para un administrador (la auditoría usa su perfil)."""
    filas = await db.execute(
        select(AdminAccion.tipo)
        .join(AdminPerfil, AdminPerfil.id == AdminAccion.admin_id)
        .where(AdminPerfil.usuario_id == admin.id)
    )
    return [t for (t,) in filas.all()]


async def _contar_notif(db, usuario_id, tipo: str) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Notificacion).where(
                Notificacion.usuario_id == usuario_id, Notificacion.tipo == tipo
            )
        )
    ).scalar_one()


# ═════════════════ Postulaciones: cupos, lista de espera, retiro, historial ═════════════════


async def test_r5_r7_r8_cupos_lista_espera_retiro_e_historial(
    db, crear_fundacion, crear_voluntario, crear_publicacion
):
    f = await crear_fundacion()
    pub = await crear_publicacion(f, cupo=1)
    v1, v2, v3 = [await crear_voluntario() for _ in range(3)]
    svc = PostulacionService(db)

    p1 = await svc.postular(v1, PostulacionCreate(publicacion_id=pub.id))
    p2 = await svc.postular(v2, PostulacionCreate(publicacion_id=pub.id))
    # R5: las postulaciones pendientes NO ocupan cupo.
    assert p1.estado == p2.estado == "PENDIENTE"

    await svc.responder(p1.id, f, PostulacionResponder(estado="ACEPTADO"))
    # R5: nunca se asignan más cupos de los disponibles.
    with pytest.raises(ConflictError):
        await svc.responder(p2.id, f, PostulacionResponder(estado="ACEPTADO"))

    # Con el cupo lleno, una nueva postulación entra en lista de espera.
    p3 = await svc.postular(v3, PostulacionCreate(publicacion_id=pub.id))
    assert p3.estado == "LISTA_ESPERA"

    # R7: retirarse siendo aceptado exige confirmación previa.
    with pytest.raises(ConflictError):
        await svc.retirar(p1.id, v1)
    retirada = await svc.retirar(p1.id, v1, confirmar=True)
    assert retirada.estado == "RETIRADO"

    # El retiro libera el cupo: ahora sí se puede aceptar a quien esperaba.
    aceptada = await svc.responder(p3.id, f, PostulacionResponder(estado="ACEPTADO"))
    assert aceptada.estado == "ACEPTADO"

    # R8: cada cambio queda registrado con quién lo hizo.
    historial = await svc.historial(p1.id, v1._usuario)
    pasos = [(h.estado_anterior, h.estado_nuevo, h.rol_actor) for h in historial]
    assert pasos == [
        (None, "PENDIENTE", "VOLUNTARIO"),
        ("PENDIENTE", "ACEPTADO", "FUNDACION"),
        ("ACEPTADO", "RETIRADO", "VOLUNTARIO"),
    ]
    # Un usuario ajeno no puede consultar el historial.
    with pytest.raises(Exception):  # noqa: B017,PT011 - NotFoundError
        await svc.historial(p1.id, v2._usuario)


async def test_no_permite_postulacion_duplicada_ni_fuera_de_edad(
    db, crear_fundacion, crear_voluntario, crear_publicacion
):
    f = await crear_fundacion()
    pub = await crear_publicacion(f, cupo=3)
    v = await crear_voluntario()
    svc = PostulacionService(db)
    await svc.postular(v, PostulacionCreate(publicacion_id=pub.id))
    with pytest.raises(ConflictError):
        await svc.postular(v, PostulacionCreate(publicacion_id=pub.id))

    exigente = await crear_publicacion(f, cupo=3)
    exigente.edad_minima = 80
    await db.commit()
    with pytest.raises(ConflictError):
        await svc.postular(v, PostulacionCreate(publicacion_id=exigente.id))


async def test_notificaciones_respetan_preferencias(
    db, crear_fundacion, crear_voluntario, crear_publicacion
):
    f = await crear_fundacion()
    pub = await crear_publicacion(f, cupo=2)
    con_aviso, sin_aviso = await crear_voluntario(), await crear_voluntario()
    await CuentaService(db).guardar_preferencias(
        sin_aviso.usuario_id, {"notif_postulaciones": False}
    )
    svc = PostulacionService(db)
    for v in (con_aviso, sin_aviso):
        p = await svc.postular(v, PostulacionCreate(publicacion_id=pub.id))
        await svc.responder(p.id, f, PostulacionResponder(estado="ACEPTADO"))
    assert await _contar_notif(db, con_aviso.usuario_id, "POSTULACION_ACEPTADA") == 1
    assert await _contar_notif(db, sin_aviso.usuario_id, "POSTULACION_ACEPTADA") == 0


# ═════════════════ Gamificación ═════════════════


async def test_xp_solo_por_asistencia_50_mas_5_por_hora_sin_bono_de_logro(
    db, crear_fundacion, crear_voluntario, crear_publicacion
):
    f = await crear_fundacion()
    pub = await crear_publicacion(f, cupo=2, horas=3)
    v = await crear_voluntario()
    await _participar(db, f, pub, v)

    puntos = await db.get(VoluntarioPuntos, v.id)
    assert puntos.total_historico == 65  # 50 + 3 h x 5, sin bono por logro (sección 4.9)
    assert v.actividades_completadas == 1 and v.horas_acumuladas == 3
    logros = (
        await db.execute(
            select(func.count()).select_from(VoluntarioLogro).where(VoluntarioLogro.voluntario_id == v.id)
        )
    ).scalar_one()
    assert logros >= 1  # "Primer paso" desbloqueado, pero no suma XP

    # No asistir no otorga XP y una asistencia ya registrada no se puede repetir.
    pub2 = await crear_publicacion(f, cupo=2, horas=5)
    svc = PostulacionService(db)
    p = await svc.postular(v, PostulacionCreate(publicacion_id=pub2.id))
    await svc.responder(p.id, f, PostulacionResponder(estado="ACEPTADO"))
    await svc.confirmar_asistencia(p.id, f, ConfirmarAsistencia(asistio=False))
    assert (await db.get(VoluntarioPuntos, v.id)).total_historico == 65
    with pytest.raises(ConflictError):
        await svc.confirmar_asistencia(
            p.id, f, ConfirmarAsistencia(asistio=True, calificacion=5)
        )


# ═════════════════ Habilidades y coincidencia (sección 4.4) ═════════════════


async def test_r3_voluntario_entre_3_y_10_habilidades(db, crear_voluntario, catalogos):
    v = await crear_voluntario()
    ids = catalogos["habilidades"]
    svc = HabilidadService(db)
    with pytest.raises(AppError):
        await svc.guardar_de_voluntario(v.id, ids[:2])
    with pytest.raises(AppError):
        await svc.guardar_de_voluntario(v.id, ids[:11])
    assert sorted(await svc.guardar_de_voluntario(v.id, ids[:3])) == sorted(ids[:3])
    assert sorted(await svc.ids_de_voluntario(v.id)) == sorted(ids[:3])


async def test_r2_la_coincidencia_ordena_pero_no_excluye(
    db, crear_fundacion, crear_voluntario, crear_publicacion, catalogos
):
    f = await crear_fundacion()
    v = await crear_voluntario()
    h = catalogos["habilidades"]
    await HabilidadService(db).guardar_de_voluntario(v.id, h[:3])
    token = uuid.uuid4().hex[:10]
    # La poco compatible empieza ANTES; aun así la compatible debe aparecer primero.
    poco = await crear_publicacion(f, titulo=f"{token} poco", habilidades=h[6:9], dias=5)
    mucho = await crear_publicacion(f, titulo=f"{token} mucho", habilidades=h[:3], dias=20)

    res = await PublicacionService(db).listar_publicas(
        categoria_id=None, modalidad=None, municipio_id=None, buscar=token,
        page=1, per_page=10, voluntario_id=v.id,
    )
    assert [p.id for p in res.data] == [mucho.id, poco.id]
    assert [p.coincidencia for p in res.data] == [100, 0]
    assert res.total == 2  # la de 0 % NO se excluye


async def test_publicar_exige_entre_3_y_10_habilidades(db, crear_fundacion, catalogos):
    f = await crear_fundacion()
    svc = PublicacionService(db)
    base = dict(
        titulo="Jornada de siembra", descripcion="Sembraremos árboles juntos.",
        categoria_id=catalogos["area"], modalidad="PRESENCIAL",
        municipio_id=catalogos["municipio"], fecha_inicio=date.today() + timedelta(days=9),
        fecha_fin=date.today() + timedelta(days=9), cupo_maximo=5,
    )
    pub = await svc.crear(f.id, PublicacionCreate(**base, habilidades=catalogos["habilidades"][:2]))
    with pytest.raises(ConflictError):
        await svc.publicar(pub.id, f.id)
    await svc.actualizar(
        pub.id, f.id, PublicacionUpdate(habilidades=catalogos["habilidades"][:3])
    )
    assert (await svc.publicar(pub.id, f.id)).estado == "PUBLICADA"


# ═════════════════ Actividades recurrentes (R4) ═════════════════


async def test_r4_recurrente_genera_tres_y_se_pausa_hasta_autorizar(
    db, crear_fundacion, catalogos
):
    f = await crear_fundacion()
    inicio = date.today() + timedelta(days=5)
    svc = ProgramacionService(db)
    out = await svc.crear(
        f,
        ProgramacionCreate(
            unidad_intervalo="DIAS", intervalo=3, fecha_inicio=inicio, cupo_maximo=4,
            plantilla=dict(
                titulo="Limpieza del refugio", descripcion="Limpieza general del refugio.",
                categoria_id=catalogos["area"], modalidad="PRESENCIAL",
                municipio_id=catalogos["municipio"], habilidades=catalogos["habilidades"][:3],
            ),
        ),
    )
    # Genera exactamente tres convocatorias cada 3 días y queda en pausa.
    assert out.estado == "PAUSADA" and out.total_generadas == 3
    assert [c.fecha_inicio for c in out.convocatorias] == [
        inicio, inicio + timedelta(days=3), inicio + timedelta(days=6),
    ]
    assert all(c.estado == "PUBLICADA" for c in out.convocatorias)
    assert out.proxima_fecha == inicio + timedelta(days=9)  # la 4.ª NO se generó sola
    assert await _contar_notif(db, f.usuario_id, "PROGRAMACION_PAUSADA") == 1

    # Solo con autorización explícita se genera el siguiente ciclo (otras 3).
    out2 = await svc.autorizar(out.id, f)
    assert out2.total_generadas == 6 and len(out2.convocatorias) == 6
    assert out2.estado == "PAUSADA"

    # Si rechaza, la programación termina y ya no se puede continuar.
    fin = await svc.finalizar(out.id, f)
    assert fin.estado == "TERMINADA"
    with pytest.raises(ConflictError):
        await svc.autorizar(out.id, f)


# ═════════════════ Objetos y servicios (R1, R9) ═════════════════


def _objeto(catalogos, cantidad: int = 5, titulo: str | None = None) -> OfrecimientoCreate:
    return OfrecimientoCreate(
        tipo="OBJETO", titulo=titulo or f"Libros {uuid.uuid4().hex[:6]}",
        descripcion="Libros infantiles en buen estado, sin costo.",
        categoria="Libros y material educativo", cantidad_total=cantidad,
        estado_producto="USADO_BUEN_ESTADO", modalidad_entrega="A_CONVENIR",
        municipio_id=catalogos["municipio"],
    )


async def test_cantidades_se_controlan_y_la_entrega_requiere_ambas_confirmaciones(
    db, crear_voluntario, crear_fundacion, catalogos
):
    v = await crear_voluntario()
    f1, f2, f3 = [await crear_fundacion() for _ in range(3)]
    svc = OfrecimientoService(db)
    of = await svc.crear(v, _objeto(catalogos, 5))

    s1 = await svc.solicitar(f1, of.id, SolicitudInteresCreate(cantidad=3))
    s2 = await svc.solicitar(f2, of.id, SolicitudInteresCreate(cantidad=2))
    s3 = await svc.solicitar(f3, of.id, SolicitudInteresCreate(cantidad=1))
    await svc.responder(v._usuario, s1.id, "ACEPTAR")  # 3 de 5
    await svc.responder(v._usuario, s2.id, "ACEPTAR")  # 2 de 5 -> 0 disponibles
    with pytest.raises(ConflictError):  # nunca se excede lo ofrecido
        await svc.responder(v._usuario, s3.id, "ACEPTAR")
    assert (await svc.detalle(of.id, v.id)).cantidad_disponible == 0
    assert (await svc.detalle(of.id, v.id)).estado == "RESERVADO"

    # R9: se completa solo cuando AMBAS partes confirman.
    uno = await svc.confirmar(v._usuario, s1.id)
    assert uno.estado == "ACEPTADA"
    with pytest.raises(ConflictError):
        await svc.confirmar(v._usuario, s1.id)  # no vale confirmar dos veces
    assert (await svc.confirmar(f1._usuario, s1.id)).estado == "COMPLETADA"
    await svc.confirmar(v._usuario, s2.id)
    await svc.confirmar(f2._usuario, s2.id)
    assert (await svc.detalle(of.id, v.id)).estado == "ENTREGADO"


async def test_cancelar_libera_la_cantidad_reservada(db, crear_voluntario, crear_fundacion, catalogos):
    v, f = await crear_voluntario(), await crear_fundacion()
    svc = OfrecimientoService(db)
    of = await svc.crear(v, _objeto(catalogos, 4))
    s = await svc.solicitar(f, of.id, SolicitudInteresCreate(cantidad=4))
    await svc.responder(v._usuario, s.id, "ACEPTAR")
    assert (await svc.detalle(of.id, v.id)).cantidad_disponible == 0
    await svc.cancelar(f._usuario, s.id)
    asi = await svc.detalle(of.id, v.id)
    assert asi.cantidad_disponible == 4 and asi.estado == "DISPONIBLE"


async def test_mensajeria_no_expone_datos_personales(db, crear_voluntario, crear_fundacion, catalogos):
    v, f = await crear_voluntario(), await crear_fundacion()
    svc = OfrecimientoService(db)
    of = await svc.crear(v, _objeto(catalogos, 1))
    s = await svc.solicitar(f, of.id, SolicitudInteresCreate(cantidad=1))
    await svc.responder(v._usuario, s.id, "ACEPTAR")
    with pytest.raises(AppError):
        await svc.enviar_mensaje(f._usuario, s.id, MensajeInput(mensaje="llámame al 300 123 4567"))
    msgs = await svc.enviar_mensaje(f._usuario, s.id, MensajeInput(mensaje="¿Cuándo podemos recogerlos?"))
    assert len(msgs) == 1 and msgs[0].es_mio and msgs[0].autor_rol == "FUNDACION"
    # Coordinar cambia el estado a "en coordinación"; el voluntario ve solo el nombre de la org.
    assert (await svc.mis_solicitudes(v._usuario))[0].estado == "EN_COORDINACION"
    vista_vol = await svc.mensajes(v._usuario, s.id)
    assert vista_vol[0].autor_nombre == f.nombre and not vista_vol[0].es_mio
    # Un tercero no puede leer la conversación.
    otro = await crear_voluntario()
    with pytest.raises(Exception):  # noqa: B017,PT011 - NotFoundError
        await svc.mensajes(otro._usuario, s.id)


# ═════════════════ Perfil público, verificación y reseñas ═════════════════


async def test_perfil_publico_respeta_privacidad_de_contacto(db, crear_fundacion, catalogos):
    f = await crear_fundacion()
    svc = OrganizacionService(db)
    pub = await svc.perfil_publico(f.id, None)
    assert pub.contacto.telefono is None and pub.contacto.direccion is None
    assert pub.verificacion.verificada is False

    await svc.actualizar_perfil_publico(
        f, PerfilPublicoUpdate(mostrar_telefono=True, historia="Nacimos en 2020.", areas=[catalogos["area"]])
    )
    pub = await svc.perfil_publico(f.id, None)
    assert pub.contacto.telefono == "3001234567" and pub.contacto.direccion is None
    assert pub.historia == "Nacimos en 2020." and len(pub.areas) == 1
    # Galería: sin autorización de imagen no se sube nada.
    with pytest.raises(AppError):
        await svc.subir_galeria(f, None, None, True, False)  # type: ignore[arg-type]


async def test_verificacion_documental_flujo_completo_con_auditoria(
    db, crear_fundacion, crear_admin
):
    f, admin = await crear_fundacion(), await crear_admin()
    org = OrganizacionService(db)
    gestion = AdminGestionService(db)

    with pytest.raises(ConflictError):  # sin documentos no se puede solicitar
        await org.solicitar_verificacion(f)
    db.add(
        FundacionDocumento(
            fundacion_id=f.id, tipo_documento="RUT", nombre_original="rut.pdf",
            ruta_archivo="/archivos/privado/verificacion/no-existe.pdf",
        )
    )
    await db.commit()
    assert (await org.solicitar_verificacion(f)).estado == "EN_REVISION"

    with pytest.raises(AppError):  # pedir información exige una nota
        await gestion.resolver_verificacion(admin, f.id, "PEDIR_INFO", None)
    await gestion.resolver_verificacion(admin, f.id, "APROBAR", None)
    perfil = await org.perfil_publico(f.id, None)
    assert perfil.verificacion.verificada is True
    assert "garantía" in perfil.verificacion.aviso  # no se presenta como garantía absoluta

    await gestion.resolver_verificacion(admin, f.id, "REVOCAR", "Documento vencido")
    assert (await org.perfil_publico(f.id, None)).verificacion.verificada is False
    assert await _contar_notif(db, f.usuario_id, "VERIFICACION_ACTUALIZADA") == 2
    assert (await _acciones(db, admin)).count("VERIFICACION_DOCUMENTAL_RESUELTA") == 2


async def test_r12_resenas_solo_con_participacion_confirmada_y_moderacion(
    db, crear_fundacion, crear_voluntario, crear_publicacion, crear_admin
):
    f, admin = await crear_fundacion(), await crear_admin()
    pub = await crear_publicacion(f, cupo=5)
    participante, ofensivo, ajeno = [await crear_voluntario() for _ in range(3)]
    await _participar(db, f, pub, participante)
    await _participar(db, f, pub, ofensivo)
    org = OrganizacionService(db)

    with pytest.raises(ForbiddenError):  # sin participación confirmada
        await org.crear_resena(ajeno, f.id, ResenaCreate(calificacion=5, comentario="Muy buena organización"))
    ok = await org.crear_resena(participante, f.id, ResenaCreate(calificacion=4, comentario="Muy buena organización"))
    assert ok.estado == "VISIBLE"
    with pytest.raises(ConflictError):  # una por voluntario y organización
        await org.crear_resena(participante, f.id, ResenaCreate(calificacion=5, comentario="Otra reseña distinta"))

    # Un comentario con datos personales queda retenido hasta que un admin lo revise.
    retenida = await org.crear_resena(
        ofensivo, f.id, ResenaCreate(calificacion=1, comentario="Escríbeme al 3001234567 por favor")
    )
    assert retenida.estado == "PENDIENTE_MODERACION"
    publicas = await org.listar_resenas(f.id, 1, 10)
    assert publicas.total == 1 and publicas.resumen.promedio == 4.0

    await AdminGestionService(db).moderar_resena(admin, retenida.id, "OCULTAR", "Datos personales")
    assert (await org.listar_resenas(f.id, 1, 10)).total == 1  # ocultada: no se publica
    # La organización puede responder una reseña publicada.
    r = await org.responder_resena(f, ok.id, "¡Gracias por participar!")
    assert r.respuesta == "¡Gracias por participar!"


async def test_r11_estadisticas_distinguen_publicadas_de_realizadas(
    db, crear_fundacion, crear_voluntario, crear_publicacion
):
    f = await crear_fundacion()
    realizada = await crear_publicacion(f, cupo=2)
    await crear_publicacion(f, cupo=2)  # publicada pero sin participaciones
    v = await crear_voluntario()
    await _participar(db, f, realizada, v)
    est = await OrganizacionService(db).estadisticas(f)
    assert est.convocatorias_creadas == 2
    assert est.individuales_realizadas == 1  # no se confunde publicada con realizada
    assert est.participaciones_confirmadas == 1 and est.voluntarios_participantes == 1


async def test_r13_organizacion_sin_constitucion_legal_puede_registrarse(db, catalogos):
    base = dict(
        nombre_fundacion="Refugio Patitas", representante_legal="Ana Pérez",
        telefono_contacto="3001234567", direccion="Calle 1 # 2-3",
        municipio_id=catalogos["municipio"], descripcion="Refugio independiente de animales.",
        tipo_organizacion="REFUGIO", constituida_legalmente=False,
    )
    for _ in range(2):  # dos sin NIT: el NIT nulo no choca con la restricción de unicidad
        u = await _usuario(db, "FUNDACION")
        out = await PerfilService(db).guardar_fundacion(u, FundacionPerfilInput(**base))
        assert out.nit is None and out.constituida_legalmente is False


# ═════════════════ Administración: soporte, privacidad y auditoría ═════════════════


async def test_admin_responde_ticket_notifica_y_audita(db, crear_voluntario, crear_admin):
    v, admin = await crear_voluntario(), await crear_admin()
    ticket = await SoporteService(db).crear_ticket(
        v.usuario_id, "PROBLEMAS_ACCESO", "No puedo entrar", "No me llega el correo de acceso.", None
    )
    out = await AdminGestionService(db).responder_ticket(admin, ticket.id, "Ya revisamos tu cuenta.", "RESUELTO")
    assert out.estado == "RESUELTO" and out.mensajes[-1].es_admin
    assert await _contar_notif(db, v.usuario_id, "RESPUESTA_SOPORTE") == 1
    assert (await _acciones(db, admin)).count("SOPORTE_RESPONDIDO") == 1


async def test_solicitud_de_eliminacion_no_se_ejecuta_sin_controles_y_conserva_registros(
    db, crear_voluntario, crear_fundacion, crear_publicacion, crear_admin
):
    f, admin, v = await crear_fundacion(), await crear_admin(), await crear_voluntario()
    pub = await crear_publicacion(f, cupo=2)
    post = await PostulacionService(db).postular(v, PostulacionCreate(publicacion_id=pub.id))
    email_original = v._usuario.email
    sol = await SoporteService(db).crear_solicitud(v.usuario_id, "ELIMINACION_DATOS", "Habeas data")
    gestion = AdminGestionService(db)

    # Aprobar NO ejecuta nada por sí solo.
    await gestion.resolver_solicitud(admin, sol.id, AdminResolverSolicitud(decision="APROBAR", respuesta="Procede."))
    assert (await db.get(Usuario, v.usuario_id)).email == email_original
    # Ejecutar sin aprobar, o sin respuesta, se rechaza.
    with pytest.raises(AppError):
        await gestion.resolver_solicitud(admin, sol.id, AdminResolverSolicitud(decision="EN_PROCESO", ejecutar=True))
    # Ejecución explícita: anonimiza datos personales y conserva postulaciones.
    out = await gestion.resolver_solicitud(
        admin, sol.id, AdminResolverSolicitud(decision="APROBAR", respuesta="Anonimizado.", ejecutar=True)
    )
    assert out.estado == "COMPLETADA"
    usuario = await db.get(Usuario, v.usuario_id)
    assert usuario.email != email_original and usuario.nombre == "Usuario anonimizado"
    assert usuario.estado == "BLOQUEADO"
    assert v.numero_documento.startswith("ANON-")
    assert await db.get(Postulacion, post.id) is not None  # registro conservado
    acciones = await _acciones(db, admin)
    assert acciones.count("USUARIO_ANONIMIZADO") == 1
    assert acciones.count("SOLICITUD_CUENTA_RESUELTA") == 2  # aprobada y luego ejecutada


async def test_admin_no_resuelve_solicitudes_propias(db, crear_admin):
    admin = await crear_admin()
    sol = SolicitudCuenta(usuario_id=admin.id, tipo="BLOQUEO_TEMPORAL", motivo="prueba")
    db.add(sol)
    await db.commit()
    with pytest.raises(ForbiddenError):
        await AdminGestionService(db).resolver_solicitud(
            admin, sol.id, AdminResolverSolicitud(decision="RECHAZAR", respuesta="No")
        )


async def test_panel_admin_deja_rastro_de_auditoria(db, crear_voluntario, crear_admin):
    v, admin = await crear_voluntario(), await crear_admin()
    svc = AdminService(db)
    await svc.cambiar_estado_usuario(admin.id, str(v.usuario_id), "SUSPENDIDO", "Prueba")
    await svc.cambiar_estado_usuario(admin.id, str(v.usuario_id), "ACTIVO", None)
    assert {"USUARIO_SUSPENDIDO", "USUARIO_REACTIVADO"} <= set(await _acciones(db, admin))


# ═════════════════ HTTP: archivos privados (R10) ═════════════════


@pytest_asyncio.fixture
async def http(maker):
    from app.db.session import get_db
    from app.main import create_app

    app = create_app()

    async def _db():
        async with maker() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = _db
    app.state.limiter.enabled = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _bearer(usuario: Usuario) -> dict[str, str]:
    token, _ = create_access_token(
        get_settings(), subject=str(usuario.id), rol=usuario.rol, estado=usuario.estado
    )
    return {"Authorization": f"Bearer {token}"}


async def test_r10_documentos_privados_solo_para_el_dueno_y_admin(
    db, http, crear_voluntario, crear_admin
):
    settings = get_settings()
    dueno, otro, admin = await crear_voluntario(), await crear_voluntario(), await crear_admin()
    nombre = f"{uuid.uuid4().hex}.pdf"
    carpeta = Path(settings.private_upload_dir) / "documentos"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / nombre
    archivo.write_bytes(b"%PDF-1.4 prueba")
    publico = Path(settings.upload_dir) / "documentos"
    publico.mkdir(parents=True, exist_ok=True)
    legado = publico / nombre
    legado.write_bytes(b"%PDF-1.4 legado")
    try:
        dueno.documento_identidad = f"/archivos/privado/documentos/{nombre}"
        await db.commit()
        url = f"/api/v1/archivos/privado/documentos/{nombre}"

        assert (await http.get(url)).status_code == 401  # sin sesión
        assert (await http.get(url, headers=_bearer(otro._usuario))).status_code == 404  # ajeno
        assert (await http.get(url, headers=_bearer(dueno._usuario))).status_code == 200
        assert (await http.get(url, headers=_bearer(admin))).status_code == 200
        # La ruta estática pública ya no sirve documentos, ni siquiera los antiguos.
        assert (await http.get(f"/uploads/documentos/{nombre}")).status_code == 404
        # Intento de salirse de la carpeta.
        assert (await http.get("/api/v1/archivos/privado/documentos/..%2F..%2F.env",
                               headers=_bearer(admin))).status_code == 404
    finally:
        archivo.unlink(missing_ok=True)
        legado.unlink(missing_ok=True)
