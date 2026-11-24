--
-- PostgreSQL database dump
--


-- Dumped from database version 18.2
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: dificultad_tipo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.dificultad_tipo AS ENUM (
    'FACIL',
    'MEDIA',
    'DIFICIL',
    'MUY_DIFICIL'
);


--
-- Name: disponibilidad_tipo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.disponibilidad_tipo AS ENUM (
    'ENTRE_SEMANA',
    'FINES_DE_SEMANA',
    'FLEXIBLE'
);


--
-- Name: estado_postulacion; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estado_postulacion AS ENUM (
    'PENDIENTE',
    'ACEPTADO',
    'RECHAZADO',
    'RETIRADO',
    'ASISTIO',
    'NO_ASISTIO',
    'EN_REVISION',
    'LISTA_ESPERA',
    'CANCELADO_FUNDACION'
);


--
-- Name: estado_publicacion; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estado_publicacion AS ENUM (
    'BORRADOR',
    'PENDIENTE_APROBACION',
    'PUBLICADA',
    'CERRADA',
    'CANCELADA',
    'COMPLETADA',
    'FINALIZADA'
);


--
-- Name: estado_reporte; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estado_reporte AS ENUM (
    'PENDIENTE',
    'EN_REVISION',
    'RESUELTO',
    'DESESTIMADO'
);


--
-- Name: estado_usuario; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estado_usuario AS ENUM (
    'ACTIVO',
    'BLOQUEADO',
    'SUSPENDIDO'
);


--
-- Name: estado_verificacion; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estado_verificacion AS ENUM (
    'PENDIENTE',
    'APROBADA',
    'RECHAZADA',
    'SUSPENDIDA'
);


--
-- Name: genero_tipo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.genero_tipo AS ENUM (
    'MASCULINO',
    'FEMENINO',
    'OTRO'
);


--
-- Name: modalidad_tipo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.modalidad_tipo AS ENUM (
    'PRESENCIAL',
    'VIRTUAL',
    'HIBRIDA'
);


--
-- Name: motivo_reporte; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.motivo_reporte AS ENUM (
    'INFORMACION_FALSA',
    'CONTENIDO_INAPROPIADO',
    'ACTIVIDAD_SOSPECHOSA',
    'PERFIL_SOSPECHOSO',
    'OTRO'
);


--
-- Name: nivel_admin; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.nivel_admin AS ENUM (
    'SUPER',
    'OPERATIVO'
);


--
-- Name: proveedor_auth; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.proveedor_auth AS ENUM (
    'LOCAL',
    'GOOGLE'
);


--
-- Name: rol_usuario; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rol_usuario AS ENUM (
    'VOLUNTARIO',
    'FUNDACION',
    'ADMIN'
);


--
-- Name: tipo_accion_admin; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_accion_admin AS ENUM (
    'USUARIO_SUSPENDIDO',
    'USUARIO_BLOQUEADO',
    'USUARIO_REACTIVADO',
    'USUARIO_ELIMINADO',
    'USUARIO_EDITADO',
    'FUNDACION_APROBADA',
    'FUNDACION_RECHAZADA',
    'FUNDACION_SUSPENDIDA',
    'FUNDACION_REACTIVADA',
    'PUBLICACION_OCULTADA',
    'PUBLICACION_RESTAURADA',
    'PUBLICACION_ELIMINADA',
    'PUBLICACION_ESTADO_CAMBIADO',
    'POSTULACION_INTERVENIDA',
    'REPORTE_RESUELTO',
    'REPORTE_DESESTIMADO',
    'PUNTOS_AJUSTADOS',
    'LOGRO_ASIGNADO',
    'ADMIN_CREADO',
    'ADMIN_DESACTIVADO',
    'ADMIN_PERMISOS_ACTUALIZADOS',
    'SOPORTE_RESPONDIDO',
    'SOLICITUD_CUENTA_RESUELTA',
    'USUARIO_ANONIMIZADO',
    'VERIFICACION_DOCUMENTAL_RESUELTA',
    'RESENA_MODERADA',
    'VOLUNTARIO_VERIFICADO',
    'CATALOGO_MODIFICADO',
    'AUTORIZACION_MENOR_RESUELTA'
);


--
-- Name: tipo_documento; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_documento AS ENUM (
    'CC',
    'TI',
    'CE',
    'PASAPORTE'
);


--
-- Name: tipo_notificacion; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_notificacion AS ENUM (
    'NUEVA_POSTULACION',
    'POSTULACION_RETIRADA',
    'VOLUNTARIO_ASISTIO',
    'VOLUNTARIO_NO_ASISTIO',
    'POSTULACION_ACEPTADA',
    'POSTULACION_RECHAZADA',
    'ACTIVIDAD_CANCELADA',
    'ACTIVIDAD_MODIFICADA',
    'FUNDACION_APROBADA',
    'FUNDACION_RECHAZADA',
    'FUNDACION_SUSPENDIDA',
    'FUNDACION_REACTIVADA',
    'RECORDATORIO_ACTIVIDAD',
    'NUEVA_CONVOCATORIA_COMPATIBLE',
    'LOGRO_DESBLOQUEADO',
    'XP_OBTENIDO',
    'RESPUESTA_SOPORTE',
    'CUENTA_ACTUALIZADA',
    'NUEVO_MENSAJE',
    'INTERES_RECIBIDO',
    'INTERES_ACTUALIZADO',
    'PROGRAMACION_PAUSADA',
    'VERIFICACION_ACTUALIZADA',
    'NUEVA_RESENA',
    'RESENA_RESPONDIDA',
    'POSTULACION_ACTUALIZADA'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_acciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_acciones (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    admin_id uuid NOT NULL,
    tipo public.tipo_accion_admin NOT NULL,
    objeto_tipo character varying(30),
    objeto_id uuid,
    objeto_descripcion text,
    detalle_anterior jsonb,
    detalle_nuevo jsonb,
    motivo text,
    fecha_accion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: admin_perfiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_perfiles (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    nivel public.nivel_admin DEFAULT 'OPERATIVO'::public.nivel_admin NOT NULL,
    permisos jsonb,
    creado_por uuid,
    activo boolean DEFAULT true NOT NULL,
    cargo character varying(100),
    notas_internas text,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: advertencias_voluntario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.advertencias_voluntario (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    voluntario_id uuid NOT NULL,
    admin_id uuid NOT NULL,
    motivo text NOT NULL,
    activa boolean DEFAULT true NOT NULL,
    fecha timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: areas_impacto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.areas_impacto (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: areas_impacto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.areas_impacto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: areas_impacto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.areas_impacto_id_seq OWNED BY public.areas_impacto.id;


--
-- Name: auditoria_perfil; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auditoria_perfil (
    id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    campo character varying(60) NOT NULL,
    valor_anterior text,
    valor_nuevo text,
    realizado_por uuid,
    ip character varying(50),
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: configuracion_sistema; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuracion_sistema (
    clave character varying(100) NOT NULL,
    valor_texto text,
    valor_int integer,
    valor_decimal numeric(10,4),
    valor_bool boolean,
    descripcion text NOT NULL,
    modulo character varying(50) NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: departamentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.departamentos (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: departamentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.departamentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: departamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.departamentos_id_seq OWNED BY public.departamentos.id;


--
-- Name: documento_legal_versiones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_legal_versiones (
    id integer NOT NULL,
    documento_id integer NOT NULL,
    version character varying(40) NOT NULL,
    contenido text,
    contenido_hash character varying(64),
    url_publica character varying(500),
    vigente boolean DEFAULT false NOT NULL,
    fecha_publicacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: documento_legal_versiones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_legal_versiones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_legal_versiones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_legal_versiones_id_seq OWNED BY public.documento_legal_versiones.id;


--
-- Name: documentos_legales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos_legales (
    id integer NOT NULL,
    codigo character varying(60) NOT NULL,
    nombre character varying(150) NOT NULL,
    descripcion text,
    requerido_registro boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: documentos_legales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_legales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentos_legales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentos_legales_id_seq OWNED BY public.documentos_legales.id;


--
-- Name: fundacion_areas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fundacion_areas (
    fundacion_id uuid NOT NULL,
    area_id integer NOT NULL
);


--
-- Name: fundacion_documentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fundacion_documentos (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    tipo_documento character varying(60) NOT NULL,
    nombre_original character varying(300) NOT NULL,
    ruta_archivo text NOT NULL,
    validado boolean DEFAULT false NOT NULL,
    fecha_subida timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: fundacion_galeria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fundacion_galeria (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    ruta character varying(500) NOT NULL,
    descripcion character varying(200),
    contiene_menores boolean DEFAULT false NOT NULL,
    autorizacion_imagen boolean DEFAULT false NOT NULL,
    orden smallint DEFAULT '0'::smallint NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: fundaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fundaciones (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    nombre character varying(150) NOT NULL,
    nit character varying(20),
    representante_legal character varying(150) NOT NULL,
    correo_institucional character varying(150),
    telefono character varying(20) NOT NULL,
    direccion character varying(200) NOT NULL,
    municipio_id integer NOT NULL,
    pagina_web character varying(255),
    descripcion text NOT NULL,
    documento_legal text,
    logo character varying(500),
    estado_verificacion public.estado_verificacion DEFAULT 'PENDIENTE'::public.estado_verificacion NOT NULL,
    fecha_verificacion timestamp(0) without time zone,
    motivo_rechazo text,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tipo_organizacion character varying(30) DEFAULT 'FUNDACION'::character varying NOT NULL,
    constituida_legalmente boolean DEFAULT true NOT NULL,
    historia text,
    mision text,
    mostrar_telefono boolean DEFAULT false NOT NULL,
    mostrar_correo boolean DEFAULT false NOT NULL,
    mostrar_direccion boolean DEFAULT false NOT NULL,
    verificacion_documental character varying(30) DEFAULT 'NO_SOLICITADA'::character varying NOT NULL,
    verificacion_documental_fecha timestamp without time zone,
    verificacion_documental_nota text,
    verificacion_documental_por uuid,
    CONSTRAINT chk_correo_si_aprobada CHECK (((estado_verificacion <> 'APROBADA'::public.estado_verificacion) OR (correo_institucional IS NOT NULL))),
    CONSTRAINT chk_nit_formato CHECK (((nit)::text ~ '^\d{7,10}-\d$'::text))
);


--
-- Name: habilidades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.habilidades (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    categoria character varying(60),
    es_profesional boolean DEFAULT false NOT NULL
);


--
-- Name: habilidades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.habilidades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: habilidades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.habilidades_id_seq OWNED BY public.habilidades.id;


--
-- Name: historial_estados_fundacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.historial_estados_fundacion (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    estado_anterior character varying(20) NOT NULL,
    estado_nuevo character varying(20) NOT NULL,
    motivo text,
    admin_id uuid NOT NULL,
    fecha timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: historial_estados_voluntario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.historial_estados_voluntario (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    estado_anterior character varying(20) NOT NULL,
    estado_nuevo character varying(20) NOT NULL,
    motivo text,
    duracion_dias integer,
    admin_id uuid NOT NULL,
    fecha timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: intereses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intereses (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: intereses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intereses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intereses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intereses_id_seq OWNED BY public.intereses.id;


--
-- Name: logros; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.logros (
    id integer NOT NULL,
    codigo character varying(50) NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text NOT NULL,
    icono character varying(10) DEFAULT '🏆'::character varying NOT NULL,
    tipo character varying(30) NOT NULL,
    umbral integer DEFAULT 0 NOT NULL,
    activo boolean DEFAULT true NOT NULL
);


--
-- Name: logros_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.logros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: logros_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.logros_id_seq OWNED BY public.logros.id;


--
-- Name: mensajes_interes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensajes_interes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    solicitud_id uuid NOT NULL,
    autor_id uuid NOT NULL,
    mensaje text NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: mensajes_postulacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensajes_postulacion (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    postulacion_id uuid NOT NULL,
    autor_id uuid NOT NULL,
    mensaje text NOT NULL,
    leido boolean DEFAULT false NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_msg_post_longitud CHECK ((char_length(mensaje) <= 1000))
);


--
-- Name: municipios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipios (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    departamento_id integer NOT NULL
);


--
-- Name: municipios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.municipios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: municipios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.municipios_id_seq OWNED BY public.municipios.id;


--
-- Name: notificaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notificaciones (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    tipo public.tipo_notificacion NOT NULL,
    mensaje text NOT NULL,
    objeto_tipo character varying(30),
    objeto_id uuid,
    leida boolean DEFAULT false NOT NULL,
    fecha_lectura timestamp(0) without time zone,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: ofrecimiento_habilidades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ofrecimiento_habilidades (
    ofrecimiento_id uuid NOT NULL,
    habilidad_id integer NOT NULL
);


--
-- Name: ofrecimientos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ofrecimientos (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    voluntario_id uuid NOT NULL,
    tipo character varying(10) NOT NULL,
    titulo character varying(200) NOT NULL,
    descripcion text NOT NULL,
    categoria character varying(60) NOT NULL,
    cantidad_total integer DEFAULT 1 NOT NULL,
    cantidad_disponible integer DEFAULT 1 NOT NULL,
    estado_producto character varying(30),
    modalidad_entrega character varying(30),
    municipio_id integer,
    fecha_vencimiento date,
    disponibilidad text,
    alcance text,
    condiciones text,
    imagenes jsonb DEFAULT '[]'::jsonb NOT NULL,
    estado character varying(30) DEFAULT 'DISPONIBLE'::character varying NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_of_cant_disp CHECK (((cantidad_disponible >= 0) AND (cantidad_disponible <= cantidad_total))),
    CONSTRAINT chk_of_cant_total CHECK ((cantidad_total >= 1)),
    CONSTRAINT chk_of_tipo CHECK (((tipo)::text = ANY ((ARRAY['OBJETO'::character varying, 'SERVICIO'::character varying])::text[])))
);


--
-- Name: postulacion_historial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.postulacion_historial (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    postulacion_id uuid NOT NULL,
    estado_anterior character varying(30),
    estado_nuevo character varying(30) NOT NULL,
    cambiado_por uuid,
    rol_actor character varying(20),
    motivo text,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: postulaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.postulaciones (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    publicacion_id uuid NOT NULL,
    voluntario_id uuid NOT NULL,
    estado public.estado_postulacion DEFAULT 'PENDIENTE'::public.estado_postulacion NOT NULL,
    mensaje_voluntario text,
    motivo_rechazo text,
    fecha_respuesta timestamp(0) without time zone,
    fecha_confirmacion timestamp(0) without time zone,
    calificacion smallint,
    comentario_fundacion text,
    fecha_postulacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_calificacion_solo_si_asistio CHECK (((calificacion IS NULL) OR (estado = 'ASISTIO'::public.estado_postulacion))),
    CONSTRAINT chk_calificacion_valida CHECK (((calificacion IS NULL) OR ((calificacion >= 1) AND (calificacion <= 5))))
);


--
-- Name: preferencias_notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.preferencias_notificacion (
    usuario_id uuid NOT NULL,
    notif_postulaciones boolean DEFAULT true NOT NULL,
    notif_convocatorias boolean DEFAULT true NOT NULL,
    notif_recordatorios boolean DEFAULT true NOT NULL,
    notif_logros boolean DEFAULT true NOT NULL,
    notif_soporte boolean DEFAULT true NOT NULL,
    canal_email boolean DEFAULT true NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: programaciones_recurrentes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.programaciones_recurrentes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    titulo character varying(200) NOT NULL,
    plantilla jsonb NOT NULL,
    unidad_intervalo character varying(10) NOT NULL,
    intervalo integer NOT NULL,
    fecha_inicio date NOT NULL,
    duracion_dias integer DEFAULT 1 NOT NULL,
    hora_inicio time without time zone,
    hora_fin time without time zone,
    cupo_maximo integer DEFAULT 1 NOT NULL,
    estado character varying(20) DEFAULT 'ACTIVA'::character varying NOT NULL,
    total_generadas integer DEFAULT 0 NOT NULL,
    ciclo_generadas integer DEFAULT 0 NOT NULL,
    proxima_fecha date NOT NULL,
    fecha_pausa timestamp without time zone,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_prog_intervalo CHECK ((intervalo >= 1))
);


--
-- Name: publicacion_habilidades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publicacion_habilidades (
    publicacion_id uuid NOT NULL,
    habilidad_id integer NOT NULL
);


--
-- Name: publicacion_imagenes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publicacion_imagenes (
    id uuid NOT NULL,
    publicacion_id uuid NOT NULL,
    ruta character varying(500) NOT NULL,
    orden smallint DEFAULT '0'::smallint NOT NULL,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: publicaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publicaciones (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    titulo character varying(200) NOT NULL,
    descripcion text NOT NULL,
    categoria_id integer NOT NULL,
    modalidad public.modalidad_tipo NOT NULL,
    municipio_id integer,
    direccion_exacta character varying(200),
    enlace_virtual text,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    hora_inicio time(0) without time zone,
    hora_fin time(0) without time zone,
    cupo_maximo integer DEFAULT 1 NOT NULL,
    edad_minima integer,
    edad_maxima integer,
    requisitos_adicionales text,
    imagen character varying(500),
    contacto_nombre character varying(150),
    contacto_email character varying(150),
    contacto_telefono character varying(20),
    estado public.estado_publicacion DEFAULT 'BORRADOR'::public.estado_publicacion NOT NULL,
    oculta_por_admin boolean DEFAULT false NOT NULL,
    motivo_ocultamiento text,
    fecha_ocultamiento timestamp(0) without time zone,
    fecha_publicacion timestamp(0) without time zone,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    dificultad public.dificultad_tipo DEFAULT 'MEDIA'::public.dificultad_tipo NOT NULL,
    urgente boolean DEFAULT false NOT NULL,
    objetivo text,
    impacto_esperado text,
    actividades_voluntario text,
    perfil_beneficiarios text,
    que_llevar text,
    recomendaciones text,
    incluye_transporte boolean DEFAULT false NOT NULL,
    incluye_alimentacion boolean DEFAULT false NOT NULL,
    incluye_seguro boolean DEFAULT false NOT NULL,
    politica_cancelacion text,
    otorga_certificado boolean DEFAULT false NOT NULL,
    horas_reconocidas integer DEFAULT 0 NOT NULL,
    nivel_experiencia character varying(40),
    fecha_limite_postulacion date,
    programacion_id uuid,
    CONSTRAINT chk_cupo_valido CHECK ((cupo_maximo >= 1)),
    CONSTRAINT chk_edades_validas CHECK (((edad_minima IS NULL) OR (edad_maxima IS NULL) OR (edad_maxima >= edad_minima))),
    CONSTRAINT chk_fechas_validas CHECK ((fecha_fin >= fecha_inicio)),
    CONSTRAINT chk_ubicacion_presencial CHECK (((modalidad = 'VIRTUAL'::public.modalidad_tipo) OR ((modalidad = ANY (ARRAY['PRESENCIAL'::public.modalidad_tipo, 'HIBRIDA'::public.modalidad_tipo])) AND (municipio_id IS NOT NULL))))
);


--
-- Name: recuperacion_password; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recuperacion_password (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    token text,
    expiracion timestamp(0) without time zone DEFAULT (CURRENT_TIMESTAMP + '01:00:00'::interval) NOT NULL,
    usado boolean DEFAULT false NOT NULL,
    fecha_uso timestamp(0) without time zone,
    ip_solicitud character varying(50),
    user_agent text,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    token_hash character varying(64),
    intentos integer DEFAULT 0
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    token text,
    expiracion timestamp(0) without time zone NOT NULL,
    usado boolean DEFAULT false NOT NULL,
    fecha_uso timestamp(0) without time zone,
    ip_solicitud character varying(50),
    user_agent text,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    token_hash character varying(64),
    fecha_ultimo_uso timestamp without time zone,
    fecha_inicio_sesion timestamp without time zone
);


--
-- Name: reportes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reportes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    reportante_id uuid NOT NULL,
    objeto_tipo character varying(30) NOT NULL,
    objeto_id uuid NOT NULL,
    motivo public.motivo_reporte NOT NULL,
    detalle text,
    estado public.estado_reporte DEFAULT 'PENDIENTE'::public.estado_reporte NOT NULL,
    admin_asignado_id uuid,
    fecha_asignacion timestamp(0) without time zone,
    resolucion text,
    fecha_resolucion timestamp(0) without time zone,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: resenas_organizacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resenas_organizacion (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    fundacion_id uuid NOT NULL,
    voluntario_id uuid NOT NULL,
    calificacion smallint NOT NULL,
    comentario text NOT NULL,
    estado character varying(30) DEFAULT 'VISIBLE'::character varying NOT NULL,
    motivo_moderacion text,
    respuesta text,
    fecha_respuesta timestamp without time zone,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_resena_calif CHECK (((calificacion >= 1) AND (calificacion <= 5)))
);


--
-- Name: solicitudes_cuenta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitudes_cuenta (
    id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    tipo character varying(40) NOT NULL,
    motivo text,
    estado character varying(30) DEFAULT 'PENDIENTE'::character varying NOT NULL,
    respuesta_admin text,
    atendida_por uuid,
    fecha_atencion timestamp without time zone,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: solicitudes_interes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitudes_interes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    ofrecimiento_id uuid NOT NULL,
    fundacion_id uuid NOT NULL,
    cantidad integer DEFAULT 1 NOT NULL,
    mensaje text,
    estado character varying(20) DEFAULT 'PENDIENTE'::character varying NOT NULL,
    confirmada_voluntario boolean DEFAULT false NOT NULL,
    confirmada_fundacion boolean DEFAULT false NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_completada timestamp without time zone,
    CONSTRAINT chk_si_cantidad CHECK ((cantidad >= 1))
);


--
-- Name: ticket_mensajes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_mensajes (
    id uuid NOT NULL,
    ticket_id uuid NOT NULL,
    autor_id uuid NOT NULL,
    es_admin boolean DEFAULT false NOT NULL,
    mensaje text NOT NULL,
    adjunto_url character varying(500),
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: ticket_numero_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ticket_numero_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tickets_soporte; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tickets_soporte (
    id uuid NOT NULL,
    numero bigint DEFAULT nextval('public.ticket_numero_seq'::regclass) NOT NULL,
    usuario_id uuid NOT NULL,
    categoria character varying(40) NOT NULL,
    asunto character varying(200) NOT NULL,
    descripcion text NOT NULL,
    adjunto_url character varying(500),
    estado character varying(30) DEFAULT 'ABIERTO'::character varying NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: transacciones_puntos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transacciones_puntos (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    voluntario_id uuid NOT NULL,
    postulacion_id uuid,
    puntos_base integer NOT NULL,
    puntos_bonus integer DEFAULT 0 NOT NULL,
    puntos_total integer NOT NULL,
    motivo character varying(200) NOT NULL,
    fecha timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: usuario_aceptaciones_legales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_aceptaciones_legales (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    version_id integer NOT NULL,
    aceptado boolean DEFAULT true NOT NULL,
    ip_aceptacion character varying(50),
    user_agent text,
    fecha_aceptacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    nombre character varying(120) NOT NULL,
    email character varying(150) NOT NULL,
    password_hash text,
    provider public.proveedor_auth DEFAULT 'LOCAL'::public.proveedor_auth NOT NULL,
    provider_id character varying(255),
    telefono character varying(20),
    rol public.rol_usuario NOT NULL,
    estado public.estado_usuario DEFAULT 'ACTIVO'::public.estado_usuario NOT NULL,
    email_verificado boolean DEFAULT false NOT NULL,
    fecha_registro timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    mfa_secret text,
    mfa_activo boolean DEFAULT false NOT NULL,
    mfa_codigos_respaldo jsonb,
    mfa_ultimo_paso bigint,
    CONSTRAINT chk_auth_valid CHECK ((((provider = 'LOCAL'::public.proveedor_auth) AND (password_hash IS NOT NULL)) OR ((provider = 'GOOGLE'::public.proveedor_auth) AND (provider_id IS NOT NULL))))
);


--
-- Name: verificacion_email; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.verificacion_email (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    token text,
    expiracion timestamp(0) without time zone DEFAULT (CURRENT_TIMESTAMP + '1 day'::interval) NOT NULL,
    usado boolean DEFAULT false NOT NULL,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    token_hash character varying(64)
);


--
-- Name: voluntario_favoritos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntario_favoritos (
    id uuid NOT NULL,
    voluntario_id uuid NOT NULL,
    tipo character varying(20) NOT NULL,
    publicacion_id uuid,
    fundacion_id uuid,
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: voluntario_habilidades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntario_habilidades (
    voluntario_id uuid NOT NULL,
    habilidad_id integer NOT NULL
);


--
-- Name: voluntario_intereses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntario_intereses (
    voluntario_id uuid NOT NULL,
    interes_id integer NOT NULL
);


--
-- Name: voluntario_logros; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntario_logros (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    voluntario_id uuid NOT NULL,
    logro_id integer NOT NULL,
    fecha_obtencion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: voluntario_puntos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntario_puntos (
    voluntario_id uuid NOT NULL,
    saldo integer DEFAULT 0 NOT NULL,
    total_historico integer DEFAULT 0 NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: voluntarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voluntarios (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    usuario_id uuid NOT NULL,
    tipo_documento public.tipo_documento NOT NULL,
    numero_documento character varying(30) NOT NULL,
    fecha_nacimiento date NOT NULL,
    genero public.genero_tipo NOT NULL,
    municipio_id integer NOT NULL,
    disponibilidad public.disponibilidad_tipo NOT NULL,
    experiencia text,
    foto_perfil character varying(500),
    fecha_creacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    documento_identidad character varying(255),
    esta_verificado boolean DEFAULT false NOT NULL,
    direccion character varying(200),
    descripcion text,
    telefono_contacto character varying(20),
    nivel_educativo character varying(100),
    profesion character varying(150),
    idiomas character varying(300),
    preferencia_modalidad character varying(20),
    contacto_emergencia_nombre character varying(150),
    contacto_emergencia_telefono character varying(20),
    horas_acumuladas integer DEFAULT 0 NOT NULL,
    actividades_completadas integer DEFAULT 0 NOT NULL,
    acudiente_nombre character varying(150),
    acudiente_documento character varying(30),
    acudiente_telefono character varying(20),
    acudiente_parentesco character varying(40),
    autorizacion_acudiente character varying(500),
    autorizacion_estado character varying(20),
    autorizacion_fecha timestamp with time zone,
    autorizacion_nota text,
    CONSTRAINT chk_edad_minima CHECK ((fecha_nacimiento <= (CURRENT_DATE - '14 years'::interval))),
    CONSTRAINT ck_voluntarios_autorizacion_estado CHECK (((autorizacion_estado IS NULL) OR ((autorizacion_estado)::text = ANY ((ARRAY['NO_REQUERIDA'::character varying, 'PENDIENTE'::character varying, 'APROBADA'::character varying, 'RECHAZADA'::character varying])::text[]))))
);


--
-- Name: areas_impacto id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas_impacto ALTER COLUMN id SET DEFAULT nextval('public.areas_impacto_id_seq'::regclass);


--
-- Name: departamentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departamentos ALTER COLUMN id SET DEFAULT nextval('public.departamentos_id_seq'::regclass);


--
-- Name: documento_legal_versiones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_legal_versiones ALTER COLUMN id SET DEFAULT nextval('public.documento_legal_versiones_id_seq'::regclass);


--
-- Name: documentos_legales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_legales ALTER COLUMN id SET DEFAULT nextval('public.documentos_legales_id_seq'::regclass);


--
-- Name: habilidades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.habilidades ALTER COLUMN id SET DEFAULT nextval('public.habilidades_id_seq'::regclass);


--
-- Name: intereses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intereses ALTER COLUMN id SET DEFAULT nextval('public.intereses_id_seq'::regclass);


--
-- Name: logros id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.logros ALTER COLUMN id SET DEFAULT nextval('public.logros_id_seq'::regclass);


--
-- Name: municipios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipios ALTER COLUMN id SET DEFAULT nextval('public.municipios_id_seq'::regclass);


--
-- Name: admin_acciones admin_acciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_acciones
    ADD CONSTRAINT admin_acciones_pkey PRIMARY KEY (id);


--
-- Name: admin_perfiles admin_perfiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_perfiles
    ADD CONSTRAINT admin_perfiles_pkey PRIMARY KEY (id);


--
-- Name: admin_perfiles admin_perfiles_usuario_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_perfiles
    ADD CONSTRAINT admin_perfiles_usuario_id_unique UNIQUE (usuario_id);


--
-- Name: advertencias_voluntario advertencias_voluntario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advertencias_voluntario
    ADD CONSTRAINT advertencias_voluntario_pkey PRIMARY KEY (id);


--
-- Name: areas_impacto areas_impacto_nombre_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas_impacto
    ADD CONSTRAINT areas_impacto_nombre_unique UNIQUE (nombre);


--
-- Name: areas_impacto areas_impacto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas_impacto
    ADD CONSTRAINT areas_impacto_pkey PRIMARY KEY (id);


--
-- Name: auditoria_perfil auditoria_perfil_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_perfil
    ADD CONSTRAINT auditoria_perfil_pkey PRIMARY KEY (id);


--
-- Name: configuracion_sistema configuracion_sistema_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_sistema
    ADD CONSTRAINT configuracion_sistema_pkey PRIMARY KEY (clave);


--
-- Name: departamentos departamentos_nombre_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departamentos
    ADD CONSTRAINT departamentos_nombre_unique UNIQUE (nombre);


--
-- Name: departamentos departamentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departamentos
    ADD CONSTRAINT departamentos_pkey PRIMARY KEY (id);


--
-- Name: documento_legal_versiones documento_legal_versiones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_legal_versiones
    ADD CONSTRAINT documento_legal_versiones_pkey PRIMARY KEY (id);


--
-- Name: documentos_legales documentos_legales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_legales
    ADD CONSTRAINT documentos_legales_pkey PRIMARY KEY (id);


--
-- Name: fundacion_areas fundacion_areas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_areas
    ADD CONSTRAINT fundacion_areas_pkey PRIMARY KEY (fundacion_id, area_id);


--
-- Name: fundacion_documentos fundacion_documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_documentos
    ADD CONSTRAINT fundacion_documentos_pkey PRIMARY KEY (id);


--
-- Name: fundacion_galeria fundacion_galeria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_galeria
    ADD CONSTRAINT fundacion_galeria_pkey PRIMARY KEY (id);


--
-- Name: fundaciones fundaciones_nit_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_nit_unique UNIQUE (nit);


--
-- Name: fundaciones fundaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_pkey PRIMARY KEY (id);


--
-- Name: fundaciones fundaciones_usuario_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_usuario_id_unique UNIQUE (usuario_id);


--
-- Name: habilidades habilidades_nombre_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.habilidades
    ADD CONSTRAINT habilidades_nombre_unique UNIQUE (nombre);


--
-- Name: habilidades habilidades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.habilidades
    ADD CONSTRAINT habilidades_pkey PRIMARY KEY (id);


--
-- Name: historial_estados_fundacion historial_estados_fundacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_fundacion
    ADD CONSTRAINT historial_estados_fundacion_pkey PRIMARY KEY (id);


--
-- Name: historial_estados_voluntario historial_estados_voluntario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_voluntario
    ADD CONSTRAINT historial_estados_voluntario_pkey PRIMARY KEY (id);


--
-- Name: intereses intereses_nombre_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intereses
    ADD CONSTRAINT intereses_nombre_unique UNIQUE (nombre);


--
-- Name: intereses intereses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intereses
    ADD CONSTRAINT intereses_pkey PRIMARY KEY (id);


--
-- Name: logros logros_codigo_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.logros
    ADD CONSTRAINT logros_codigo_unique UNIQUE (codigo);


--
-- Name: logros logros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.logros
    ADD CONSTRAINT logros_pkey PRIMARY KEY (id);


--
-- Name: mensajes_interes mensajes_interes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_interes
    ADD CONSTRAINT mensajes_interes_pkey PRIMARY KEY (id);


--
-- Name: mensajes_postulacion mensajes_postulacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_postulacion
    ADD CONSTRAINT mensajes_postulacion_pkey PRIMARY KEY (id);


--
-- Name: municipios municipios_nombre_departamento_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipios
    ADD CONSTRAINT municipios_nombre_departamento_id_unique UNIQUE (nombre, departamento_id);


--
-- Name: municipios municipios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipios
    ADD CONSTRAINT municipios_pkey PRIMARY KEY (id);


--
-- Name: notificaciones notificaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificaciones
    ADD CONSTRAINT notificaciones_pkey PRIMARY KEY (id);


--
-- Name: ofrecimiento_habilidades ofrecimiento_habilidades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimiento_habilidades
    ADD CONSTRAINT ofrecimiento_habilidades_pkey PRIMARY KEY (ofrecimiento_id, habilidad_id);


--
-- Name: ofrecimientos ofrecimientos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimientos
    ADD CONSTRAINT ofrecimientos_pkey PRIMARY KEY (id);


--
-- Name: postulacion_historial postulacion_historial_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulacion_historial
    ADD CONSTRAINT postulacion_historial_pkey PRIMARY KEY (id);


--
-- Name: postulaciones postulaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulaciones
    ADD CONSTRAINT postulaciones_pkey PRIMARY KEY (id);


--
-- Name: postulaciones postulaciones_publicacion_id_voluntario_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulaciones
    ADD CONSTRAINT postulaciones_publicacion_id_voluntario_id_unique UNIQUE (publicacion_id, voluntario_id);


--
-- Name: preferencias_notificacion preferencias_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_notificacion
    ADD CONSTRAINT preferencias_notificacion_pkey PRIMARY KEY (usuario_id);


--
-- Name: programaciones_recurrentes programaciones_recurrentes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programaciones_recurrentes
    ADD CONSTRAINT programaciones_recurrentes_pkey PRIMARY KEY (id);


--
-- Name: publicacion_habilidades publicacion_habilidades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicacion_habilidades
    ADD CONSTRAINT publicacion_habilidades_pkey PRIMARY KEY (publicacion_id, habilidad_id);


--
-- Name: publicacion_imagenes publicacion_imagenes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicacion_imagenes
    ADD CONSTRAINT publicacion_imagenes_pkey PRIMARY KEY (id);


--
-- Name: publicaciones publicaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicaciones
    ADD CONSTRAINT publicaciones_pkey PRIMARY KEY (id);


--
-- Name: recuperacion_password recuperacion_password_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recuperacion_password
    ADD CONSTRAINT recuperacion_password_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: reportes reportes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reportes
    ADD CONSTRAINT reportes_pkey PRIMARY KEY (id);


--
-- Name: resenas_organizacion resenas_organizacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resenas_organizacion
    ADD CONSTRAINT resenas_organizacion_pkey PRIMARY KEY (id);


--
-- Name: solicitudes_cuenta solicitudes_cuenta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_cuenta
    ADD CONSTRAINT solicitudes_cuenta_pkey PRIMARY KEY (id);


--
-- Name: solicitudes_interes solicitudes_interes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_interes
    ADD CONSTRAINT solicitudes_interes_pkey PRIMARY KEY (id);


--
-- Name: ticket_mensajes ticket_mensajes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_mensajes
    ADD CONSTRAINT ticket_mensajes_pkey PRIMARY KEY (id);


--
-- Name: tickets_soporte tickets_soporte_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets_soporte
    ADD CONSTRAINT tickets_soporte_pkey PRIMARY KEY (id);


--
-- Name: transacciones_puntos transacciones_puntos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transacciones_puntos
    ADD CONSTRAINT transacciones_puntos_pkey PRIMARY KEY (id);


--
-- Name: documento_legal_versiones uq_doc_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_legal_versiones
    ADD CONSTRAINT uq_doc_version UNIQUE (documento_id, version);


--
-- Name: documentos_legales uq_documentos_legales_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_legales
    ADD CONSTRAINT uq_documentos_legales_codigo UNIQUE (codigo);


--
-- Name: resenas_organizacion uq_resena_vol_fund; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resenas_organizacion
    ADD CONSTRAINT uq_resena_vol_fund UNIQUE (fundacion_id, voluntario_id);


--
-- Name: tickets_soporte uq_tickets_numero; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets_soporte
    ADD CONSTRAINT uq_tickets_numero UNIQUE (numero);


--
-- Name: usuario_aceptaciones_legales usuario_aceptaciones_legales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_aceptaciones_legales
    ADD CONSTRAINT usuario_aceptaciones_legales_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: verificacion_email verificacion_email_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verificacion_email
    ADD CONSTRAINT verificacion_email_pkey PRIMARY KEY (id);


--
-- Name: voluntario_favoritos vol_fav_fund_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT vol_fav_fund_unique UNIQUE (voluntario_id, fundacion_id);


--
-- Name: voluntario_favoritos vol_fav_pub_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT vol_fav_pub_unique UNIQUE (voluntario_id, publicacion_id);


--
-- Name: voluntario_favoritos voluntario_favoritos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT voluntario_favoritos_pkey PRIMARY KEY (id);


--
-- Name: voluntario_habilidades voluntario_habilidades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_habilidades
    ADD CONSTRAINT voluntario_habilidades_pkey PRIMARY KEY (voluntario_id, habilidad_id);


--
-- Name: voluntario_intereses voluntario_intereses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_intereses
    ADD CONSTRAINT voluntario_intereses_pkey PRIMARY KEY (voluntario_id, interes_id);


--
-- Name: voluntario_logros voluntario_logros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_logros
    ADD CONSTRAINT voluntario_logros_pkey PRIMARY KEY (id);


--
-- Name: voluntario_logros voluntario_logros_voluntario_id_logro_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_logros
    ADD CONSTRAINT voluntario_logros_voluntario_id_logro_id_unique UNIQUE (voluntario_id, logro_id);


--
-- Name: voluntario_puntos voluntario_puntos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_puntos
    ADD CONSTRAINT voluntario_puntos_pkey PRIMARY KEY (voluntario_id);


--
-- Name: voluntarios voluntarios_numero_documento_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntarios
    ADD CONSTRAINT voluntarios_numero_documento_unique UNIQUE (numero_documento);


--
-- Name: voluntarios voluntarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntarios
    ADD CONSTRAINT voluntarios_pkey PRIMARY KEY (id);


--
-- Name: voluntarios voluntarios_usuario_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntarios
    ADD CONSTRAINT voluntarios_usuario_id_unique UNIQUE (usuario_id);


--
-- Name: idx_aceptacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aceptacion_usuario ON public.usuario_aceptaciones_legales USING btree (usuario_id);


--
-- Name: idx_admin_acc_admin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_acc_admin ON public.admin_acciones USING btree (admin_id);


--
-- Name: idx_admin_acc_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_acc_fecha ON public.admin_acciones USING btree (fecha_accion DESC);


--
-- Name: idx_admin_acc_objeto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_acc_objeto ON public.admin_acciones USING btree (objeto_tipo, objeto_id);


--
-- Name: idx_admin_acc_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_acc_tipo ON public.admin_acciones USING btree (tipo);


--
-- Name: idx_admin_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_activo ON public.admin_perfiles USING btree (activo) WHERE (activo = true);


--
-- Name: idx_admin_nivel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_nivel ON public.admin_perfiles USING btree (nivel);


--
-- Name: idx_admin_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_usuario ON public.admin_perfiles USING btree (usuario_id);


--
-- Name: idx_adv_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_adv_activa ON public.advertencias_voluntario USING btree (activa) WHERE (activa = true);


--
-- Name: idx_adv_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_adv_voluntario ON public.advertencias_voluntario USING btree (voluntario_id);


--
-- Name: idx_auditoria_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auditoria_usuario ON public.auditoria_perfil USING btree (usuario_id);


--
-- Name: idx_config_modulo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_config_modulo ON public.configuracion_sistema USING btree (modulo);


--
-- Name: idx_doc_version_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_doc_version_vigente ON public.documento_legal_versiones USING btree (documento_id, vigente);


--
-- Name: idx_email_provider_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_email_provider_unique ON public.usuarios USING btree (email, provider);


--
-- Name: idx_fund_docs_fundacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fund_docs_fundacion ON public.fundacion_documentos USING btree (fundacion_id);


--
-- Name: idx_fund_docs_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fund_docs_tipo ON public.fundacion_documentos USING btree (tipo_documento);


--
-- Name: idx_fundacion_areas; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fundacion_areas ON public.fundacion_areas USING btree (fundacion_id);


--
-- Name: idx_fundacion_correo_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_fundacion_correo_unique ON public.fundaciones USING btree (correo_institucional) WHERE (correo_institucional IS NOT NULL);


--
-- Name: idx_fundacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fundacion_estado ON public.fundaciones USING btree (estado_verificacion);


--
-- Name: idx_fundacion_municipio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fundacion_municipio ON public.fundaciones USING btree (municipio_id);


--
-- Name: idx_fundacion_nit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fundacion_nit ON public.fundaciones USING btree (nit);


--
-- Name: idx_fundacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fundacion_usuario ON public.fundaciones USING btree (usuario_id);


--
-- Name: idx_galeria_fund; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_galeria_fund ON public.fundacion_galeria USING btree (fundacion_id);


--
-- Name: idx_hist_fund_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hist_fund_fecha ON public.historial_estados_fundacion USING btree (fecha DESC);


--
-- Name: idx_hist_fund_fundacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hist_fund_fundacion ON public.historial_estados_fundacion USING btree (fundacion_id);


--
-- Name: idx_hist_vol_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hist_vol_fecha ON public.historial_estados_voluntario USING btree (fecha DESC);


--
-- Name: idx_hist_vol_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hist_vol_usuario ON public.historial_estados_voluntario USING btree (usuario_id);


--
-- Name: idx_msg_interes_sol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_msg_interes_sol ON public.mensajes_interes USING btree (solicitud_id);


--
-- Name: idx_msg_post_no_leidos; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_msg_post_no_leidos ON public.mensajes_postulacion USING btree (postulacion_id) WHERE (leido = false);


--
-- Name: idx_msg_post_postulacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_msg_post_postulacion ON public.mensajes_postulacion USING btree (postulacion_id, fecha_creacion);


--
-- Name: idx_municipio_departamento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_municipio_departamento ON public.municipios USING btree (departamento_id);


--
-- Name: idx_notif_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notif_usuario ON public.notificaciones USING btree (usuario_id, leida, fecha_creacion DESC);


--
-- Name: idx_of_estado_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_of_estado_tipo ON public.ofrecimientos USING btree (estado, tipo);


--
-- Name: idx_of_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_of_voluntario ON public.ofrecimientos USING btree (voluntario_id);


--
-- Name: idx_post_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_estado ON public.postulaciones USING btree (estado);


--
-- Name: idx_post_hist_post; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_hist_post ON public.postulacion_historial USING btree (postulacion_id);


--
-- Name: idx_post_publicacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_publicacion ON public.postulaciones USING btree (publicacion_id);


--
-- Name: idx_post_publicacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_publicacion_estado ON public.postulaciones USING btree (publicacion_id, estado);


--
-- Name: idx_post_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_voluntario ON public.postulaciones USING btree (voluntario_id);


--
-- Name: idx_post_voluntario_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_post_voluntario_estado ON public.postulaciones USING btree (voluntario_id, estado);


--
-- Name: idx_prog_fundacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prog_fundacion ON public.programaciones_recurrentes USING btree (fundacion_id);


--
-- Name: idx_provider_id_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_provider_id_unique ON public.usuarios USING btree (provider, provider_id) WHERE (provider_id IS NOT NULL);


--
-- Name: idx_pub_categoria; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_categoria ON public.publicaciones USING btree (categoria_id);


--
-- Name: idx_pub_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_estado ON public.publicaciones USING btree (estado);


--
-- Name: idx_pub_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_estado_fecha ON public.publicaciones USING btree (estado, fecha_inicio);


--
-- Name: idx_pub_fecha_inicio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_fecha_inicio ON public.publicaciones USING btree (fecha_inicio);


--
-- Name: idx_pub_fundacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_fundacion ON public.publicaciones USING btree (fundacion_id);


--
-- Name: idx_pub_habilidades; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_habilidades ON public.publicacion_habilidades USING btree (publicacion_id);


--
-- Name: idx_pub_modalidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_modalidad ON public.publicaciones USING btree (modalidad);


--
-- Name: idx_pub_municipio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_municipio ON public.publicaciones USING btree (municipio_id);


--
-- Name: idx_pub_programacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pub_programacion ON public.publicaciones USING btree (programacion_id);


--
-- Name: idx_recuperacion_password_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_recuperacion_password_token_hash ON public.recuperacion_password USING btree (token_hash);


--
-- Name: idx_refresh_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_expiracion ON public.refresh_tokens USING btree (expiracion) WHERE (usado = false);


--
-- Name: idx_refresh_token_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_refresh_token_unique ON public.refresh_tokens USING btree (token);


--
-- Name: idx_refresh_tokens_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_token_hash ON public.refresh_tokens USING btree (token_hash);


--
-- Name: idx_refresh_tokens_usuario_activos; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_usuario_activos ON public.refresh_tokens USING btree (usuario_id, usado);


--
-- Name: idx_refresh_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_usuario ON public.refresh_tokens USING btree (usuario_id);


--
-- Name: idx_reporte_admin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reporte_admin ON public.reportes USING btree (admin_asignado_id);


--
-- Name: idx_reporte_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reporte_estado ON public.reportes USING btree (estado);


--
-- Name: idx_reporte_objeto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reporte_objeto ON public.reportes USING btree (objeto_tipo, objeto_id);


--
-- Name: idx_resena_fund_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_resena_fund_estado ON public.resenas_organizacion USING btree (fundacion_id, estado);


--
-- Name: idx_reset_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reset_expiracion ON public.recuperacion_password USING btree (expiracion) WHERE (usado = false);


--
-- Name: idx_reset_token_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_reset_token_unique ON public.recuperacion_password USING btree (token);


--
-- Name: idx_reset_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reset_usuario ON public.recuperacion_password USING btree (usuario_id);


--
-- Name: idx_si_fundacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_si_fundacion ON public.solicitudes_interes USING btree (fundacion_id);


--
-- Name: idx_si_ofrecimiento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_si_ofrecimiento ON public.solicitudes_interes USING btree (ofrecimiento_id);


--
-- Name: idx_solicitudes_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitudes_usuario ON public.solicitudes_cuenta USING btree (usuario_id);


--
-- Name: idx_ticket_mensajes_ticket; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_mensajes_ticket ON public.ticket_mensajes USING btree (ticket_id);


--
-- Name: idx_tickets_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tickets_usuario ON public.tickets_soporte USING btree (usuario_id);


--
-- Name: idx_token_verificacion_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_token_verificacion_unique ON public.verificacion_email USING btree (token);


--
-- Name: idx_trans_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trans_fecha ON public.transacciones_puntos USING btree (fecha DESC);


--
-- Name: idx_trans_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trans_voluntario ON public.transacciones_puntos USING btree (voluntario_id);


--
-- Name: idx_usuario_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_email ON public.usuarios USING btree (email);


--
-- Name: idx_usuario_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_provider ON public.usuarios USING btree (provider);


--
-- Name: idx_verificacion_email_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verificacion_email_token_hash ON public.verificacion_email USING btree (token_hash);


--
-- Name: idx_verificacion_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verificacion_expiracion ON public.verificacion_email USING btree (expiracion);


--
-- Name: idx_verificacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_verificacion_usuario ON public.verificacion_email USING btree (usuario_id);


--
-- Name: idx_vol_hab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vol_hab ON public.voluntario_habilidades USING btree (voluntario_id);


--
-- Name: idx_vol_int; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vol_int ON public.voluntario_intereses USING btree (voluntario_id);


--
-- Name: idx_vol_logros_voluntario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vol_logros_voluntario ON public.voluntario_logros USING btree (voluntario_id);


--
-- Name: idx_voluntario_municipio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_voluntario_municipio ON public.voluntarios USING btree (municipio_id);


--
-- Name: idx_voluntario_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_voluntario_usuario ON public.voluntarios USING btree (usuario_id);


--
-- Name: ix_voluntarios_autorizacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_voluntarios_autorizacion_estado ON public.voluntarios USING btree (autorizacion_estado) WHERE ((autorizacion_estado)::text = 'PENDIENTE'::text);


--
-- Name: publicacion_imagenes_publicacion_id_orden_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX publicacion_imagenes_publicacion_id_orden_index ON public.publicacion_imagenes USING btree (publicacion_id, orden);


--
-- Name: uq_si_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_si_activa ON public.solicitudes_interes USING btree (ofrecimiento_id, fundacion_id) WHERE ((estado)::text = ANY ((ARRAY['PENDIENTE'::character varying, 'ACEPTADA'::character varying, 'EN_COORDINACION'::character varying])::text[]));


--
-- Name: voluntario_favoritos_voluntario_id_tipo_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX voluntario_favoritos_voluntario_id_tipo_index ON public.voluntario_favoritos USING btree (voluntario_id, tipo);


--
-- Name: admin_acciones admin_acciones_admin_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_acciones
    ADD CONSTRAINT admin_acciones_admin_id_foreign FOREIGN KEY (admin_id) REFERENCES public.admin_perfiles(id) ON DELETE RESTRICT;


--
-- Name: admin_perfiles admin_perfiles_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_perfiles
    ADD CONSTRAINT admin_perfiles_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: advertencias_voluntario advertencias_voluntario_admin_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advertencias_voluntario
    ADD CONSTRAINT advertencias_voluntario_admin_id_foreign FOREIGN KEY (admin_id) REFERENCES public.admin_perfiles(id) ON DELETE RESTRICT;


--
-- Name: advertencias_voluntario advertencias_voluntario_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advertencias_voluntario
    ADD CONSTRAINT advertencias_voluntario_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: auditoria_perfil auditoria_perfil_realizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_perfil
    ADD CONSTRAINT auditoria_perfil_realizado_por_fkey FOREIGN KEY (realizado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: auditoria_perfil auditoria_perfil_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria_perfil
    ADD CONSTRAINT auditoria_perfil_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: documento_legal_versiones documento_legal_versiones_documento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_legal_versiones
    ADD CONSTRAINT documento_legal_versiones_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES public.documentos_legales(id) ON DELETE CASCADE;


--
-- Name: admin_perfiles fk_admin_creado_por; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_perfiles
    ADD CONSTRAINT fk_admin_creado_por FOREIGN KEY (creado_por) REFERENCES public.admin_perfiles(id) ON DELETE SET NULL;


--
-- Name: reportes fk_reporte_admin; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reportes
    ADD CONSTRAINT fk_reporte_admin FOREIGN KEY (admin_asignado_id) REFERENCES public.admin_perfiles(id) ON DELETE SET NULL;


--
-- Name: fundacion_areas fundacion_areas_area_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_areas
    ADD CONSTRAINT fundacion_areas_area_id_foreign FOREIGN KEY (area_id) REFERENCES public.areas_impacto(id) ON DELETE CASCADE;


--
-- Name: fundacion_areas fundacion_areas_fundacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_areas
    ADD CONSTRAINT fundacion_areas_fundacion_id_foreign FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: fundacion_documentos fundacion_documentos_fundacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_documentos
    ADD CONSTRAINT fundacion_documentos_fundacion_id_foreign FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: fundacion_galeria fundacion_galeria_fundacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundacion_galeria
    ADD CONSTRAINT fundacion_galeria_fundacion_id_fkey FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: fundaciones fundaciones_municipio_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_municipio_id_foreign FOREIGN KEY (municipio_id) REFERENCES public.municipios(id) ON DELETE RESTRICT;


--
-- Name: fundaciones fundaciones_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: fundaciones fundaciones_verificacion_documental_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fundaciones
    ADD CONSTRAINT fundaciones_verificacion_documental_por_fkey FOREIGN KEY (verificacion_documental_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: historial_estados_fundacion historial_estados_fundacion_admin_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_fundacion
    ADD CONSTRAINT historial_estados_fundacion_admin_id_foreign FOREIGN KEY (admin_id) REFERENCES public.admin_perfiles(id) ON DELETE RESTRICT;


--
-- Name: historial_estados_fundacion historial_estados_fundacion_fundacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_fundacion
    ADD CONSTRAINT historial_estados_fundacion_fundacion_id_foreign FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: historial_estados_voluntario historial_estados_voluntario_admin_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_voluntario
    ADD CONSTRAINT historial_estados_voluntario_admin_id_foreign FOREIGN KEY (admin_id) REFERENCES public.admin_perfiles(id) ON DELETE RESTRICT;


--
-- Name: historial_estados_voluntario historial_estados_voluntario_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_estados_voluntario
    ADD CONSTRAINT historial_estados_voluntario_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: mensajes_interes mensajes_interes_autor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_interes
    ADD CONSTRAINT mensajes_interes_autor_id_fkey FOREIGN KEY (autor_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: mensajes_interes mensajes_interes_solicitud_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_interes
    ADD CONSTRAINT mensajes_interes_solicitud_id_fkey FOREIGN KEY (solicitud_id) REFERENCES public.solicitudes_interes(id) ON DELETE CASCADE;


--
-- Name: mensajes_postulacion mensajes_postulacion_autor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_postulacion
    ADD CONSTRAINT mensajes_postulacion_autor_id_fkey FOREIGN KEY (autor_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: mensajes_postulacion mensajes_postulacion_postulacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes_postulacion
    ADD CONSTRAINT mensajes_postulacion_postulacion_id_fkey FOREIGN KEY (postulacion_id) REFERENCES public.postulaciones(id) ON DELETE CASCADE;


--
-- Name: municipios municipios_departamento_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipios
    ADD CONSTRAINT municipios_departamento_id_foreign FOREIGN KEY (departamento_id) REFERENCES public.departamentos(id) ON DELETE RESTRICT;


--
-- Name: notificaciones notificaciones_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notificaciones
    ADD CONSTRAINT notificaciones_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: ofrecimiento_habilidades ofrecimiento_habilidades_habilidad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimiento_habilidades
    ADD CONSTRAINT ofrecimiento_habilidades_habilidad_id_fkey FOREIGN KEY (habilidad_id) REFERENCES public.habilidades(id) ON DELETE CASCADE;


--
-- Name: ofrecimiento_habilidades ofrecimiento_habilidades_ofrecimiento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimiento_habilidades
    ADD CONSTRAINT ofrecimiento_habilidades_ofrecimiento_id_fkey FOREIGN KEY (ofrecimiento_id) REFERENCES public.ofrecimientos(id) ON DELETE CASCADE;


--
-- Name: ofrecimientos ofrecimientos_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimientos
    ADD CONSTRAINT ofrecimientos_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.municipios(id) ON DELETE SET NULL;


--
-- Name: ofrecimientos ofrecimientos_voluntario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofrecimientos
    ADD CONSTRAINT ofrecimientos_voluntario_id_fkey FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: postulacion_historial postulacion_historial_cambiado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulacion_historial
    ADD CONSTRAINT postulacion_historial_cambiado_por_fkey FOREIGN KEY (cambiado_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: postulacion_historial postulacion_historial_postulacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulacion_historial
    ADD CONSTRAINT postulacion_historial_postulacion_id_fkey FOREIGN KEY (postulacion_id) REFERENCES public.postulaciones(id) ON DELETE CASCADE;


--
-- Name: postulaciones postulaciones_publicacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulaciones
    ADD CONSTRAINT postulaciones_publicacion_id_foreign FOREIGN KEY (publicacion_id) REFERENCES public.publicaciones(id) ON DELETE CASCADE;


--
-- Name: postulaciones postulaciones_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.postulaciones
    ADD CONSTRAINT postulaciones_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: preferencias_notificacion preferencias_notificacion_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_notificacion
    ADD CONSTRAINT preferencias_notificacion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: programaciones_recurrentes programaciones_recurrentes_fundacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programaciones_recurrentes
    ADD CONSTRAINT programaciones_recurrentes_fundacion_id_fkey FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: publicacion_habilidades publicacion_habilidades_habilidad_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicacion_habilidades
    ADD CONSTRAINT publicacion_habilidades_habilidad_id_foreign FOREIGN KEY (habilidad_id) REFERENCES public.habilidades(id) ON DELETE CASCADE;


--
-- Name: publicacion_habilidades publicacion_habilidades_publicacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicacion_habilidades
    ADD CONSTRAINT publicacion_habilidades_publicacion_id_foreign FOREIGN KEY (publicacion_id) REFERENCES public.publicaciones(id) ON DELETE CASCADE;


--
-- Name: publicacion_imagenes publicacion_imagenes_publicacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicacion_imagenes
    ADD CONSTRAINT publicacion_imagenes_publicacion_id_foreign FOREIGN KEY (publicacion_id) REFERENCES public.publicaciones(id) ON DELETE CASCADE;


--
-- Name: publicaciones publicaciones_categoria_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicaciones
    ADD CONSTRAINT publicaciones_categoria_id_foreign FOREIGN KEY (categoria_id) REFERENCES public.areas_impacto(id) ON DELETE RESTRICT;


--
-- Name: publicaciones publicaciones_fundacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicaciones
    ADD CONSTRAINT publicaciones_fundacion_id_foreign FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: publicaciones publicaciones_municipio_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicaciones
    ADD CONSTRAINT publicaciones_municipio_id_foreign FOREIGN KEY (municipio_id) REFERENCES public.municipios(id) ON DELETE RESTRICT;


--
-- Name: publicaciones publicaciones_programacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publicaciones
    ADD CONSTRAINT publicaciones_programacion_id_fkey FOREIGN KEY (programacion_id) REFERENCES public.programaciones_recurrentes(id) ON DELETE SET NULL;


--
-- Name: recuperacion_password recuperacion_password_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recuperacion_password
    ADD CONSTRAINT recuperacion_password_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: reportes reportes_reportante_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reportes
    ADD CONSTRAINT reportes_reportante_id_foreign FOREIGN KEY (reportante_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: resenas_organizacion resenas_organizacion_fundacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resenas_organizacion
    ADD CONSTRAINT resenas_organizacion_fundacion_id_fkey FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: resenas_organizacion resenas_organizacion_voluntario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resenas_organizacion
    ADD CONSTRAINT resenas_organizacion_voluntario_id_fkey FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: solicitudes_cuenta solicitudes_cuenta_atendida_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_cuenta
    ADD CONSTRAINT solicitudes_cuenta_atendida_por_fkey FOREIGN KEY (atendida_por) REFERENCES public.usuarios(id) ON DELETE SET NULL;


--
-- Name: solicitudes_cuenta solicitudes_cuenta_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_cuenta
    ADD CONSTRAINT solicitudes_cuenta_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: solicitudes_interes solicitudes_interes_fundacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_interes
    ADD CONSTRAINT solicitudes_interes_fundacion_id_fkey FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: solicitudes_interes solicitudes_interes_ofrecimiento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitudes_interes
    ADD CONSTRAINT solicitudes_interes_ofrecimiento_id_fkey FOREIGN KEY (ofrecimiento_id) REFERENCES public.ofrecimientos(id) ON DELETE CASCADE;


--
-- Name: ticket_mensajes ticket_mensajes_autor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_mensajes
    ADD CONSTRAINT ticket_mensajes_autor_id_fkey FOREIGN KEY (autor_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: ticket_mensajes ticket_mensajes_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_mensajes
    ADD CONSTRAINT ticket_mensajes_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES public.tickets_soporte(id) ON DELETE CASCADE;


--
-- Name: tickets_soporte tickets_soporte_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets_soporte
    ADD CONSTRAINT tickets_soporte_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: transacciones_puntos transacciones_puntos_postulacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transacciones_puntos
    ADD CONSTRAINT transacciones_puntos_postulacion_id_foreign FOREIGN KEY (postulacion_id) REFERENCES public.postulaciones(id) ON DELETE SET NULL;


--
-- Name: transacciones_puntos transacciones_puntos_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transacciones_puntos
    ADD CONSTRAINT transacciones_puntos_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: usuario_aceptaciones_legales usuario_aceptaciones_legales_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_aceptaciones_legales
    ADD CONSTRAINT usuario_aceptaciones_legales_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: usuario_aceptaciones_legales usuario_aceptaciones_legales_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_aceptaciones_legales
    ADD CONSTRAINT usuario_aceptaciones_legales_version_id_fkey FOREIGN KEY (version_id) REFERENCES public.documento_legal_versiones(id) ON DELETE RESTRICT;


--
-- Name: verificacion_email verificacion_email_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.verificacion_email
    ADD CONSTRAINT verificacion_email_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: voluntario_favoritos voluntario_favoritos_fundacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT voluntario_favoritos_fundacion_id_foreign FOREIGN KEY (fundacion_id) REFERENCES public.fundaciones(id) ON DELETE CASCADE;


--
-- Name: voluntario_favoritos voluntario_favoritos_publicacion_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT voluntario_favoritos_publicacion_id_foreign FOREIGN KEY (publicacion_id) REFERENCES public.publicaciones(id) ON DELETE CASCADE;


--
-- Name: voluntario_favoritos voluntario_favoritos_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_favoritos
    ADD CONSTRAINT voluntario_favoritos_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: voluntario_habilidades voluntario_habilidades_habilidad_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_habilidades
    ADD CONSTRAINT voluntario_habilidades_habilidad_id_foreign FOREIGN KEY (habilidad_id) REFERENCES public.habilidades(id) ON DELETE CASCADE;


--
-- Name: voluntario_habilidades voluntario_habilidades_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_habilidades
    ADD CONSTRAINT voluntario_habilidades_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: voluntario_intereses voluntario_intereses_interes_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_intereses
    ADD CONSTRAINT voluntario_intereses_interes_id_foreign FOREIGN KEY (interes_id) REFERENCES public.intereses(id) ON DELETE CASCADE;


--
-- Name: voluntario_intereses voluntario_intereses_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_intereses
    ADD CONSTRAINT voluntario_intereses_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: voluntario_logros voluntario_logros_logro_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_logros
    ADD CONSTRAINT voluntario_logros_logro_id_foreign FOREIGN KEY (logro_id) REFERENCES public.logros(id) ON DELETE RESTRICT;


--
-- Name: voluntario_logros voluntario_logros_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_logros
    ADD CONSTRAINT voluntario_logros_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: voluntario_puntos voluntario_puntos_voluntario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntario_puntos
    ADD CONSTRAINT voluntario_puntos_voluntario_id_foreign FOREIGN KEY (voluntario_id) REFERENCES public.voluntarios(id) ON DELETE CASCADE;


--
-- Name: voluntarios voluntarios_municipio_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntarios
    ADD CONSTRAINT voluntarios_municipio_id_foreign FOREIGN KEY (municipio_id) REFERENCES public.municipios(id) ON DELETE RESTRICT;


--
-- Name: voluntarios voluntarios_usuario_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voluntarios
    ADD CONSTRAINT voluntarios_usuario_id_foreign FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


