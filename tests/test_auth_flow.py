"""Pruebas de integración del flujo de autenticación contra la BD de pruebas."""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_registro_voluntario_exitoso(client, voluntario_payload, db_engine):
    resp = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    # Contrato que consume el móvil.
    assert set(data) >= {"usuario", "token", "refresh_token", "token_type", "expires_in"}
    assert data["token_type"] == "bearer"
    assert data["usuario"]["rol"] == "VOLUNTARIO"
    assert data["usuario"]["estado"] == "ACTIVO"

    # La contraseña se guarda hasheada con Argon2id, nunca en claro.
    async with db_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT password_hash FROM usuarios WHERE email = :e"),
                {"e": voluntario_payload["email"]},
            )
        ).first()
    assert row is not None
    assert row[0].startswith("$argon2")
    assert voluntario_payload["password"] not in row[0]


async def test_registro_fundacion_exitoso(client, fundacion_payload, db_engine):
    resp = await client.post("/api/v1/auth/register/foundation", json=fundacion_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["usuario"]["rol"] == "FUNDACION"

    async with db_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT estado_verificacion FROM fundaciones WHERE nit = :n"),
                {"n": fundacion_payload["nit"]},
            )
        ).first()
    assert row is not None
    assert row[0] == "PENDIENTE"


async def test_registro_rechaza_campos_invalidos(client, voluntario_payload):
    voluntario_payload["email"] = "no-es-un-email"
    resp = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert resp.status_code == 422
    assert "errors" in resp.json()


async def test_registro_rechaza_password_debil(client, voluntario_payload):
    voluntario_payload["password"] = "corta"
    voluntario_payload["password_confirmation"] = "corta"
    resp = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert resp.status_code == 422


async def test_registro_email_duplicado_es_generico(client, voluntario_payload):
    r1 = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert r1.status_code == 201
    voluntario_payload["numero_documento"] = "9999999999"
    r2 = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert r2.status_code == 409
    # Mensaje genérico: no revela que el email ya existe.
    assert "ya está registrado" not in r2.json()["message"].lower()


async def test_no_se_puede_autoasignar_admin(client, voluntario_payload):
    # extra='forbid' bloquea campos no declarados como 'estado' o 'rol' arbitrario.
    payload = {**voluntario_payload, "estado": "ADMIN", "rol": "ADMIN"}
    resp = await client.post("/api/v1/auth/register/volunteer", json=payload)
    assert resp.status_code == 422  # rechazado por campos no permitidos


async def test_login_correcto_e_incorrecto(client, voluntario_payload):
    await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)

    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": voluntario_payload["email"], "password": voluntario_payload["password"]},
    )
    assert ok.status_code == 200
    assert ok.json()["token"]

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": voluntario_payload["email"], "password": "ClaveIncorrecta9"},
    )
    assert bad.status_code == 401
    # Mensaje genérico idéntico para credenciales inválidas.
    mensaje = bad.json()["message"].lower()
    assert "incorrect" in mensaje or "incorrecto" in mensaje


async def test_login_email_inexistente_mensaje_generico(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nadie@example.com", "password": "ClaveSegura123"},
    )
    assert resp.status_code == 401
    assert "message" in resp.json()


async def test_ruta_protegida_requiere_token(client, voluntario_payload):
    sin_token = await client.get("/api/v1/auth/me")
    assert sin_token.status_code == 401

    reg = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    token = reg.json()["token"]
    con_token = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert con_token.status_code == 200
    assert con_token.json()["email"] == voluntario_payload["email"]


async def test_refresh_rota_el_token(client, voluntario_payload):
    reg = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    refresh = reg.json()["refresh_token"]

    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r1.status_code == 200
    nuevo_refresh = r1.json()["refresh_token"]
    assert nuevo_refresh != refresh

    # El refresh token viejo ya no sirve (rotación + un solo uso).
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


async def test_forgot_password_siempre_generico(client, voluntario_payload):
    await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    existe = await client.post(
        "/api/v1/auth/forgot-password", json={"email": voluntario_payload["email"]}
    )
    no_existe = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "otro@example.com"}
    )
    assert existe.status_code == no_existe.status_code == 200
    assert existe.json()["message"] == no_existe.json()["message"]


async def test_reset_password_token_invalido(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "token-que-no-existe",
            "password": "NuevaClave123",
            "password_confirmation": "NuevaClave123",
        },
    )
    assert resp.status_code == 400


async def test_reset_password_flujo_completo(client, voluntario_payload, db_engine):
    await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    await client.post(
        "/api/v1/auth/forgot-password", json={"email": voluntario_payload["email"]}
    )
    # En producción el token llega por correo. En pruebas lo recuperamos desde la BD
    # mediante un token nuevo con hash conocido para simular el enlace recibido.
    # Generamos un token controlado insertándolo directamente (hash SHA-256).
    import hashlib

    from sqlalchemy import text as _t

    raw = "token-de-prueba-controlado"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    async with db_engine.begin() as conn:
        uid = (
            await conn.execute(
                _t("SELECT id FROM usuarios WHERE email = :e"),
                {"e": voluntario_payload["email"]},
            )
        ).first()[0]
        await conn.execute(
            _t(
                "INSERT INTO recuperacion_password (usuario_id, token_hash, expiracion, usado)"
                " VALUES (:u, :h, CURRENT_TIMESTAMP + INTERVAL '1 hour', false)"
            ),
            {"u": uid, "h": token_hash},
        )

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw,
            "password": "NuevaClave123",
            "password_confirmation": "NuevaClave123",
        },
    )
    assert resp.status_code == 200

    # La nueva contraseña funciona.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": voluntario_payload["email"], "password": "NuevaClave123"},
    )
    assert login.status_code == 200


async def test_google_desactivado_sin_config(client):
    resp = await client.post(
        "/api/v1/auth/google", json={"id_token": "x", "rol": "VOLUNTARIO"}
    )
    # Sin GOOGLE_CLIENT_ID configurado responde 503 (no implementado/activado).
    assert resp.status_code == 503


async def test_logout_revoca_refresh(client, voluntario_payload):
    reg = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    token = reg.json()["token"]
    refresh = reg.json()["refresh_token"]

    out = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert out.status_code == 200

    # Tras logout, el refresh queda revocado.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401
