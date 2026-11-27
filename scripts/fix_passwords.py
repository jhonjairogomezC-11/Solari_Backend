import psycopg
from app.core.security import hash_password
from app.core.config import get_settings

settings = get_settings()

# Convierte la URL async a sync (quita +psycopg, usa psycopg directamente)
db_url = settings.database_url.replace('postgresql+psycopg://', '')

h_admin = hash_password('Admin2026#')
h_fund  = hash_password('Fundacion2026#')

with psycopg.connect(f'postgresql://{db_url}') as conn:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET password_hash = %s WHERE email = %s",
            (h_admin, 'admin@solari.co')
        )
        cur.execute(
            "UPDATE usuarios SET password_hash = %s WHERE email = %s",
            (h_fund, 'contacto@fundacionluzverde.org')
        )
        cur.execute(
            "SELECT email, LEFT(password_hash, 30) FROM usuarios WHERE email IN ('admin@solari.co','contacto@fundacionluzverde.org')"
        )
        for row in cur.fetchall():
            print(row)
    conn.commit()

print("Hashes actualizados.")
