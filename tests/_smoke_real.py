"""Smoke test manual contra el servidor en vivo + BD real.

Registra un voluntario de prueba, hace login y consulta /me, y LUEGO borra el
usuario de prueba para no dejar datos en producción. Uso:
    uv run python tests/_smoke_real.py
"""

from __future__ import annotations

import time

import httpx
import psycopg

BASE = "http://127.0.0.1:8001/api/v1"
DSN = "postgresql://postgres:admin@127.0.0.1:5432/voluntapp"
EMAIL = f"smoke.test.{int(time.time())}@example.com"
DOC = f"SMOKE{int(time.time())}"


def cleanup() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM usuarios WHERE email = %s", (EMAIL,))
        print("limpieza: usuario de prueba eliminado")


def main() -> None:
    payload = {
        "nombre": "Smoke Test",
        "email": EMAIL,
        "password": "ClaveSegura123",
        "password_confirmation": "ClaveSegura123",
        "rol": "VOLUNTARIO",
        "tipo_documento": "CC",
        "numero_documento": DOC[:30],
        "fecha_nacimiento": "2000-01-01",
        "genero": "OTRO",
        "municipio_id": 1,
        "disponibilidad": "FLEXIBLE",
    }
    try:
        with httpx.Client(base_url=BASE, timeout=20) as c:
            r = c.post("/auth/register/volunteer", json=payload)
            print("register:", r.status_code)
            assert r.status_code == 201, r.text
            data = r.json()
            assert set(data) >= {"usuario", "token", "refresh_token", "expires_in"}
            token = data["token"]

            me = c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            print("me:", me.status_code, me.json().get("email"))
            assert me.status_code == 200

            login = c.post(
                "/auth/login", json={"email": EMAIL, "password": "ClaveSegura123"}
            )
            print("login:", login.status_code)
            assert login.status_code == 200

            # Verifica que el token de Python sería válido en formato (claims Laravel).
            refresh = c.post(
                "/auth/refresh", json={"refresh_token": data["refresh_token"]}
            )
            print("refresh:", refresh.status_code)
            assert refresh.status_code == 200
            print("SMOKE OK")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
