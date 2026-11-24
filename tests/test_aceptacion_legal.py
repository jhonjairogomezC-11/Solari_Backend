"""El registro exige aceptar los documentos legales publicados y guarda la evidencia."""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

_CODIGOS = ("TERMINOS_CONDICIONES", "POLITICA_DATOS_PERSONALES")


async def _publicar_documentos(db_engine) -> None:
    async with db_engine.begin() as conn:
        for codigo in _CODIGOS:
            doc_id = (
                await conn.execute(
                    text(
                        "INSERT INTO documentos_legales (codigo, nombre, requerido_registro) "
                        "VALUES (:c, :c, true) RETURNING id"
                    ),
                    {"c": codigo},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    "INSERT INTO documento_legal_versiones (documento_id, version, contenido, vigente) "
                    "VALUES (:d, '1.0', 'texto', true)"
                ),
                {"d": doc_id},
            )


async def test_registro_sin_aceptar_documentos_se_rechaza(client, voluntario_payload, db_engine):
    await _publicar_documentos(db_engine)
    resp = await client.post("/api/v1/auth/register/volunteer", json=voluntario_payload)
    assert resp.status_code == 409, resp.text
    assert "documentos legales" in resp.json()["message"]


async def test_registro_guarda_evidencia_de_aceptacion(client, voluntario_payload, db_engine):
    await _publicar_documentos(db_engine)
    payload = {
        **voluntario_payload,
        "aceptaciones": [{"codigo": c, "aceptado": True} for c in _CODIGOS],
    }
    resp = await client.post("/api/v1/auth/register/volunteer", json=payload)
    assert resp.status_code == 201, resp.text

    async with db_engine.connect() as conn:
        filas = (
            await conn.execute(
                text(
                    "SELECT d.codigo, v.version FROM usuario_aceptaciones_legales a "
                    "JOIN documento_legal_versiones v ON v.id = a.version_id "
                    "JOIN documentos_legales d ON d.id = v.documento_id "
                    "JOIN usuarios u ON u.id = a.usuario_id WHERE u.email = :e"
                ),
                {"e": voluntario_payload["email"]},
            )
        ).all()
    assert sorted(c for c, _ in filas) == sorted(_CODIGOS)
    assert all(v == "1.0" for _, v in filas)
