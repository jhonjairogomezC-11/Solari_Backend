# syntax=docker/dockerfile:1
FROM python:3.14-slim

# uv oficial (binario estático).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Dependencias (capa cacheable mientras no cambien pyproject.toml / uv.lock).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Código de la aplicación y migraciones.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini run.py ./
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# Usuario sin privilegios; las carpetas de subida deben ser escribibles
# (los volúmenes con nombre heredan este dueño al crearse).
RUN useradd --system --uid 10001 --home-dir /app solari \
    && mkdir -p uploads private_uploads \
    && chown -R solari:solari uploads private_uploads
USER solari

EXPOSE 9000

# En Linux el event loop por defecto funciona con psycopg async (run.py solo hace falta en Windows).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
