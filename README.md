# Solary Backend — Autenticación (Python/FastAPI)

Backend de autenticación y gestión de cuentas de Solary, migrado a Python.
Coexiste con el backend Laravel existente usando la **misma** base de datos
PostgreSQL y JWT compatibles.

Consulta `docs/ADR-001-arquitectura-y-migracion.md` para las decisiones de diseño
y `docs/INSTALACION.md` para la guía de instalación y operación en Windows.

## Resumen rápido

- Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + psycopg 3, Alembic.
- Contraseñas con Argon2id (y verificación de bcrypt heredado con rehash perezoso).
- JWT HS256 compatible con `php-open-source-saver/jwt-auth`.
- Rate limiting, respuestas no enumerables, tokens opacos hasheados.
- Registro de voluntarios y fundaciones, login local, Google OIDC, recuperación de
  contraseña y aceptación de documentos legales.

## Arranque (desarrollo)

```powershell
# 1. Crear entorno e instalar dependencias (requiere uv)
uv venv --python 3.14
uv sync

# 2. Configurar variables
copy .env.example .env
# edita .env: pon el MISMO JWT_SECRET del backend Laravel y la DATABASE_URL

# 3. (una vez) aplicar la migración aditiva a la BD existente
uv run alembic upgrade head

# 4. Ejecutar el servidor
uv run uvicorn app.main:app --reload --port 8001
```

Documentación OpenAPI en `http://localhost:8001/docs`.
