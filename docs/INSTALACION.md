# Guía de instalación y operación (Windows)

Backend de autenticación de Solari en Python/FastAPI. Coexiste con el backend
Laravel usando la misma base de datos PostgreSQL.

## 1. Requisitos

- Windows 10/11.
- PostgreSQL 14+ en ejecución (la misma instancia que usa Laravel).
- `uv` (gestor de dependencias y de versiones de Python). Si no lo tienes:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Reinicia la terminal o añade al PATH de la sesión:
$env:Path = "C:\Users\<TU_USUARIO>\.local\bin;$env:Path"
```

## 2. Python 3.14 y entorno virtual

```powershell
uv python install 3.14
uv venv --python 3.14
uv sync
```

`uv sync` instala exactamente las versiones del lockfile (`uv.lock`), reproducible.

## 3. Configuración (.env)

```powershell
copy .env.example .env
```

Edita `.env`:

- `DATABASE_URL`: apunta a la MISMA base que Laravel, con driver psycopg:
  `postgresql+psycopg://postgres:TU_PASSWORD@127.0.0.1:5432/voluntapp`
- `JWT_SECRET`: copia EXACTAMENTE el valor de `JWT_SECRET` del `.env` de Laravel
  (en `Proyecto/.env`). Esto permite que ambos backends acepten los mismos tokens.
- `JWT_ISSUER`: deja el valor por defecto salvo que cambies la URL de Laravel.
- Correo y Google: ver más abajo.

Nunca subas `.env` al repositorio (ya está en `.gitignore`).

## 4. Migración aditiva de la base de datos

La Fase 1 añade columnas y tablas **de forma aditiva y reversible** (no borra ni
modifica datos). Revisa primero el SQL que se ejecutará:

```powershell
uv run alembic upgrade head --sql    # dry-run: muestra el SQL sin aplicarlo
uv run alembic upgrade head          # aplica la migración
```

Para revertir (si fuese necesario):

```powershell
uv run alembic downgrade -1
```

Qué agrega la migración `0001_aditivo`:

- `token_hash` (nullable) en `refresh_tokens`, `recuperacion_password`,
  `verificacion_email`, y hace `token` nullable (Laravel sigue funcionando).
- `intentos` en `recuperacion_password`.
- Tablas `documentos_legales`, `documento_legal_versiones`,
  `usuario_aceptaciones_legales`.

## 5. Ejecutar el servidor

En Windows usa el arranque dedicado (configura el event loop correcto para
psycopg async):

```powershell
uv run python run.py
```

- API: `http://127.0.0.1:9000/api/v1`
- OpenAPI (Swagger): `http://127.0.0.1:9000/docs`
- Salud: `http://127.0.0.1:9000/api/v1/health`
- El puerto se cambia con `SOLARI_PORT` (8001 y 8080 suelen estar reservados por Hyper-V).
- `run.py` no recarga solo: tras cambiar código del backend, detenlo (Ctrl+C) y vuelve a
  ejecutarlo.

Después de la primera instalación, publica los documentos legales (sin ellos el registro
no pide aceptación):

```powershell
uv run python scripts/seed_documentos_legales.py
```

> Nota: no uses `uvicorn --reload` directamente en Windows con psycopg async; el
> reload crea un loop ProactorEventLoop incompatible. `run.py` resuelve esto.

## 6. Ejecutar pruebas

Las pruebas usan una base aislada `voluntapp_test` (nunca tocan los datos reales).

```powershell
uv run python tests/_create_test_db.py   # crea voluntapp_test (una vez)
uv run pytest -q
```

Prueba de humo contra el servidor en vivo (registra y borra un usuario de prueba):

```powershell
# con el servidor corriendo:
uv run python tests/_smoke_real.py
```

## 7. Calidad de código

```powershell
uv run ruff check .      # linter
uv run ruff format .     # formateo
uv run mypy app          # tipos
```

## 8. Configuración del correo (recuperación/verificación)

El envío es conmutable por `MAIL_BACKEND`:

- `console` (por defecto, coste cero): escribe el correo en el log. Ideal para
  desarrollo.
- `smtp`: envía por SMTP. Rellena `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`,
  `MAIL_PASSWORD`, `MAIL_USE_TLS`.

Opciones gratuitas o con nivel gratuito para empezar (verifica condiciones
vigentes antes de decidir, porque los límites cambian):

- SMTP de un buzón existente (p. ej. el correo institucional del proyecto).
  Revisa los límites de envío diario del proveedor.
- Proveedores de correo transaccional con plan gratuito (p. ej. algunos ofrecen
  un número limitado de correos al mes). No asumas volúmenes ilimitados.

Cambiar de proveedor NO requiere tocar la lógica: solo variables de entorno.

## 9. Configuración de Google OAuth (OpenID Connect)

Para activar el login con Google:

1. En Google Cloud Console crea un proyecto y configura la pantalla de
   consentimiento OAuth.
2. Crea credenciales "OAuth 2.0 Client IDs". Para una app móvil necesitarás los
   client IDs de Android/iOS; para pruebas desde web, un client ID web.
3. Copia el/los client ID en `.env`:
   - `GOOGLE_CLIENT_ID=<tu-client-id-principal>`
   - `GOOGLE_ALLOWED_AUDIENCES=<id-web>,<id-android>,<id-ios>` (opcional; si se
     deja vacío se usa `GOOGLE_CLIENT_ID`).
4. El cliente (app móvil) obtiene un `id_token` de Google y lo envía a
   `POST /api/v1/auth/google` junto con `rol` (solo si la cuenta es nueva).

El backend verifica firma, emisor, audiencia y expiración del `id_token`. Sin
`GOOGLE_CLIENT_ID` configurado, el endpoint responde 503 (desactivado).

No se escriben secretos en el código ni en el repositorio.

## 10. Reversión / rollback

- Código: el backend Python es un servicio independiente. Para desactivarlo basta
  con detenerlo; Laravel sigue operando con la misma base.
- Esquema: `uv run alembic downgrade -1` revierte la migración aditiva. Como las
  columnas añadidas son nullable y las tablas nuevas no las usa Laravel, revertir
  no afecta al backend PHP.
