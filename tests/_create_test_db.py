"""Crea (si no existe) la base de datos de pruebas aislada `voluntapp_test`.

NUNCA toca la base de datos real. Uso manual:  uv run python tests/_create_test_db.py
"""

from __future__ import annotations

import os

import psycopg

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN", "postgresql://postgres:admin@127.0.0.1:5432/postgres"
)
TEST_DB = os.environ.get("TEST_DB_NAME", "voluntapp_test")


def main() -> None:
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
            if cur.fetchone():
                print(f"La base de pruebas '{TEST_DB}' ya existe.")
                return
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
            print(f"Base de pruebas '{TEST_DB}' creada.")


if __name__ == "__main__":
    main()
