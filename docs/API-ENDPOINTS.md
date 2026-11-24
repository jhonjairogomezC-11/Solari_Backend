# Contrato de endpoints — Autenticación y documentos legales

Base: `/api/v1`. Respuestas de error con formato `{ "message": "..." }` y, en
validación, `{ "message": "...", "errors": { "campo": ["..."] } }`.

Este documento cubre **solo autenticación y legal**. La lista completa de endpoints
(convocatorias, postulaciones, perfil, notificaciones, objetos y servicios, admin…) está en
la documentación interactiva (OpenAPI) en `http://localhost:9000/docs`.

## Correo sin confirmar

Mientras el usuario no confirme su correo (`email_verificado = false`), todos los
endpoints que requieren sesión responden **403** `"Confirma tu correo electrónico para
continuar."`, excepto `GET /auth/me`, `POST /auth/resend-verification`,
`POST /auth/logout` y `POST /auth/revoke-refresh`. Los administradores están exentos.

## Aceptación de documentos legales

Si hay documentos legales publicados como requeridos (`GET /legal/documentos`,
`requerido_registro = true`), los registros deben incluir:

```json
"aceptaciones": [
  { "codigo": "TERMINOS_CONDICIONES", "aceptado": true },
  { "codigo": "POLITICA_DATOS_PERSONALES", "aceptado": true }
]
```

Si falta alguno, el registro responde **409**. El backend resuelve la versión vigente y
guarda la fecha, la IP y el navegador; el cliente no envía versión ni fecha.

## Compatibilidad con la app móvil

Las rutas y el formato de respuesta de login/register/refresh reproducen el
contrato que la app Flutter ya consume:

```json
{ "usuario": {"id","nombre","email","rol","estado","telefono","email_verificado"},
  "token": "<jwt>", "refresh_token": "<opaco>", "token_type": "bearer", "expires_in": 3600 }
```

---

## POST /auth/register  (compatibilidad móvil)
- Propósito: registro que acepta `rol` en el cuerpo (como hace el móvil hoy) y
  enruta internamente a voluntario o fundación. El `rol` nunca concede ADMIN.
- Entrada: campos del registro + `rol` ("VOLUNTARIO"|"FUNDACION").
- Respuesta: 201 con `TokenResponse`.
- Errores: 409 (datos en conflicto, genérico), 422 (validación).
- Rate limit: 10/hora por IP.

## POST /auth/register/volunteer
- Propósito: registro explícito de voluntario (crea usuario + perfil).
- Entrada (JSON): `nombre, email, password, password_confirmation, telefono?,
  tipo_documento (CC|TI|CE|PASAPORTE), numero_documento, fecha_nacimiento,
  genero (MASCULINO|FEMENINO|OTRO), municipio_id, disponibilidad
  (ENTRE_SEMANA|FINES_DE_SEMANA|FLEXIBLE), experiencia?, aceptaciones[]?`.
- Seguridad: `extra="forbid"` bloquea campos peligrosos (estado, provider, etc.).
  El rol se fija en el backend. Password validado (min 8, mayúscula, minúscula, dígito).
- Respuesta: 201 `TokenResponse`. Errores: 409, 422. Rate limit: 10/hora.

## POST /auth/register/foundation
- Propósito: registro explícito de fundación (usuario + perfil en estado
  `PENDIENTE` de verificación).
- Entrada: `nombre, email, password, password_confirmation, telefono?,
  nombre_fundacion, nit (000000000-0), representante_legal, correo_institucional?,
  telefono_contacto, direccion, municipio_id, descripcion, documento_legal,
  pagina_web?, aceptaciones[]?`.
- Respuesta: 201 `TokenResponse`. Errores: 409, 422. Rate limit: 10/hora.

## POST /auth/login
- Entrada: `{ email, password }`.
- Respuesta: 200 `TokenResponse`.
- Seguridad: Argon2id + rehash perezoso de bcrypt heredado. Mensaje de error
  genérico ("Correo o contraseña incorrectos.") para no enumerar cuentas. Bloquea
  cuentas SUSPENDIDO/BLOQUEADO. Rate limit: 5/minuto por IP.
- Errores: 401 (credenciales o estado), 422.

## POST /auth/refresh
- Entrada: `{ refresh_token }`.
- Respuesta: 200 `TokenResponse` con token y refresh NUEVOS (rotación, un solo uso).
- Errores: 401 (inválido/expirado/ya usado). Rate limit: 30/minuto.

## POST /auth/logout  (requiere Bearer)
- Revoca todos los refresh tokens del usuario. Respuesta: 200.

## POST /auth/revoke-refresh  (requiere Bearer)
- Revoca refresh tokens (logout multidispositivo). Respuesta: `{ message, revocados }`.

## GET /auth/me  (requiere Bearer)
- Respuesta: 200 `UsuarioOut`.
- Errores: 401 (sin token/ inválido/ expirado), 403 (cuenta no activa).

## GET /auth/verify-email/{token}
- Marca el email como verificado si el token es válido y no usado (vigencia: 24 horas).
- El enlace del correo apunta al frontend: `FRONTEND_VERIFY_URL?token=<token>`; el
  frontend llama a este endpoint.
- Respuesta: 200 o 400 (token inválido/expirado).

## POST /auth/resend-verification  (requiere Bearer)
- Genera un enlace de verificación nuevo y lo envía al correo del usuario.
- Si el correo ya está verificado, responde 200 sin enviar nada.
- Respuesta: 200 `{ message }`. Rate limit: 5/hora.

## POST /auth/forgot-password
- Entrada: `{ email }`.
- Respuesta: 200 SIEMPRE con mensaje genérico (no revela si el email existe).
- Efecto: si existe, invalida tokens previos, genera uno nuevo (hash en BD,
  expira en 1h, un solo uso) y envía el enlace por correo. Rate limit: 3/hora.

## POST /auth/reset-password
- Entrada: `{ token, password, password_confirmation }`.
- Respuesta: 200 o 400 (token inválido/expirado). Al cambiar la contraseña se
  revocan todas las sesiones (refresh tokens). Rate limit: 5/hora.

## POST /auth/google
- Entrada: `{ id_token, rol? }` (rol solo para cuentas nuevas).
- Verifica el id_token con Google (firma, iss, aud, exp). No vincula
  automáticamente a cuentas LOCAL con el mismo email. Respuesta: 200 `TokenResponse`.
- Errores: 401 (token inválido / email no verificado), 409 (requiere selección de
  rol o vinculación), 503 (Google no configurado). Rate limit: 10/minuto.

## GET /legal/documentos
- Lista los documentos legales vigentes (código, versión, url/contenido).
- Respuesta: 200 lista de `DocumentoLegalVigenteOut`.

## GET /health
- Verifica app + conexión a BD. Respuesta: `{ "status": "ok" }` o 503.

---

## Controles de seguridad aplicados (resumen)

| Riesgo | Mitigación |
|---|---|
| Inyección SQL | ORM SQLAlchemy con consultas parametrizadas; sin concatenación. |
| Asignación masiva | Pydantic `extra="forbid"`; rol/estado fijados por backend. |
| Escalada de privilegios | `rol` del cliente se ignora; nunca concede ADMIN. |
| Fuerza bruta | Rate limiting por IP en login y endpoints sensibles. |
| Enumeración de cuentas | Mensajes genéricos en login, registro y forgot-password. |
| Robo/reuso de tokens | Refresh opaco hasheado (SHA-256), rotación y un solo uso. |
| Reset abusivo | Token hasheado, expiración 1h, un solo uso, invalidación previa. |
| JWT inseguro | Algoritmo fijado (HS256), rechazo de 'none', claims requeridos. |
| Filtración en errores | Handler central: nunca expone trazas ni SQL al cliente. |
| CORS inseguro | Orígenes explícitos por configuración (no comodín con credenciales). |
| Contraseñas débiles | Política en backend (longitud + mayús/minús/dígito). |
| Contraseñas en claro | Argon2id; verificación bcrypt heredado con rehash perezoso. |
