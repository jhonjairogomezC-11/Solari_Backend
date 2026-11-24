"""Con el correo sin confirmar, la API solo permite las rutas de verificación (requiere BD)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_correo_sin_verificar_bloquea_la_api(client, voluntario_payload):
    reg = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    if reg.status_code != 201:
        pytest.skip(f"El registro de prueba no está disponible: {reg.status_code}")
    token = reg.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    # Puede consultar su sesión y reenviar el correo...
    assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 200
    # ...pero no usar el resto de la API hasta confirmar el correo.
    resp = await client.get("/api/v1/perfil/voluntario", headers=h)
    assert resp.status_code == 403
    assert "Confirma tu correo" in resp.json()["message"]
