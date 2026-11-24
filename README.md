# Solari — Plataforma de voluntariado (backend)

Solari conecta **voluntarios** con **organizaciones sociales** (fundaciones, refugios,
colectivos e iniciativas ciudadanas). Las organizaciones publican convocatorias, los
voluntarios se postulan, la organización confirma la asistencia y la plataforma reconoce
la trayectoria del voluntario con horas, experiencia (XP), logros y certificados.

Es un proyecto de grado del SENA con piloto en **Bogotá D.C.** (la base ya tiene datos de
Cundinamarca para crecer después).

Este README describe el sistema completo **tal como está hoy en el código**: backend,
frontend, base de datos, reglas de negocio, cumplimiento legal y pendientes. Sirve como
punto de partida para el documento de documentación y el documento legal.

## Índice

1. [Documentación relacionada](#1-documentación-relacionada)
2. [Repositorios y arquitectura](#2-repositorios-y-arquitectura)
3. [Usuarios del sistema](#3-usuarios-del-sistema)
4. [Flujo de ingreso de un usuario nuevo](#4-flujo-de-ingreso-de-un-usuario-nuevo)
5. [Módulos funcionales](#5-módulos-funcionales)
6. [Reglas de negocio clave](#6-reglas-de-negocio-clave)
7. [Documentos legales y protección de datos](#7-documentos-legales-y-protección-de-datos)
8. [Backend: stack, estructura y operación](#8-backend-stack-estructura-y-operación)
9. [Frontend (resumen)](#9-frontend-resumen)
10. [Base de datos](#10-base-de-datos)
11. [Seguridad](#11-seguridad)
12. [Pruebas e integración continua](#12-pruebas-e-integración-continua)
13. [Docker](#13-docker)
14. [Pendientes conocidos](#14-pendientes-conocidos)
15. [Cambios recientes](#15-cambios-recientes)

---

## 1. Documentación relacionada

| Documento | Contenido | Estado |
|---|---|---|
| `docs/legal/terminos_y_condiciones.md` | Términos y Condiciones de Uso, versión 1.0 | Prototipo: falta completar datos y revisión de abogado |
| `docs/legal/politica_tratamiento_datos.md` | Política de Tratamiento de Datos Personales (Ley 1581 de 2012), versión 1.0 | Prototipo: falta completar datos y revisión de abogado |
| `docs/schema.sql` | DDL completo de la base (49 tablas, llaves, índices, ENUM), listo para generar el diagrama entidad-relación | Al día |
| `docs/SOLARI-SUSTENTACION.md` | Documento de sustentación: problema, actores, módulos, seguridad | Desactualizado (ver [pendientes](#14-pendientes-conocidos)) |
| `docs/ADR-001-arquitectura-y-migracion.md` | Decisión de migrar de Laravel a FastAPI sin romper la base | Vigente |
| `docs/API-ENDPOINTS.md` | Contrato de los endpoints de **autenticación** y legal | Solo cubre autenticación; la lista completa está en `/docs` (Swagger) |
| `docs/INSTALACION.md` | Instalación y operación en Windows, correo, Google OAuth, rollback | Vigente |
| `docs/TRASPASO-DOCUMENTO-GRADO.md` | Relación con el documento de grado | Vigente |
| `../Solary frontend/README.md` | Detalle del frontend: rutas, guardias, tutorial, páginas legales | Al día |

La documentación interactiva de la API (todos los endpoints, con esquemas de entrada y
salida) está en `http://localhost:9000/docs` con el backend encendido.

---

## 2. Repositorios y arquitectura

El proyecto vive en tres carpetas hermanas:

| Carpeta | Qué es | Estado |
|---|---|---|
| `Solary backend/` | API REST en **Python 3.14 + FastAPI** (este repo) | **Activo** |
| `Solary frontend/` | Aplicación web en **React 19 + Vite + TypeScript** | **Activo** |
| `Proyecto/` | Versión original en **Laravel (PHP) + Vue** y el script SQL inicial (`voluntapp_mvp.sql`) | Heredado, solo referencia |

Las carpetas se llaman `Solary …` (con *y*), igual que los repos de GitHub; el producto
se llama **Solari**.

La base de datos PostgreSQL (`voluntapp`) la creó el backend Laravel. El backend Python
trabaja sobre **la misma base**, con migraciones **aditivas** (no borra ni renombra
tablas o columnas) y JWT compatibles con el backend anterior y con la app móvil Flutter.

```
┌─────────────────────────┐   HTTP/JSON + JWT Bearer   ┌─────────────────────────┐
│  Solary frontend         │ ─────────────────────────▶ │  Solary backend          │
│  React 19 · Vite · TS    │ ◀───────────────────────── │  FastAPI · SQLAlchemy 2  │
│  http://localhost:5173   │   SSE (notificaciones)     │  http://localhost:9000   │
└─────────────────────────┘                            └────────────┬────────────┘
                                                                     │ psycopg 3 (async)
                                                                     ▼
                                                        ┌─────────────────────────┐
                                                        │ PostgreSQL · voluntapp   │
                                                        └─────────────────────────┘
```

---

## 3. Usuarios del sistema

| Rol (en código) | Quién es | Qué hace |
|---|---|---|
| `VOLUNTARIO` | Persona natural de 16 años o más | Completa su perfil, elige intereses y habilidades, explora y se postula a convocatorias, guarda favoritos, gana XP y logros, ve su trayectoria, descarga certificados, ofrece objetos o servicios gratuitos y abre tickets de soporte |
| `FUNDACION` | Organización social (fundación, refugio, colectivo, iniciativa ciudadana u otra) | Publica convocatorias individuales o recurrentes, revisa postulaciones con su porcentaje de compatibilidad, registra asistencia y califica al terminar la actividad, mantiene un perfil público con galería, solicita la verificación documental y pide objetos o servicios a voluntarios |
| `ADMIN` | Personal de Solari | Gestiona usuarios, organizaciones, convocatorias, postulaciones y catálogos; responde soporte; resuelve solicitudes de privacidad; aprueba autorizaciones de acudientes; otorga la insignia de verificación; modera reseñas. Todas sus acciones quedan en auditoría |

---

## 4. Flujo de ingreso de un usuario nuevo

Ningún usuario entra al panel sin pasar por estos pasos. El frontend los encadena con
guardias de rutas y **la API también los exige**, así que no se pueden saltar llamando al
backend directamente.

```
1. Registro (/registro)
   ├─ Voluntario: primer nombre*, segundo nombre, primer apellido*, segundo apellido,
   │  correo, contraseña, documento, fecha de nacimiento (≥ 16 años), género,
   │  municipio, disponibilidad, teléfono (opcional)
   ├─ Organización: datos institucionales (NIT y documento legal si está constituida)
   └─ Casilla obligatoria: acepta Términos y Política de datos → se guarda la evidencia
          │
          ▼
2. Confirmar correo (/verifica-tu-correo)
   ├─ Se envía un enlace /verify-email?token=… válido por 24 horas
   ├─ Botones: "Ya confirmé mi correo", "Reenviar correo" (máx. 5 por hora), "Cerrar sesión"
   └─ La API responde 403 "Confirma tu correo electrónico para continuar" a todo,
      salvo /auth/me, /auth/resend-verification, /auth/logout y /auth/revoke-refresh
          │
          ▼
3. Completar perfil (/completar-perfil) — solo voluntarios
   └─ Obligatorios: teléfono de contacto, dirección de residencia,
      nombre y teléfono del contacto de emergencia
          │
          ▼
4. Panel (/app) → se abre el tutorial de bienvenida la primera vez
```

- Los administradores no pasan por los pasos 2 y 3.
- Las cuentas de Google llegan con el correo verificado, así que saltan el paso 2.
- Si alguien cierra el navegador a medias, al volver a iniciar sesión lo devuelve al paso
  que le falta.
- El nombre se pide en cuatro campos, pero se guarda unido en `usuarios.nombre`
  (por ejemplo, "Ana María Pérez Gómez"). No hay columnas separadas por ahora.

---

## 5. Módulos funcionales

| Módulo | Qué hace | Reglas importantes |
|---|---|---|
| Autenticación | Registro (voluntario / organización), login, Google OIDC, verificación de correo con reenvío, recuperación de contraseña, refresh token | Argon2id (con rehash de bcrypt heredado); refresh con rotación y un solo uso; mensajes que no revelan si una cuenta existe; aceptación de documentos legales con evidencia; API bloqueada hasta confirmar el correo |
| Perfil del voluntario | Datos personales, contacto, contacto de emergencia, foto, documento de identidad | Teléfono, dirección y contacto de emergencia (nombre y teléfono) son **obligatorios**. Documento, fecha de nacimiento y género **no se editan** después del registro; se corrigen por solicitud a soporte |
| Perfil de la organización | Datos institucionales, logo | NIT y documento legal solo si está constituida legalmente. Nombre, tipo de organización, NIT, representante legal y documento legal **no se editan** desde el perfil; se corrigen por soporte |
| Convocatorias | Crear (borrador), publicar, editar, cancelar. Campos ricos: objetivo, impacto, actividades, beneficiarios, qué llevar, recomendaciones, política de cancelación, beneficios, horas, certificado, dificultad, urgente | Para publicar exige entre 3 y 10 habilidades. Estados: `BORRADOR`, `PENDIENTE_APROBACION`, `PUBLICADA`, `CERRADA`, `CANCELADA`, `COMPLETADA`, `FINALIZADA` |
| Galería de convocatorias | Hasta 8 fotos por convocatoria; la primera es la portada | Tabla `publicacion_imagenes`; la portada también se guarda en `publicaciones.imagen` |
| Postulaciones | Postularse, retirarse, responder (aceptar, revisión, lista de espera, rechazar), registrar asistencia con calificación 1–5 | Cupos con bloqueo de fila (`SELECT … FOR UPDATE`); sin duplicados; no se postula después de la fecha límite; sin cupo entra en lista de espera. **La asistencia y la calificación solo se registran cuando la actividad terminó** |
| Habilidades y compatibilidad | Catálogo de 108 habilidades en 7 categorías | El voluntario elige 3–10. Compatibilidad = coincidentes / requeridas × 100. Ordena el listado, **nunca** impide postularse |
| Intereses y recomendaciones | Catálogo de intereses; recomendaciones por afinidad | Puntúa categoría, municipio, modalidad, cupo y cercanía de la fecha |
| Gamificación | XP, 8 niveles, 11 logros, ranking top 1000 | XP **solo** al confirmar asistencia: 50 + 5 por hora reconocida. Idempotente; cada logro se gana una vez |
| Favoritos | Convocatorias y organizaciones | Persisten en la base, sin duplicados |
| Notificaciones | Avisos internos por eventos reales, en vivo por SSE | El usuario configura preferencias por tipo; no se envían por correo. Cada notificación lleva `objeto_tipo` y `objeto_id` (y `publicacion_id` en las de postulación) para que el frontend lleve al lugar exacto, por ejemplo al chat |
| Actividades recurrentes | Programación por días, semanas o meses | Máximo 3 convocatorias por ciclo; luego se pausa hasta que la organización autorice |
| Objetos y servicios | El voluntario publica objetos (con estado, forma de entrega, municipio y cantidad) o servicios (con modalidad y habilidades); la organización pulsa "Me interesa" y coordinan por mensajes | Siempre gratuitos (se rechazan precios y términos comerciales); los mensajes bloquean correos, teléfonos y enlaces; la entrega se completa solo si **ambas partes** confirman. La lista indica `ya_solicitado` para que la organización no repita la solicitud |
| Perfil público y verificación | Historia, misión, áreas de impacto, galería, contacto visible a elección, estadísticas reales; documentos privados para verificación | La insignia la otorga un administrador y se muestra con aviso de que no es garantía absoluta |
| Reseñas | El voluntario reseña a la organización | Solo con participación confirmada; la organización responde; el admin puede ocultar con motivo |
| Soporte y privacidad | Tickets con hilo de mensajes; solicitudes de cuenta (bloqueo temporal, inhabilitación, eliminación de cuenta o de datos, reportes de acceso sospechoso) | Las solicitudes de privacidad requieren orden explícita del admin. La eliminación **anonimiza** (ver [sección 7](#7-documentos-legales-y-protección-de-datos)) |
| Trayectoria | Actividades, horas, organizaciones y XP del voluntario | Calculada con registros reales |
| Edad mínima y menores | Registro desde los **16 años**; de 16 a 17 el acudiente firma y se sube su autorización | Regla única en `app/core/edad.py` (`EDAD_MINIMA = 16`, `MAYORIA_EDAD = 18`). Un menor puede postularse, pero la organización no puede aceptarlo hasta que un administrador apruebe la autorización |
| Certificados | PDF descargable cuando la asistencia está confirmada y la convocatoria otorga certificado | Código de verificación HMAC (no se guarda); verificación pública en `/certificados/verificar` |
| Calendario | Próximas actividades; exportación `.ics` | Recordatorio automático antes de cada actividad aceptada |
| Mensajes de postulación | Chat entre voluntario y organización dentro de una postulación | Mismo filtro de datos personales que objetos y servicios |
| Seguridad de la cuenta | Sesiones y dispositivos activos, cerrar sesiones, verificación en dos pasos (TOTP) | Alerta al iniciar sesión desde un dispositivo nuevo |
| Documentos legales | Términos y Política de datos versionados, con evidencia de aceptación | Ver [sección 7](#7-documentos-legales-y-protección-de-datos) |
| Tutorial de bienvenida | Recorrido guiado por los módulos del menú (solo frontend) | Ver `../Solary frontend/README.md` |

### Ciclo de una participación

```
1. La organización se registra, confirma su correo y el admin la verifica
2. Crea una convocatoria (BORRADOR), agrega fotos y la PUBLICA
3. El voluntario se registra, confirma su correo, completa su perfil, intereses y habilidades
4. Explora (ordenado por compatibilidad) y se postula → PENDIENTE o LISTA_ESPERA
5. La organización acepta o rechaza → notificación al voluntario
   (un menor de 16–17 solo puede ser aceptado con la autorización del acudiente aprobada)
6. Cuando la actividad TERMINA, la organización registra la asistencia
   (ASISTIO con calificación 1–5, o NO_ASISTIO)
7. El voluntario recibe XP, se evalúan logros y se actualizan horas, trayectoria,
   ranking y, si aplica, el certificado
```

---

## 6. Reglas de negocio clave

Resumen de las reglas que el backend hace cumplir (no dependen del frontend). Entre
paréntesis, dónde están en el código.

| Regla | Detalle | Dónde |
|---|---|---|
| Edad mínima | 16 años; de 16 a 17 se exige autorización del acudiente aprobada por un admin para ser aceptado | `app/core/edad.py`, `menores_service.py` |
| Correo confirmado | Sin correo confirmado la API solo permite `/auth/me`, `/auth/resend-verification`, `/auth/logout` y `/auth/revoke-refresh` (admins exentos) | `app/api/deps.py` (`get_current_user`) |
| Perfil de voluntario | Dirección (≥ 4 caracteres), teléfono y contacto de emergencia (nombre y teléfono) obligatorios; teléfonos de 7 a 20 caracteres (`0-9 + - espacio`) | `app/schemas/perfil.py` (`VoluntarioPerfilInput`) |
| Datos de identidad inmutables | Voluntario: documento, fecha de nacimiento y género. Organización: nombre, tipo, NIT, representante legal y documento legal | `perfil_service.py` |
| Aceptación legal | Si hay documentos publicados como requeridos, el registro exige aceptarlos; el backend fija versión, fecha, IP y navegador | `legal_service.py` |
| Asistencia | Solo para postulaciones aceptadas y **después de que la actividad termina** (fecha y hora de fin en hora de Bogotá, o al final del día si no hay hora; o si la convocatoria está `FINALIZADA`/`COMPLETADA`) | `postulacion_service.py` (`actividad_terminada`) |
| XP | Solo por asistencia confirmada: 50 + 5 por hora reconocida; idempotente | `gamificacion_service.py` |
| Cupos | Bloqueo de fila; sin cupo pasa a lista de espera | `postulacion_service.py` |
| Gratuidad | Objetos y servicios sin precios, ventas ni cobros (filtro de términos comerciales) | `app/schemas/ofrecimiento.py` |
| Solicitudes duplicadas | Una organización no puede tener dos solicitudes activas sobre la misma publicación | `ofrecimiento_service.py` |
| Datos personales en mensajes | Se bloquean correos, teléfonos y enlaces en los chats | `mensaje_postulacion_service.py`, `ofrecimiento_service.py` |
| Contraseña | Mínimo 8 caracteres, mayúscula, minúscula y número | `app/schemas/auth.py` |

---

## 7. Documentos legales y protección de datos

Esta sección resume lo necesario para el documento legal.

### 7.1 Documentos

| Código | Documento | Archivo fuente | Página pública |
|---|---|---|---|
| `TERMINOS_CONDICIONES` | Términos y Condiciones de Uso (16 secciones) | `docs/legal/terminos_y_condiciones.md` | `http://localhost:5173/terminos` |
| `POLITICA_DATOS_PERSONALES` | Política de Tratamiento de Datos Personales (14 secciones) | `docs/legal/politica_tratamiento_datos.md` | `http://localhost:5173/privacidad` |

Marco legal citado: **Ley 1581 de 2012** y **Decreto 1377 de 2013** (protección de datos),
**Ley 720 de 2001** y **Decreto 4290 de 2005** (voluntariado), **Ley 1098 de 2006**
(infancia y adolescencia) y **Ley 527 de 1999** (mensajes de datos).

Los dos documentos son un **prototipo inicial**. Antes de publicarlos de verdad hay que:

1. Completar los datos entre corchetes: `[NOMBRE O RAZÓN SOCIAL]`, `[NIT / C.C.]`,
   `[DIRECCIÓN, CIUDAD]`, `[CORREO DE CONTACTO]`, `[CORREO DE PROTECCIÓN DE DATOS]`,
   `[TELÉFONO]`, `[FECHA DE PUBLICACIÓN]`, `[PROVEEDOR DE HOSTING / PAÍS]`,
   `[PROVEEDOR DE CORREO / PAÍS]`, `[PLAZO]` de conservación y `[CIUDAD]` de jurisdicción.
2. Hacerlos revisar por un abogado.
3. Quitar el aviso de "prototipo" y publicar una versión nueva (ver 7.2).

### 7.2 Cómo se publican y versionan

El texto vive en los `.md` (en git) y se carga a la base con un script:

```powershell
uv run python scripts/seed_documentos_legales.py                 # publica la versión 1.0
uv run python scripts/seed_documentos_legales.py --version 1.1   # publica una versión nueva
uv run python scripts/seed_documentos_legales.py --opcional      # visibles pero no exigidos en el registro
```

- Guarda el contenido y su hash SHA-256 en `documento_legal_versiones`, y deja solo una
  versión **vigente** por documento.
- Es idempotente: si el contenido no cambió, no hace nada.
- Si una versión ya fue aceptada por algún usuario y su texto cambió, **se niega a
  sobrescribirla** y pide una versión nueva. Así la evidencia de cada aceptación siempre
  apunta al texto exacto que se aceptó.
- Estado actual de la base local: versión **1.0** de ambos documentos publicada y
  **requerida** en el registro.
- El frontend la lee de `GET /api/v1/legal/documentos` (público, sin sesión).

### 7.3 Evidencia de aceptación

Al registrarse, el frontend envía `aceptaciones: [{codigo, aceptado}]`. El backend
(`legal_service.py`):

1. Rechaza el registro (409) si falta algún documento requerido.
2. Resuelve la versión **vigente** de cada documento (el cliente no puede elegir versión).
3. Guarda en `usuario_aceptaciones_legales`: usuario, versión, fecha (del servidor), IP y
   navegador.

### 7.4 Qué datos se tratan y quién los ve

| Dato | Quién lo ve |
|---|---|
| Nombre, foto, municipio, disponibilidad, experiencia, descripción, idiomas, profesión, habilidades, horas, XP, estado de verificación | La organización a la que el voluntario se postula |
| Número de documento, dirección, correo, teléfono, contacto de emergencia | **No** se muestran a las organizaciones en el listado de postulantes |
| Documento de identidad y autorización del acudiente (archivos) | Solo el dueño y los administradores (almacenamiento privado) |
| Primer nombre | Otros usuarios en objetos y servicios |
| IP y navegador | Evidencia de aceptación legal, sesiones y alertas de dispositivo nuevo |

### 7.5 Eliminación y anonimización

Cuando un admin ejecuta una solicitud de eliminación de cuenta o de datos
(`admin_gestion_service.py`, `_anonimizar`):

- Se reemplazan nombre ("Usuario anonimizado") y correo (`anonimo-<id>@anonimizado.invalid`);
  se borran teléfono, número de documento, foto, documento de identidad (también el
  archivo), dirección, descripción, contacto de emergencia y demás datos de perfil.
- La cuenta queda bloqueada y con una contraseña aleatoria inutilizable.
- Se retiran las publicaciones de objetos y servicios disponibles.
- Se **conservan** sin identidad los registros con valor histórico o legal: participación,
  horas y certificados emitidos.

### 7.6 Pendientes legales

- El registro con **Google** no pasa por la casilla de aceptación: esas cuentas no tienen
  evidencia de aceptación. Falta un paso para que acepten al primer ingreso.
- Si la **app móvil Flutter** no envía `aceptaciones`, su registro falla mientras los
  documentos estén como requeridos (solución temporal: `--opcional`).
- Al publicar una versión nueva, los usuarios existentes no tienen todavía un flujo para
  aceptar la nueva versión.
- Definir los plazos de conservación y, cuando aplique, inscribir las bases de datos en
  el Registro Nacional de Bases de Datos (RNBD) de la SIC.

---

## 8. Backend: stack, estructura y operación

### Stack

Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2 async · psycopg 3 · Alembic ·
argon2-cffi · PyJWT (HS256) · slowapi (rate limiting) · google-auth · uvicorn ·
gestor de entorno **uv**.

### Estructura por capas

```
app/
├── main.py          # Crea la app: CORS, rate limit, routers, /uploads público
├── core/            # config (.env), security (hash/JWT), exceptions, rate_limit, edad, mfa
├── db/              # Motor y sesión async
├── models/          # Tablas ORM (usuario, voluntario, fundacion, publicacion, legal…)
├── schemas/         # Entrada/salida Pydantic (extra="forbid" en las entradas)
├── repositories/    # Consultas a la base
├── services/        # Reglas de negocio (una clase por módulo)
├── api/v1/          # Endpoints REST, uno por módulo; deps.py = sesión y permisos
└── email/           # Envío de correos (console o SMTP)
alembic/versions/    # 0001 → 0007 (todas aditivas)
scripts/             # Semillas de datos y publicación de documentos legales
docs/                # Documentación, DDL y documentos legales
uploads/             # Archivos públicos (fotos, logos, galería, ofrecimientos, convocatorias)
private_uploads/     # Documentos privados (identidad, verificación, autorizaciones)
backups/             # Respaldos locales de la base (no se suben al repo)
tests/               # Pruebas (pytest)
```

Flujo de una petición: **endpoint** (`api/v1`) → **service** (reglas) →
**repository** (datos) → **model**; responde con un **schema**.

### Routers (`app/api/v1/`, todos bajo `/api/v1`)

`auth`, `perfil`, `publicaciones`, `postulaciones`, `mensajes_postulacion`, `favoritos`,
`gamificacion`, `habilidades`, `notificaciones`, `programaciones`, `ofrecimientos`,
`organizaciones`, `calendario`, `certificados`, `menores`, `seguridad`, `soporte`,
`cuenta`, `catalogos`, `legal`, `archivos` (descarga autenticada de archivos privados),
`admin`, `admin_gestion`, `health`.

Endpoints que cambiaron hace poco y vale la pena conocer:

| Endpoint | Qué hace |
|---|---|
| `POST /auth/resend-verification` | Reenvía el correo de verificación al usuario autenticado (5 por hora) |
| `GET /auth/verify-email/{token}` | Confirma el correo (el enlace del correo apunta al frontend con `?token=`) |
| `GET /legal/documentos` | Documentos legales vigentes, con su contenido en markdown |
| `GET /notificaciones` | Ahora incluye `publicacion_id` en las notificaciones de postulación |
| `GET /ofrecimientos` y `GET /ofrecimientos/{id}` | Ahora incluyen `ya_solicitado` para la organización autenticada |
| `POST /postulaciones/{id}/confirmar-asistencia` | Responde 409 si la actividad aún no ha terminado |
| `PUT /perfil/voluntario` | Responde 422 si faltan teléfono, dirección o contacto de emergencia |
| `PUT /perfil/fundacion` | Responde 403 si se intentan cambiar los datos legales |

### Archivos subidos

- `StorageService` valida el tipo real por *magic bytes*, limita el tamaño
  (`UPLOAD_MAX_MB`, 5 MB por defecto) y usa nombres aleatorios.
- Solo se sirven públicamente las carpetas `fotos`, `logos`, `ofrecimientos`, `galeria` y
  `convocatorias` bajo `/uploads`.
- Los documentos privados solo se descargan por `/archivos/privado`, con sesión y control
  de propiedad.

### Variables de entorno (`.env`, ver `.env.example`)

| Variable | Valor por defecto | Uso |
|---|---|---|
| `DATABASE_URL` | — | Conexión a PostgreSQL (`postgresql+psycopg://…/voluntapp`) |
| `JWT_SECRET` | — | Secreto de firma; el mismo que el backend Laravel para compatibilidad |
| `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_PROVIDER_MODEL` | `HS256`, … | Compatibilidad del token con Laravel y la app móvil |
| `JWT_ACCESS_TTL_MINUTES` / `JWT_REFRESH_TTL_MINUTES` | `60` / `20160` (14 días) | Vigencia de los tokens |
| `CORS_ORIGINS` | vacío | Orígenes permitidos (incluir `http://localhost:5173`) |
| `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTER`, `RATE_LIMIT_FORGOT_PASSWORD`, `RATE_LIMIT_RESET_PASSWORD` | `5/minute`, `10/hour`, `3/hour`, `5/hour` | Límites anti abuso |
| `MAIL_BACKEND` | `console` | `console` imprime los correos en la terminal del backend (útil en desarrollo para copiar el enlace de verificación); `smtp` los envía de verdad |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`, `MAIL_FROM_ADDRESS`, `MAIL_FROM_NAME` | — | Servidor SMTP (ver `docs/INSTALACION.md`, sección 8) |
| `FRONTEND_VERIFY_URL` / `FRONTEND_RESET_URL` | `http://localhost:5173/verify-email` / `…/reset-password` | Enlaces que van en los correos |
| `GOOGLE_CLIENT_ID`, `GOOGLE_ALLOWED_AUDIENCES` | vacío | Inicio de sesión con Google |
| `PASSWORD_MIN_LENGTH` | `8` | Longitud mínima de contraseña |
| `UPLOAD_DIR` / `PRIVATE_UPLOAD_DIR` / `UPLOAD_MAX_MB` | `uploads` / `private_uploads` / `5` | Archivos subidos |
| `UPLOAD_PUBLIC_BASE` | `http://localhost:9000/uploads` | Base de las URLs públicas de archivos |
| `REMINDERS_ENABLED` | `true` | Recordatorios automáticos de actividades |
| `SOLARI_HOST` / `SOLARI_PORT` | `127.0.0.1` / `9000` | Dirección y puerto de `run.py` |

Nunca subas el `.env` real al repositorio.

### Arranque (Windows)

```powershell
cd "Solary backend"
uv venv --python 3.14
uv sync
copy .env.example .env        # completar DATABASE_URL y JWT_SECRET
uv run alembic upgrade head   # migraciones aditivas
uv run python run.py          # http://127.0.0.1:9000  ·  Swagger: /docs
```

- En Windows se usa `run.py` porque fija el *event loop* Selector que necesita psycopg async.
- El puerto es **9000** (8001 y 8080 suelen estar reservados por Hyper-V).
- `run.py` arranca **sin recarga automática**: después de cambiar código del backend hay
  que detenerlo (Ctrl+C) y volver a ejecutarlo.
- Corre **una sola** instancia: dos procesos en el mismo puerto dan resultados confusos.

### Scripts (`scripts/`, todos idempotentes)

```powershell
uv run python scripts/seed_documentos_legales.py  # Términos y Política de datos (ver sección 7)
uv run python scripts/seed_habilidades.py         # 108 habilidades
uv run python scripts/seed_intereses.py           # intereses del voluntario
uv run python scripts/seed_areas_impacto.py       # 32 áreas de impacto (corrige tildes)
uv run python scripts/seed_ofrecimientos.py       # 6 objetos y 5 servicios de ejemplo
uv run python scripts/seed_convocatoria_demo.py   # convocatoria con 5 fotos para fundacion1@demo.com
uv run python scripts/migrar_documentos_privados.py  # mueve documentos antiguos al almacenamiento privado
```

`seed_convocatoria_demo.py` necesita las fotos en `uploads/convocatorias/` (Wikimedia
Commons: tres de dominio público y dos CC BY-SA 4.0). Las cuentas de prueba están en
`Proyecto/CREDENCIALES_ACCESO.md`.

---

## 9. Frontend (resumen)

React 19 · Vite 8 · TypeScript 6 · Tailwind CSS v4 · React Router 7 · Axios · React Hook
Form + Zod · Framer Motion · Vitest. Corre en `http://localhost:5173` y apunta a
`http://localhost:9000/api/v1`.

El detalle (rutas, guardias del flujo de ingreso, tutorial de bienvenida, páginas legales,
validaciones y pruebas) está en **`../Solary frontend/README.md`**.

---

## 10. Base de datos

PostgreSQL, base `voluntapp`. **50 tablas**: las 49 de `docs/schema.sql` más
`alembic_version` (registro de migraciones de Alembic; no se debe borrar). Usa UUID como
clave en las entidades principales, ENUM nativos para roles y estados, llaves foráneas con
`CASCADE`, `RESTRICT` o `SET NULL`, y restricciones `CHECK`.

| Grupo | Tablas |
|---|---|
| Cuentas y sesión | `usuarios`, `voluntarios`, `fundaciones`, `admin_perfiles`, `refresh_tokens`, `verificacion_email`, `recuperacion_password`, `auditoria_perfil` |
| Convocatorias | `publicaciones`, `publicacion_habilidades`, `publicacion_imagenes`, `postulaciones`, `postulacion_historial`, `programaciones_recurrentes`, `mensajes_postulacion` |
| Voluntario | `voluntario_habilidades`, `voluntario_intereses`, `voluntario_favoritos`, `voluntario_puntos`, `transacciones_puntos`, `voluntario_logros`, `historial_estados_voluntario`, `advertencias_voluntario` |
| Organización | `fundacion_areas`, `fundacion_galeria`, `fundacion_documentos`, `resenas_organizacion`, `historial_estados_fundacion` |
| Objetos y servicios | `ofrecimientos`, `ofrecimiento_habilidades`, `solicitudes_interes`, `mensajes_interes` |
| Comunicación y soporte | `notificaciones`, `preferencias_notificacion`, `tickets_soporte`, `ticket_mensajes`, `solicitudes_cuenta`, `reportes` |
| Legal | `documentos_legales`, `documento_legal_versiones`, `usuario_aceptaciones_legales` |
| Administración | `admin_acciones`, `configuracion_sistema` |
| Catálogos | `departamentos`, `municipios`, `areas_impacto`, `habilidades`, `intereses`, `logros` |

### Diagrama entidad-relación

`docs/schema.sql` tiene el DDL completo (tablas, llaves primarias y foráneas, `UNIQUE`,
`CHECK`, índices y ENUM), generado con `pg_dump --schema-only`. Se puede importar en
dbdiagram.io, draw.io, pgAdmin, DBeaver o DataGrip. Para regenerarlo:

```powershell
pg_dump -h 127.0.0.1 -U postgres -d voluntapp --schema-only --no-owner --no-privileges --no-comments -f docs/schema.sql
```

Después hay que quitar las líneas `\restrict` / `\unrestrict` que agrega `pg_dump` 18 y la
tabla `alembic_version` si no se quiere en el diagrama.

### Limpieza de tablas de Laravel

Se borraron de la base local las tablas internas de Laravel que este backend no usa:
`cache`, `cache_locks`, `jobs`, `job_batches`, `failed_jobs`, `migrations`, `sessions` y
`personal_access_tokens`. Antes se hizo un respaldo completo en
`backups/antes_de_limpiar_tablas_laravel.dump` (restaurable con `pg_restore`). Si la app
Laravel de `Proyecto/` vuelve a usar esta base, necesitará esas tablas.

---

## 11. Seguridad

- Consultas parametrizadas con el ORM; entradas con `extra="forbid"` (sin asignación masiva).
- El rol y el estado los fija el backend; el cliente nunca puede darse ADMIN.
- Contraseñas con Argon2id; verificación en dos pasos (TOTP) opcional.
- JWT con algoritmo fijo; refresh token hasheado, rotado y de un solo uso.
- API bloqueada hasta confirmar el correo.
- Rate limiting en login, registro, recuperación y reenvío de verificación.
- Bloqueo de fila para cupos y cantidades.
- Archivos validados por contenido; documentos privados fuera de `/uploads`.
- Alertas de inicio de sesión desde dispositivo nuevo; bitácora de acciones de admin.
- Errores centralizados sin trazas ni SQL; CORS con orígenes explícitos.
- Detalle en `docs/SOLARI-SUSTENTACION.md`, sección 9.

---

## 12. Pruebas e integración continua

```powershell
uv run pytest     # 187 pruebas; necesita PostgreSQL para las de base de datos
```

| Archivo | Qué prueba | ¿Necesita BD? |
|---|---|---|
| `tests/integration/test_reglas_documento.py` | Reglas del documento de grado de punta a punta | Sí |
| `tests/test_auth_flow.py` | Registro, login, refresh, logout, recuperación | Sí |
| `tests/test_aceptacion_legal.py` | El registro exige aceptar los documentos y guarda la evidencia | Sí |
| `tests/test_onboarding_api.py` | La API bloquea a quien no confirmó el correo | Sí |
| `tests/test_reglas_onboarding.py` | Perfil obligatorio y cálculo de fin de actividad | No |
| `tests/test_edad_minima.py`, `test_menores.py` | Edad mínima y autorización del acudiente | No |
| `tests/test_certificados.py`, `test_calendario.py`, `test_mensajes_sse.py` | Certificados, calendario, mensajes y SSE | No |
| `tests/test_security.py`, `test_seguridad.py`, `test_jwt_coexistencia.py` | Hash, JWT, MFA y compatibilidad con Laravel | No |
| `tests/test_unidades_alineacion.py` | Unidades de los módulos de alineación | No |

La base de pruebas se crea desde cero con el esquema de `tests/conftest.py`. Si se agrega
una columna a un modelo, hay que agregarla también ahí.

**CI** (`.github/workflows/ci.yml`, en push y PR a `master`): `uv sync`, `ruff check app
tests` y las pruebas que no necesitan base de datos (148). Se excluyen
`tests/integration`, `test_auth_flow.py`, `test_aceptacion_legal.py` y
`test_onboarding_api.py`. Ruff ignora por ahora `E501,I001,C416,C408,S608,S311`, que tienen
errores previos en el código.

---

## 13. Docker

`docker-compose.yml` levanta tres servicios:

| Servicio | Qué hace | Puerto en el equipo |
|---|---|---|
| `db` | PostgreSQL 16 con la base `voluntapp`. En el primer arranque ejecuta el script de `DB_INIT_SQL` | `5433` |
| `backend` | Imagen de este repo. Ejecuta `alembic upgrade head` y `uvicorn` en `0.0.0.0:9000` | `9000` |
| `frontend` | Compila con Vite y sirve `dist/` con nginx | `5173` |

```powershell
cd "Solary backend"
copy .env.docker.example .env.docker   # cambiar POSTGRES_PASSWORD, DATABASE_URL y JWT_SECRET
docker compose up --build
```

- `.env.docker` está en `.gitignore`. El backend no arranca si `JWT_SECRET` sigue
  empezando por `cambia-esto`.
- Variables opcionales: `DB_INIT_SQL` (por defecto `../Proyecto/voluntapp_mvp.sql`),
  `FRONTEND_DIR`, `VITE_API_BASE_URL`, `VITE_GOOGLE_CLIENT_ID`.
- `voluntapp_mvp.sql` no tiene todas las tablas que crearon después las migraciones de
  Laravel, así que con él `alembic upgrade head` falla. Usa un volcado de la base local:

```powershell
pg_dump -U postgres -h 127.0.0.1 -d voluntapp --no-owner --no-privileges -f voluntapp_dump.sql
$env:DB_INIT_SQL="$PWD\voluntapp_dump.sql"
docker compose up --build
```

- Después de cargar la base en Docker, publica los documentos legales con
  `seed_documentos_legales.py`. No subas el volcado a ningún repositorio: contiene cuentas
  y datos personales.
- `docker compose down -v` **borra** los datos y archivos de los volúmenes.

---

## 14. Pendientes conocidos

**Legal** (ver [7.6](#76-pendientes-legales)): completar datos y revisión de abogado;
aceptación en el registro con Google; aceptación en la app móvil; flujo para aceptar
versiones nuevas; plazos de conservación y RNBD.

**Producto**
- 25 voluntarios de prueba de la base local tienen el correo sin confirmar y quedan
  bloqueados por la regla de correo. Se pueden marcar como verificados si se usan para
  probar.
- El tutorial recuerda que ya se vio solo en el navegador (`localStorage`); en otro
  dispositivo se muestra de nuevo una vez.
- El nombre se guarda unido; si se necesitan nombres y apellidos por separado, hay que
  agregar columnas y una migración.
- Las calificaciones registradas antes de la regla de "solo al terminar la actividad" se
  conservan tal cual.

**Documentación**
- `docs/SOLARI-SUSTENTACION.md` menciona el puerto 8080 y 11 áreas de impacto, y no incluye
  los módulos nuevos (certificados, calendario, mensajes, seguridad, menores, flujo de
  ingreso, documentos legales, tutorial).
- `docs/API-ENDPOINTS.md` solo cubre autenticación; el resto está en `/docs`.

**Técnico**
- Las pruebas que usan base de datos no corren en CI.
- En una corrida local aparecieron 4 fallos que no se repitieron en tres corridas
  siguientes; si vuelve a pasar, revisar si dos procesos usan la base de pruebas a la vez.

---

## 15. Cambios recientes

Resumen de lo agregado en la última etapa, para incluirlo en la documentación:

| Área | Cambio |
|---|---|
| Flujo de ingreso | Pantallas de confirmar correo y completar perfil antes del panel; barra de "sesión iniciada" con cerrar sesión e indicador de pasos; reenvío del correo |
| API | Bloqueo de la API hasta confirmar el correo; `POST /auth/resend-verification` |
| Perfil | Teléfono, dirección y contacto de emergencia obligatorios (frontend y API); datos legales de la organización no editables |
| Registro | Nombre en cuatro campos (primer y segundo nombre, primer y segundo apellido); alerta que explica cada error del formulario; corrección del enlace de verificación (`/verify-email?token=`) |
| Postulaciones | La asistencia y la calificación solo se registran al terminar la actividad; rediseño de "Mis postulaciones" con pestañas |
| Notificaciones | Al tocar una notificación lleva al lugar exacto (chat, ticket, postulaciones, etc.) |
| Objetos y servicios | Formulario completo (estado, entrega, municipio, habilidades); "Solicitud enviada" en lugar de repetir "Me interesa" |
| Explorar | Botón "Limpiar filtros" |
| Legal | Términos y Política de datos versión 1.0, páginas `/terminos` y `/privacidad`, aceptación obligatoria con evidencia, script de publicación |
| Tutorial | Recorrido guiado por los módulos, distinto para voluntario y organización, repetible desde "Ver tutorial" |
| Base de datos | `docs/schema.sql` con el DDL completo; borradas las tablas internas de Laravel (con respaldo) |
| Pruebas | Nuevas pruebas de onboarding, aceptación legal y fin de actividad; esquema de pruebas con las columnas del acudiente |
