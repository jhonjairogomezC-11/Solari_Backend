# ADR-001 — Arquitectura del backend Python y estrategia de migración

Estado: Aceptado (Fase 1)
Fecha: 2026-10-24
Autores: Equipo Solari

Este documento registra las decisiones arquitectónicas de la Fase 1 (autenticación,
registro y seguridad) del nuevo backend en Python, y cómo coexiste con el backend
Laravel/PHP existente sin romperlo.

---

## 1. Contexto heredado (auditoría del backend actual)

Backend actual verificado en el workspace `Proyecto/`:

- **Framework**: Laravel 12, PHP 8.2.
- **Base de datos**: PostgreSQL 14+ (`voluntapp`), con extensión `uuid-ossp`,
  tipos `ENUM` nativos, constraints `CHECK` e índices parciales.
- **Auth**: JWT con `php-open-source-saver/jwt-auth` 2.8. Guard `api` usa driver `jwt`.
- **Hashing**: bcrypt (`BCRYPT_ROUNDS=12`).
- **Clientes**: Flutter (Dio + Riverpod) y Vue 3. La app móvil NO se toca en esta fase.
- **Prefijo API**: `/api/v1`.

### 1.1. Esquema real relevante (no se renombra nada)

Tabla `usuarios` (PK `uuid` = `uuid_generate_v4()`), sin `created_at/updated_at`
(usa `fecha_registro` y `fecha_actualizacion`):

| Columna | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| nombre | varchar(120) | |
| email | varchar(150) | |
| password_hash | text NULL | bcrypt hoy |
| provider | enum proveedor_auth('LOCAL','GOOGLE') | |
| provider_id | varchar(255) NULL | |
| telefono | varchar(20) NULL | |
| rol | enum rol_usuario('VOLUNTARIO','FUNDACION','ADMIN') | |
| estado | enum estado_usuario('ACTIVO','BLOQUEADO','SUSPENDIDO') | default ACTIVO |
| email_verificado | bool | default false |
| fecha_registro | timestamp | useCurrent |
| fecha_actualizacion | timestamp | useCurrent |

Constraints e índices a respetar:

- `CHECK chk_auth_valid`: `(LOCAL AND password_hash NOT NULL) OR (GOOGLE AND provider_id NOT NULL)`.
- Único `(email, provider)` — el mismo email puede existir en LOCAL y GOOGLE separados.
- Único parcial `(provider, provider_id) WHERE provider_id IS NOT NULL`.

Perfiles 1:1 (`usuario_id` único):

- `voluntarios`: `tipo_documento` enum, `numero_documento` único, `fecha_nacimiento`
  (CHECK edad ≥ 14), `genero` enum, `municipio_id` FK, `disponibilidad` enum,
  `documento_identidad`, `esta_verificado`.
- `fundaciones`: `nit` único (CHECK `^\d{7,10}-\d$`), `representante_legal`,
  `telefono`, `direccion`, `municipio_id` FK, `descripcion`, `documento_legal`,
  `estado_verificacion` enum('PENDIENTE','APROBADA','RECHAZADA','SUSPENDIDA').

Tablas de tokens existentes (texto plano hoy):

- `verificacion_email` (token, expiracion 24h, usado).
- `recuperacion_password` (token, expiracion 1h, usado, fecha_uso, ip_solicitud, user_agent).
- `refresh_tokens` (token, expiracion 30d, usado, fecha_uso, ip_solicitud, user_agent).

### 1.2. Contrato que consume la app móvil (DEBE preservarse)

Verificado en el código Flutter (`auth_repository.dart`, `auth_session.dart`,
`api_constants.dart`, interceptores):

Registro `POST /api/v1/auth/register`:
```json
{ "nombre": "...", "email": "...", "password": "...",
  "password_confirmation": "...", "rol": "VOLUNTARIO|FUNDACION", "telefono": "opcional" }
```

Login `POST /api/v1/auth/login`: `{ "email", "password" }`.

Respuesta de login/register (claves EXACTAS que el móvil parsea):
```json
{
  "usuario": { "id","nombre","email","rol","estado","telefono","email_verificado" },
  "token": "<jwt>",
  "refresh_token": "<opaco>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

- Header `Authorization: Bearer <token>`, `Accept: application/json`.
- Refresh `POST /auth/refresh` con `{ "refresh_token" }` → `{ token, refresh_token, token_type, expires_in }`.
- El móvil hace **refresh automático ante 401**. La semántica de 401 debe conservarse.
- Otras rutas: `/auth/logout`, `/auth/me`, `/auth/revoke-refresh`,
  `/auth/forgot-password`, `/auth/reset-password`.

### 1.3. Parámetros JWT actuales (de `config/jwt.php` y `.env`)

- Algoritmo: **HS256**, secreto `JWT_SECRET` compartido.
- `ttl` access = 60 min; `refresh_ttl` = 20160 min (14 días).
- `required_claims`: `iss, iat, exp, nbf, sub, jti`.
- `lock_subject = true` → añade claim `prv` = `sha1('App\\Models\\Usuario')`.
- `iss` = URL de la app (emisor del token original en Laravel es la ruta de login).

---

## 2. Riesgos detectados en el backend actual

1. Hashing bcrypt (se pide Argon2id). No se puede recifrar sin la contraseña →
   **rehash perezoso en login**.
2. **Enumeración de cuentas** en registro ("El email ya está registrado").
3. **Sin rate limiting** en login / forgot-password.
4. Envío de correo **no implementado** (marcado TODO). Reset genera token pero no envía.
5. Refresh / reset / verificación tokens en **texto plano** en BD.
6. **Sin tablas legales** (términos / aceptaciones) — exigido por Ley 1581/2012.
7. Google OAuth preparado en enum pero **no implementado**.
8. El registro **no crea el perfil** (voluntario/fundación), deja cuentas incompletas.

---

## 3. Decisiones arquitectónicas

### D1 — Servicio FastAPI independiente, misma BD

Nuevo servicio en `Solari backend/`, apuntando a la **misma** base PostgreSQL
`voluntapp`. No se modifica Laravel. Ambos pueden escribir las mismas tablas.

### D2 — Compatibilidad JWT por secreto compartido (HS256)

Python firma y valida JWT con el **mismo `JWT_SECRET` y HS256**, replicando los
claims que Laravel exige (`iss, iat, exp, nbf, sub, jti, prv`). Así:

- Tokens emitidos por Python son aceptados por Laravel y viceversa (coexistencia real).
- No se obliga a los usuarios activos a volver a iniciar sesión.

El claim `prv` se calcula como `sha1('App\\Models\\Usuario')` para igualar a
`jwt-auth` con `lock_subject=true`. `sub` = UUID del usuario (igual que hoy).

### D3 — Argon2id con fallback bcrypt y rehash perezoso

- Registros nuevos: **Argon2id** (`argon2-cffi`).
- Login: si el hash es bcrypt (`$2y$`/`$2b$`) se verifica con bcrypt y, si es
  correcto, se **rehashea a Argon2id** y se actualiza `password_hash`.
- Columna `password_hash` es `text`, así que soporta ambos formatos sin migración.

### D4 — Capas y dominios

```
app/
  core/        config, security (hash + jwt), exceptions, logging, rate_limit
  db/          engine/session async (SQLAlchemy 2 + psycopg 3)
  models/      mapeo a tablas EXISTENTES (nombres reales de columnas)
  schemas/     Pydantic v2 (contrato de entrada/salida idéntico al móvil)
  repositories/ acceso a datos (consultas parametrizadas vía ORM)
  services/    reglas de negocio: auth, tokens, password reset, legal, google
  api/v1/      routers: auth, legal, health
  email/       proveedor SMTP conmutable por configuración
```

Principio: separación por responsabilidades sin sobre-abstracción. Preparado para
añadir módulos futuros (convocatorias, fundaciones, notificaciones) como nuevos
paquetes en `models/`, `services/`, `api/v1/` sin tocar auth.

### D5 — Driver PostgreSQL: psycopg 3 (async)

psycopg 3.3 soporta Python 3.14 con wheels en Windows y es el driver recomendado
por SQLAlchemy 2. Se descartó asyncpg por problemas de wheels para 3.14 en Windows.

### D6 — Seguridad por diseño

- Rate limiting (slowapi) en login, register, forgot-password, reset-password.
- Respuestas **no enumerables**: registro y login devuelven mensajes genéricos.
- Tokens opacos (refresh/reset/verificación) almacenados **hasheados** (SHA-256)
  en columnas nuevas y aditivas; el valor en claro solo viaja al cliente/email.
- Validación estricta Pydantic v2; CORS explícito; manejo central de errores sin
  filtrar trazas ni SQL; logs sin contraseñas ni tokens.

### D7 — Gestión de dependencias: uv + lockfile

`pyproject.toml` + `uv.lock` reproducible. Versiones fijadas tras verificar 3.14.

---

## 4. Estrategia de coexistencia PHP ↔ Python

- **Lectura/escritura compartida** de `usuarios`, `refresh_tokens`, etc.
- Columnas nuevas se añaden **aditivas y nullable** para que Laravel siga operando.
- Mientras ambos backends vivan, la fuente de verdad de contraseñas es
  `usuarios.password_hash` (soporta bcrypt y argon2id simultáneamente).
- Migraciones de esquema se gestionan con **Alembic** en modo aditivo y reversible;
  nunca `DROP`/`ALTER` destructivo sin aprobación explícita.

### Migraciones aditivas previstas (Fase 1, requieren ejecución aprobada)

1. `refresh_tokens.token_hash`, `recuperacion_password.token_hash`,
   `verificacion_email.token_hash` (nullable). Transición: Python escribe hash;
   Laravel sigue usando `token` hasta su retiro.
2. Tablas legales nuevas: `documentos_legales`, `documento_legal_versiones`,
   `usuario_aceptaciones_legales`. No afectan a Laravel.

---

## 5. Compatibilidad con Python 3.14 (verificada)

| Paquete | Estado 3.14 | Rol |
|---|---|---|
| FastAPI (>=0.11x) | Compatible | Framework HTTP |
| Pydantic v2 | Requerido en 3.14 (v1 sin soporte) | Validación |
| SQLAlchemy 2.x | Compatible | ORM |
| psycopg 3.3 | Compatible (wheels Windows) | Driver PG |
| Alembic | Compatible | Migraciones |
| argon2-cffi | Compatible | Hash de contraseñas |
| bcrypt | Compatible | Verificación de hashes heredados |
| pyjwt | Compatible | Firma/validación JWT HS256 |
| slowapi | Compatible | Rate limiting |
| pydantic-settings | Compatible | Config |

Si al fijar el lockfile alguna versión concreta no ofreciera wheel para 3.14 en
Windows, se documentará y se elegirá alternativa mantenida, sin forzar builds.

---

## 6. Puntos que requieren revisión jurídica (Ley 1581/2012)

El sistema registra **evidencia técnica** de aceptación (versión, fecha, IP,
user-agent, hash del contenido). No constituye por sí solo cumplimiento legal.
Requieren revisión de un abogado: finalidades del tratamiento, autorizaciones
específicas, derechos de los titulares (habeas data), conservación de evidencia y
tratamiento diferenciado de datos de voluntarios y fundaciones.
