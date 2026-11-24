# Solari — Plataforma de voluntariado

Solari conecta **voluntarios** con **organizaciones sociales** (fundaciones, refugios,
colectivos e iniciativas ciudadanas) para publicar convocatorias de voluntariado,
postularse, confirmar la asistencia y reconocer la trayectoria del voluntario.
Es un proyecto de grado del SENA con piloto en **Bogotá D.C.** (la base ya tiene
datos de Cundinamarca para crecer después).

Este README describe el sistema completo tal como está hoy en el código. La
documentación más detallada está en `docs/`:

| Documento | Contenido |
|---|---|
| `docs/SOLARI-SUSTENTACION.md` | Documento de sustentación: problema, actores, módulos, seguridad |
| `docs/ADR-001-arquitectura-y-migracion.md` | Decisión de migrar de Laravel a FastAPI sin romper la base |
| `docs/API-ENDPOINTS.md` | Lista de endpoints |
| `docs/INSTALACION.md` | Instalación y operación en Windows |
| `docs/TRASPASO-DOCUMENTO-GRADO.md` | Relación con el documento de grado |

---

## 1. Repositorios y carpetas

El proyecto vive en tres carpetas hermanas:

| Carpeta | Qué es | Estado |
|---|---|---|
| `Solari backend/` | API REST en **Python 3.14 + FastAPI** | **Activo** |
| `Solari frontend/` | Aplicación web en **React 19 + Vite + TypeScript** | **Activo** |
| `Proyecto/` | Versión original en **Laravel (PHP) + Vue** y el script SQL inicial (`voluntapp_mvp.sql`) | Heredado, solo referencia |

La base de datos PostgreSQL (`voluntapp`) la creó el backend Laravel. El backend
Python trabaja sobre **la misma base**, con migraciones **aditivas** (no borra ni
renombra tablas o columnas) y JWT compatibles, así que ambos podrían convivir.

```
┌────────────────────────┐   HTTP/JSON + JWT Bearer   ┌────────────────────────┐
│  Solari frontend        │ ─────────────────────────▶ │  Solari backend         │
│  React 19 · Vite · TS   │ ◀───────────────────────── │  FastAPI · SQLAlchemy 2 │
│  http://localhost:5173  │                            │  http://localhost:9000  │
└────────────────────────┘                            └───────────┬────────────┘
                                                                   │ psycopg 3 (async)
                                                                   ▼
                                                       ┌────────────────────────┐
                                                       │ PostgreSQL · voluntapp  │
                                                       └────────────────────────┘
```

---

## 2. Usuarios del sistema

- **Voluntario:** completa su perfil, elige intereses y habilidades, explora y se
  postula a convocatorias, guarda favoritos, gana XP y logros, ve su trayectoria,
  ofrece objetos o servicios gratuitos y abre tickets de soporte.
- **Organización** (en el código y la base se llama `FUNDACION`): publica
  convocatorias individuales o recurrentes, revisa postulaciones con su porcentaje
  de compatibilidad, confirma asistencia, mantiene un perfil público con galería,
  solicita la verificación documental y pide objetos o servicios a voluntarios.
- **Administrador:** gestiona usuarios, organizaciones, convocatorias,
  postulaciones y catálogos; responde soporte; resuelve solicitudes de privacidad;
  otorga la insignia de verificación; modera reseñas. Todas sus acciones quedan en
  auditoría.

---

## 3. Módulos funcionales

| Módulo | Qué hace | Reglas importantes |
|---|---|---|
| Autenticación | Registro (voluntario / organización), login, Google OIDC, verificación de correo, recuperación de contraseña, refresh token | Argon2id (con rehash de bcrypt heredado); refresh con rotación y un solo uso; mensajes que no revelan si una cuenta existe; aceptación de términos con evidencia (Ley 1581 de 2012) |
| Perfil del voluntario | Datos personales, foto, documento de identidad | Documento, fecha de nacimiento y género **no se editan** después del registro; se corrigen por solicitud a soporte. En la pantalla esos campos aparecen bloqueados |
| Perfil de la organización | Datos institucionales, logo | NIT y documento legal solo si está constituida legalmente |
| Convocatorias | Crear (borrador), publicar, editar, cancelar. Campos ricos: objetivo, impacto, actividades, beneficiarios, qué llevar, recomendaciones, política de cancelación, beneficios, horas, certificado, dificultad, urgente | Para publicar exige entre 3 y 10 habilidades. Estados: `BORRADOR`, `PENDIENTE_APROBACION`, `PUBLICADA`, `CERRADA`, `CANCELADA`, `COMPLETADA`, `FINALIZADA` |
| Galería de convocatorias | Hasta 8 fotos por convocatoria; la primera es la portada | Tabla `publicacion_imagenes`; la portada también se guarda en `publicaciones.imagen` para tarjetas y listados |
| Postulaciones | Postularse, retirarse, responder (aceptar, revisión, lista de espera, rechazar), confirmar asistencia con calificación 1–5 | Cupos con bloqueo de fila (`SELECT … FOR UPDATE`); sin duplicados; no se postula después de la fecha límite; si no hay cupo entra en lista de espera |
| Habilidades y compatibilidad | Catálogo de 108 habilidades en 7 categorías | Voluntario elige 3–10. Compatibilidad = coincidentes / requeridas × 100. Ordena el listado, **nunca** impide postularse |
| Intereses y recomendaciones | Catálogo de intereses; recomendaciones por afinidad | Puntúa categoría, municipio, modalidad, cupo y cercanía de la fecha |
| Gamificación | XP, 8 niveles, 11 logros, ranking top 1000 | XP **solo** al confirmar asistencia: 50 + 5 por hora reconocida. Idempotente; cada logro se gana una vez |
| Favoritos | Convocatorias y organizaciones | Persisten en BD, sin duplicados |
| Notificaciones | Avisos internos por eventos reales | El usuario configura preferencias por tipo; no se envían por correo |
| Actividades recurrentes | Programación por días, semanas o meses | Máximo 3 convocatorias por ciclo; luego se pausa hasta que la organización autorice. Las fotos de la programación (hasta 8) se copian a cada convocatoria generada |
| Objetos y servicios | El voluntario publica objetos (con cantidad) o servicios (con habilidades); la organización pulsa "Me interesa" y coordinan por mensajes | Siempre gratuitos (sin precios); los mensajes bloquean correos, teléfonos y enlaces; la entrega se completa solo si **ambas partes** confirman; control de cantidades con bloqueo de fila |
| Perfil público y verificación | Historia, misión, áreas de impacto, galería, contacto visible a elección, estadísticas reales; documentos privados para verificación | Documentos en carpeta privada (solo dueño y admin). La insignia la otorga un administrador y se muestra con aviso de que no es garantía absoluta |
| Reseñas | El voluntario reseña a la organización | Solo con participación confirmada; la organización responde; el admin puede ocultar con motivo |
| Soporte y privacidad | Tickets con hilo de mensajes; solicitudes de cuenta (bloqueo, eliminación, datos…) | Las solicitudes de privacidad no se ejecutan solas: requieren orden explícita del admin |
| Trayectoria | Actividades, horas, organizaciones y XP del voluntario | Calculada con registros reales |
| Edad mínima y menores | Registro solo desde los **16 años**; de 16 a 17 el acudiente descarga el formato, lo firma y se sube | Regla única en `app/core/edad.py` (`EDAD_MINIMA = 16`, `MAYORIA_EDAD = 18`), validada en registro, perfil y frontend. Un menor de 16–17 puede postularse, pero la organización no puede aceptarlo hasta que un administrador apruebe la autorización. Una convocatoria no puede pedir edad mínima menor de 16 |
| Certificados | PDF descargable cuando la asistencia está confirmada y la convocatoria otorga certificado | Código de verificación HMAC (no se guarda); verificación pública en `/certificados/verificar` con nombre abreviado |
| Calendario | Próximas actividades del voluntario y de la organización; exportación `.ics` | Recordatorio automático (notificación) antes de cada actividad aceptada |
| Mensajes de postulación | Chat entre voluntario y organización dentro de una postulación | Mismo filtro de datos personales que objetos y servicios |
| Notificaciones en vivo | Llegan al instante por SSE (`/notificaciones/stream`) | La conexión usa un ticket de corta duración, no el JWT en la URL; si falla, vuelve al sondeo |
| Seguridad de la cuenta | Sesiones y dispositivos activos, cerrar sesiones, verificación en dos pasos (TOTP) | Alerta al iniciar sesión desde un dispositivo nuevo |

### Ciclo de una participación

```
1. La organización se registra → el admin la aprueba
2. Crea una convocatoria (BORRADOR), agrega fotos y la PUBLICA
3. El voluntario completa perfil, intereses y habilidades
4. Explora (ordenado por compatibilidad) y se postula → PENDIENTE o LISTA_ESPERA
5. La organización acepta o rechaza → notificación al voluntario
6. Tras la actividad confirma la asistencia (ASISTIO, calificación 1–5)
7. El voluntario recibe XP, se evalúan logros y se actualizan horas, trayectoria y ranking
```

---

## 4. Backend (`Solari backend/`)

### Stack
Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2 async · psycopg 3 · Alembic ·
argon2-cffi · PyJWT (HS256) · slowapi (rate limiting) · google-auth · uvicorn ·
gestor de entorno **uv**.

### Estructura por capas

```
app/
├── main.py          # Crea la app: CORS, rate limit, routers, /uploads público
├── core/            # config.py (variables .env), security (hash/JWT), exceptions, rate_limit
├── db/              # Motor y sesión async
├── models/          # Tablas ORM (usuario, voluntario, fundacion, publicacion, ofrecimiento…)
├── schemas/         # Entrada/salida Pydantic (extra="forbid" en las entradas)
├── repositories/    # Consultas a la base
├── services/        # Reglas de negocio (una clase por módulo)
├── api/v1/          # Endpoints REST, uno por módulo
└── email/           # Envío de correos
alembic/versions/    # 0001 → 0007 (todas aditivas)
scripts/             # Semillas de datos de ejemplo
uploads/             # Archivos públicos (fotos, logos, galeria, ofrecimientos, convocatorias)
private_uploads/     # Documentos privados (identidad, verificación)
```

Flujo de una petición: **endpoint** (`api/v1`) → **service** (reglas) →
**repository** (datos) → **model**; responde con un **schema**.

### Routers en `app/api/v1/`
`auth`, `perfil`, `publicaciones`, `postulaciones`, `favoritos`, `gamificacion`,
`habilidades`, `notificaciones`, `programaciones`, `ofrecimientos`,
`organizaciones`, `soporte`, `cuenta`, `catalogos`, `legal`, `archivos`
(descarga autenticada de archivos privados), `admin`, `admin_gestion`, `health`.
Todos cuelgan de `/api/v1`. La documentación interactiva está en
`http://localhost:9000/docs`.

### Archivos subidos
- `StorageService` valida el tipo real por *magic bytes*, limita el tamaño
  (`UPLOAD_MAX_MB`, 5 MB por defecto) y usa nombres aleatorios.
- Solo se sirven públicamente las carpetas de `CARPETAS_PUBLICAS`
  (`fotos`, `logos`, `ofrecimientos`, `galeria`, `convocatorias`) bajo `/uploads`.
- Los documentos privados solo se descargan por `/archivos/privado` con sesión y
  control de propiedad.
- El backend devuelve URLs absolutas con `UPLOAD_PUBLIC_BASE`
  (`http://localhost:9000/uploads`); el frontend las usa tal cual.

### Variables de entorno (`.env`, ver `.env.example`)
`DATABASE_URL`, `JWT_SECRET` (el mismo que el backend Laravel), `JWT_ALGORITHM`,
`JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_MINUTES`, `CORS_ORIGINS`, límites
`RATE_LIMIT_*`, correo `MAIL_*`, `FRONTEND_RESET_URL`, `FRONTEND_VERIFY_URL`,
`GOOGLE_CLIENT_ID`, `PASSWORD_MIN_LENGTH`, `UPLOAD_PUBLIC_BASE`.
Nunca subas el `.env` real al repositorio.

### Arranque

```powershell
cd "Solari backend"
uv venv --python 3.14
uv sync
copy .env.example .env        # completar DATABASE_URL y JWT_SECRET
uv run alembic upgrade head   # migraciones aditivas
uv run python run.py          # http://127.0.0.1:9000
```

- En Windows se usa `run.py` porque fija el *event loop* Selector que necesita
  psycopg async.
- El puerto es **9000** (8001 y 8080 suelen estar reservados por Hyper-V);
  se cambia con `SOLARI_PORT`.
- `run.py` arranca **sin recarga automática**: después de cambiar código del
  backend hay que detenerlo y volver a ejecutarlo.

### Datos de ejemplo (`scripts/`, todos idempotentes)

```powershell
uv run python scripts/seed_habilidades.py      # 108 habilidades
uv run python scripts/seed_intereses.py        # intereses del voluntario
uv run python scripts/seed_areas_impacto.py    # 32 áreas de impacto (corrige tildes)
uv run python scripts/seed_ofrecimientos.py    # 6 objetos y 5 servicios de ejemplo
uv run python scripts/seed_convocatoria_demo.py  # convocatoria con 5 fotos para fundacion1@demo.com
```

`seed_convocatoria_demo.py` necesita las fotos en `uploads/convocatorias/`
(fotos de Wikimedia Commons: tres de dominio público y dos CC BY-SA 4.0).
Las cuentas de prueba están en `Proyecto/CREDENCIALES_ACCESO.md`.

### Pruebas

```powershell
uv run pytest
```

---

## 5. Frontend (`Solari frontend/`)

### Stack
React 19 · Vite 8 · TypeScript 6 · Tailwind CSS v4 (tema "solar" claro/oscuro) ·
React Router 7 · Axios (con refresh automático del token) · React Hook Form + Zod ·
Framer Motion · lucide-react · Vitest + Testing Library (`npm test`).

### Estructura

```
src/
├── App.tsx            # Rutas (carga diferida de páginas)
├── auth/              # AuthContext: sesión, usuario, rol
├── components/
│   ├── ui/            # Button, Input, Select, Alert, Badge, HabilidadesPicker…
│   ├── layout/        # AppLayout (menú lateral por rol), AdminLayout, AuthLayout
│   ├── convocatorias/ # ConvocatoriaCard, FavoritoButton
│   └── routing/       # Guardias: pública, protegida, admin
├── pages/app/         # Pantallas de voluntario y organización
├── pages/admin/       # Panel de administración
├── services/          # Llamadas a la API (auth, convocatorias, alineacion, admin…)
├── types/             # Tipos del dominio (convocatoria.ts, alineacion.ts…)
├── hooks/             # useFavoritos, useTheme
└── lib/               # apiClient (Axios), config, utils, archivos privados
```

### Rutas principales

| Ruta | Pantalla |
|---|---|
| `/`, `/login`, `/registro`, `/recuperar`, `/reset-password`, `/verify-email/:token` | Públicas y autenticación |
| `/app` | Panel según el rol |
| `/app/perfil` | Completar o editar el perfil |
| `/app/convocatorias`, `/app/convocatorias/:id` | Explorar y detalle (galería de fotos) |
| `/app/convocatorias/nueva`, `/app/mis-convocatorias`, `/app/convocatorias/:id/postulaciones` | Gestión de la organización |
| `/app/mis-postulaciones`, `/app/favoritos`, `/app/intereses`, `/app/habilidades` | Voluntario |
| `/app/logros`, `/app/ranking`, `/app/trayectoria` | Gamificación y trayectoria |
| `/app/programaciones` | Actividades recurrentes |
| `/app/ofrecimientos`, `/app/solicitudes-interes` | Objetos y servicios, y sus solicitudes |
| `/app/perfil-publico`, `/app/organizaciones/:id` | Perfil público (edición y vista) |
| `/app/notificaciones`, `/app/soporte` | Avisos y centro de ayuda |
| `/admin/usuarios`, `/voluntarios`, `/fundaciones`, `/convocatorias`, `/postulaciones`, `/catalogos`, `/gestion` | Administración |

### Arranque

```powershell
cd "Solari frontend"
npm install
copy .env.example .env   # VITE_API_BASE_URL=http://localhost:9000/api/v1
npm run dev              # http://localhost:5173
npm run build            # compilación de producción
npm run lint
```

---

## 6. Base de datos

PostgreSQL, base `voluntapp`. Usa UUID como clave en las entidades principales,
ENUM nativos para roles y estados, llaves foráneas con `CASCADE`, `RESTRICT` o
`SET NULL`, y restricciones `CHECK`.

| Grupo | Tablas principales |
|---|---|
| Cuentas | `usuarios`, `voluntarios`, `fundaciones`, tokens, `auditoria_perfil` |
| Convocatorias | `publicaciones`, `publicacion_habilidades`, `publicacion_imagenes`, `postulaciones`, programaciones recurrentes |
| Voluntario | `voluntario_intereses`, habilidades del voluntario, `voluntario_favoritos`, `voluntario_puntos`, `transacciones_puntos`, `voluntario_logros` |
| Organización | áreas de la fundación, galería, documentos de verificación, reseñas |
| Objetos y servicios | `ofrecimientos`, `ofrecimiento_habilidades`, `solicitudes_interes`, `mensajes_interes` |
| Comunicación | `notificaciones`, `preferencias_notificacion`, `tickets_soporte`, `ticket_mensajes`, `solicitudes_cuenta` |
| Legal | `documentos_legales`, `documento_legal_versiones`, `usuario_aceptaciones_legales` |
| Catálogos | `departamentos` (2), `municipios` (34), `areas_impacto` (32), `habilidades` (108), `intereses`, `logros` (11) |

Las convocatorias usan `areas_impacto` como categoría, igual que el perfil
público de la organización y el filtro de Explorar.

---

## 7. Seguridad (resumen)

- Consultas parametrizadas con el ORM; entradas con `extra="forbid"`.
- El rol y el estado los fija el backend; el cliente nunca puede darse ADMIN.
- Rate limiting en login, registro y recuperación.
- JWT con algoritmo fijo; refresh token hasheado, rotado y de un solo uso.
- Bloqueo de fila para cupos y cantidades.
- Archivos validados por contenido; documentos privados fuera de `/uploads`.
- Errores centralizados sin trazas ni SQL; CORS con orígenes explícitos.
- Detalle completo en `docs/SOLARI-SUSTENTACION.md`, sección 9.

---

## 8. Pendientes conocidos

- `docs/SOLARI-SUSTENTACION.md` todavía menciona el puerto 8080, 11 áreas de impacto y no
  incluye los módulos nuevos (certificados, calendario, mensajes, seguridad, menores).
- Docker no arranca con `Proyecto/voluntapp_mvp.sql` solo; hace falta un `pg_dump` de la base
  local (ver sección 9).
- Las pruebas de integración del backend (`tests/integration`, `test_auth_flow.py`) necesitan
  PostgreSQL y no corren en CI.
- Las carpetas siguen llamándose `Solary backend` y `Solary frontend`, igual que los repos de GitHub.

---

## 9. Docker

`docker-compose.yml` (en este repo) levanta tres servicios:

| Servicio | Qué hace | Puerto en el equipo |
|---|---|---|
| `db` | PostgreSQL 16 con la base `voluntapp`. En el primer arranque ejecuta el script SQL de `DB_INIT_SQL` | `5433` (para no chocar con un PostgreSQL local en 5432) |
| `backend` | Imagen de este repo (`Dockerfile`, Python 3.14 + uv). Ejecuta `alembic upgrade head` y luego `uvicorn app.main:app` en `0.0.0.0:9000` | `9000` |
| `frontend` | Imagen del repo del frontend: compila con Vite y sirve `dist/` con nginx (con *fallback* de SPA) | `5173` |

Volúmenes con nombre: `pgdata` (datos de PostgreSQL), `uploads` y `private_uploads`
(archivos subidos; los privados nunca se sirven por `/uploads`).

### Arranque

```powershell
cd "Solary backend"
copy .env.docker.example .env.docker   # cambiar POSTGRES_PASSWORD, DATABASE_URL y JWT_SECRET
docker compose up --build
```

- Frontend: `http://localhost:5173` · API: `http://localhost:9000/api/v1` · Docs: `http://localhost:9000/docs`.
- `.env.docker` está en `.gitignore`; no lo subas. El backend no arranca si `JWT_SECRET`
  sigue empezando por `cambia-esto`.
- En el contenedor no se usa `run.py`: en Linux el *event loop* por defecto funciona con psycopg async.

### Variables opcionales de `docker-compose.yml`

Se leen de la shell (o de un `.env` junto al compose, que Docker Compose usa solo para
interpolar):

| Variable | Valor por defecto | Uso |
|---|---|---|
| `DB_INIT_SQL` | `../Proyecto/voluntapp_mvp.sql` | Script SQL que crea la base la primera vez |
| `FRONTEND_DIR` | `../Solary frontend` | Carpeta del repo del frontend (contexto de build) |
| `VITE_API_BASE_URL` | `http://localhost:9000/api/v1` | URL de la API que se incrusta en el bundle del frontend |
| `VITE_GOOGLE_CLIENT_ID` | vacío | Client ID de Google para el frontend |

Ejemplo en PowerShell: `$env:DB_INIT_SQL="C:\ruta\voluntapp_dump.sql"; docker compose up --build`.

### Base de datos inicial

El script de `DB_INIT_SQL` solo se ejecuta cuando el volumen `pgdata` está vacío.
Para repetir la carga: `docker compose down -v` (**borra** los datos y archivos de los volúmenes).

**Importante:** `voluntapp_mvp.sql` no contiene todas las tablas que crearon después las
migraciones de Laravel (`Proyecto/database/migrations`), por ejemplo `refresh_tokens`,
gamificación, `publicacion_imagenes` o favoritos. La migración Alembic `0001` modifica
`refresh_tokens`, así que con ese script solo `alembic upgrade head` falla y el backend
no arranca. Lo recomendado es exportar la base local completa y usarla como script inicial:

```powershell
pg_dump -U postgres -h 127.0.0.1 -d voluntapp --no-owner --no-privileges -f voluntapp_dump.sql
$env:DB_INIT_SQL="$PWD\voluntapp_dump.sql"
docker compose up --build
```

El volcado incluye la tabla `alembic_version`, así que Alembic solo aplica las migraciones
que falten. No subas el volcado a ningún repositorio: contiene cuentas y datos personales.

### Integración continua

Cada repo tiene `.github/workflows/ci.yml` (push y PR a `master`):

- Backend: `uv sync`, `ruff check app tests` y las pruebas que no necesitan base de datos
  (se excluyen `tests/integration` y `tests/test_auth_flow.py`). Ruff ignora por ahora
  `E501,I001,C416,C408,S608,S311`, que tienen errores previos en el código; hay que quitar
  cada código de la lista cuando se corrija.
- Frontend: Node 22, `npm ci`, `npm run lint`, `npm run build`.
