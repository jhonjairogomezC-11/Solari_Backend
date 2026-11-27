"""Siembra de usuarios de prueba iniciales (Admin, Fundación y Voluntario).

Cuentas generadas:
1. Administrador: admin@solari.co / Admin123456*
2. Fundación:     fundacion1@demo.com / Fundacion123*
3. Voluntario:    voluntario1@demo.com / Voluntario123*
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.admin_accion import AdminPerfil
from app.models.fundacion import Fundacion
from app.models.gamificacion import VoluntarioPuntos
from app.models.usuario import Usuario
from app.models.voluntario import Voluntario


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # 1. Admin
        admin_user = (await db.execute(select(Usuario).where(Usuario.email == "admin@solari.co"))).scalar_one_or_none()
        if not admin_user:
            admin_user = Usuario(
                nombre="Administrador Solari",
                email="admin@solari.co",
                password_hash=hash_password("Admin123456*"),
                provider="LOCAL",
                rol="ADMIN",
                estado="ACTIVO",
                email_verificado=True,
            )
            db.add(admin_user)
            await db.flush()

            admin_perfil = AdminPerfil(usuario_id=admin_user.id, activo=True)
            db.add(admin_perfil)
            print("Usuario Admin creado: admin@solari.co / Admin123456*")
        else:
            print("Usuario Admin ya existe.")

        # 2. Fundación
        fund_user = (await db.execute(select(Usuario).where(Usuario.email == "fundacion1@demo.com"))).scalar_one_or_none()
        if not fund_user:
            fund_user = Usuario(
                nombre="Fundación Semillas de Paz",
                email="fundacion1@demo.com",
                password_hash=hash_password("Fundacion123*"),
                provider="LOCAL",
                rol="FUNDACION",
                estado="ACTIVO",
                email_verificado=True,
            )
            db.add(fund_user)
            await db.flush()

            fund_perfil = Fundacion(
                usuario_id=fund_user.id,
                nombre="Fundación Semillas de Paz",
                nit="900123456-1",
                representante_legal="Carlos Gómez",
                correo_institucional="fundacion1@demo.com",
                telefono="3101234567",
                direccion="Cra 7 # 45-10",
                municipio_id=1,
                pagina_web="https://semillasdepaz.org",
                descripcion="Organización dedicada a la restauración ecológica, educación ambiental y apoyo comunitario.",
                estado_verificacion="APROBADA",
                tipo_organizacion="FUNDACION",
                constituida_legalmente=True,
                historia="Nacimos en 2020 con el propósito de recuperar áreas verdes degradadas.",
                mision="Promover la sostenibilidad y la participación ciudadana en Bogotá.",
            )
            db.add(fund_perfil)
            print("Usuario Fundación creado: fundacion1@demo.com / Fundacion123*")
        else:
            print("Usuario Fundación ya existe.")

        # 3. Voluntario
        vol_user = (await db.execute(select(Usuario).where(Usuario.email == "voluntario1@demo.com"))).scalar_one_or_none()
        if not vol_user:
            vol_user = Usuario(
                nombre="Ana María Restrepo",
                email="voluntario1@demo.com",
                password_hash=hash_password("Voluntario123*"),
                provider="LOCAL",
                rol="VOLUNTARIO",
                estado="ACTIVO",
                email_verificado=True,
            )
            db.add(vol_user)
            await db.flush()

            vol_perfil = Voluntario(
                usuario_id=vol_user.id,
                tipo_documento="CC",
                numero_documento="1012345678",
                esta_verificado=True,
                fecha_nacimiento=date(1998, 5, 20),
                genero="FEMENINO",
                municipio_id=1,
                disponibilidad="FLEXIBLE",
                direccion="Calle 100 # 15-20",
                descripcion="Bióloga apasionada por la reforestación, el trabajo comunitario y el bienestar animal.",
                horas_acumuladas=15,
                actividades_completadas=3,
            )
            db.add(vol_perfil)
            await db.flush()

            puntos = VoluntarioPuntos(
                voluntario_id=vol_perfil.id,
                saldo=125,
                total_historico=125,
            )
            db.add(puntos)
            print("Usuario Voluntario creado: voluntario1@demo.com / Voluntario123*")
        else:
            print("Usuario Voluntario ya existe.")

        await db.commit()
    print("Siembra de usuarios de prueba finalizada.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
