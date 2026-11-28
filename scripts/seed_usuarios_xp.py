"""Seed: 30 voluntarios y 20 fundaciones con XP variada."""
import uuid, random
import psycopg
from app.core.config import get_settings
from app.core.security import hash_password

settings = get_settings()
db_url = settings.database_url.replace('postgresql+psycopg://', 'postgresql://')
HASH = hash_password('Solari2026#')

def _nivel(xp):
    for n, tope in enumerate([100,300,600,1000,1500,2000,2500], start=1):
        if xp < tope: return n
    return 8

VOLUNTARIOS = [
    ('Carlos Andrés Bermúdez',   'carlos.bermudez@gmail.com',   'CC','1020111001','1999-04-12','MASCULINO',  1,'FLEXIBLE',       'Estudiante de ingeniería civil, experiencia en construcción comunitaria.',280),
    ('Luisa Fernanda Arias',     'luisa.arias@hotmail.com',     'CC','1020111002','2000-08-23','FEMENINO',   2,'FINES_DE_SEMANA','Comunicadora social, fotografía y redacción.',520),
    ('Mateo Gómez Restrepo',     'mateo.gomez@gmail.com',       'CC','1020111003','1997-02-15','MASCULINO',  3,'ENTRE_SEMANA',   'Psicólogo clínico, trabajo con poblaciones vulnerables.',1200),
    ('Sara Milena Vargas',       'sara.vargas@outlook.com',     'CC','1020111004','2001-11-07','FEMENINO',   4,'FLEXIBLE',       'Bióloga marina, conservación ambiental.',750),
    ('Nicolás Prada Jiménez',    'nicolas.prada@gmail.com',     'CC','1020111005','1994-06-30','MASCULINO',  5,'FINES_DE_SEMANA','Administrador de empresas, liderazgo en proyectos sociales.',350),
    ('Valeria Ospina Torres',    'valeria.ospina@gmail.com',    'CC','1020111006','2002-03-19','FEMENINO',   1,'ENTRE_SEMANA',   'Estudiante de medicina, brigadas de salud.',980),
    ('Felipe Cardona Muñoz',     'felipe.cardona@gmail.com',    'CC','1020111007','1996-09-04','MASCULINO',  6,'FLEXIBLE',       'Veterinario con experiencia en fauna silvestre.',620),
    ('Daniela Rincón Castro',    'daniela.rincon@gmail.com',    'CC','1020111008','2003-01-28','FEMENINO',   7,'FINES_DE_SEMANA','Artista plástica, talleres de arte terapia.',440),
    ('Alejandro Mora Silva',     'alejandro.mora@gmail.com',    'CC','1020111009','1991-12-14','MASCULINO',  8,'ENTRE_SEMANA',   'Ingeniero ambiental, proyectos de reforestación.',1850),
    ('Camila Herrera Blanco',    'camila.herrera@gmail.com',    'CC','1020111010','1998-07-09','FEMENINO',   9,'FLEXIBLE',       'Trabajadora social, víctimas del conflicto.',2100),
    ('Sebastián Ruiz Peña',      'sebastian.ruiz@outlook.com',  'CC','1020111011','2000-05-22','MASCULINO',  1,'FINES_DE_SEMANA','Licenciado en educación física, deporte social.',560),
    ('Mónica Salazar Guerrero',  'monica.salazar@gmail.com',    'CC','1020111012','1993-10-31','FEMENINO',   2,'ENTRE_SEMANA',   'Nutricionista, educación alimentaria.',890),
    ('Andrés Moreno Díaz',       'andres.moreno2@gmail.com',    'CC','1020111013','1999-02-17','MASCULINO',  3,'FLEXIBLE',       'Contador, apoyo financiero a ONG.',310),
    ('Laura Quintero Medina',    'laura.quintero@gmail.com',    'CC','1020111014','2001-08-05','FEMENINO',   4,'FINES_DE_SEMANA','Diseñadora UX, contenido digital.',720),
    ('Julián Castillo López',    'julian.castillo@gmail.com',   'CC','1020111015','1995-04-27','MASCULINO',  5,'ENTRE_SEMANA',   'Médico general, brigadas rurales.',1650),
    ('Paola Jiménez Suárez',     'paola.jimenez@hotmail.com',   'CC','1020111016','2002-12-03','FEMENINO',   6,'FLEXIBLE',       'Química farmacéutica, donación de medicamentos.',430),
    ('Ricardo Velásquez García', 'ricardo.velasquez@gmail.com', 'CC','1020111017','1988-06-18','MASCULINO',  7,'FINES_DE_SEMANA','Arquitecto, espacios comunitarios.',970),
    ('Ana María Pedraza',        'ana.pedraza@gmail.com',       'CC','1020111018','2000-09-11','FEMENINO',   8,'ENTRE_SEMANA',   'Educadora especial, inclusión educativa.',1380),
    ('Diego Ramírez Ortiz',      'diego.ramirez2@gmail.com',    'CC','1020111019','1997-03-25','MASCULINO',  9,'FLEXIBLE',       'Fotógrafo documental, impacto social.',640),
    ('Isabela Montoya Cruz',     'isabela.montoya@gmail.com',   'CC','1020111020','2003-07-16','FEMENINO',   1,'FINES_DE_SEMANA','Estudiante de derecho, derechos humanos.',290),
    ('Tomás Aguilar Navarro',    'tomas.aguilar@gmail.com',     'CC','1020111021','1992-11-08','MASCULINO',  2,'ENTRE_SEMANA',   'Economista, microfinanzas comunitarias.',1750),
    ('Valentina Mejía Acosta',   'valentina.mejia2@gmail.com',  'CC','1020111022','2001-01-30','FEMENINO',   3,'FLEXIBLE',       'Enfermera, cuidados paliativos.',2300),
    ('Esteban Nieto Parra',      'esteban.nieto@gmail.com',     'CC','1020111023','1996-08-14','MASCULINO',  4,'FINES_DE_SEMANA','Ingeniero de sistemas, apps para ONG.',820),
    ('Natalia Cárdenas Ramos',   'natalia.cardenas2@gmail.com', 'CC','1020111024','1999-05-29','FEMENINO',   5,'ENTRE_SEMANA',   'Socióloga, investigación social.',1100),
    ('Pablo Lozano Mendoza',     'pablo.lozano@gmail.com',      'CC','1020111025','2002-10-07','MASCULINO',  6,'FLEXIBLE',       'Músico, talleres para niños.',580),
    ('Mariana Duque Vergara',    'mariana.duque@hotmail.com',   'CC','1020111026','1990-02-20','FEMENINO',   7,'FINES_DE_SEMANA','Abogada, asistencia legal gratuita.',1420),
    ('Camilo Torres Benítez',    'camilo.torres2@gmail.com',    'CC','1020111027','1998-06-03','MASCULINO',  8,'ENTRE_SEMANA',   'Fisioterapeuta, rehabilitación comunitaria.',950),
    ('Sofía Varón Espinosa',     'sofia.varon@gmail.com',       'CC','1020111028','2001-12-19','FEMENINO',   9,'FLEXIBLE',       'Estudiante de arquitectura, urbanismo social.',380),
    ('Mauricio Patiño Reyes',    'mauricio.patino@gmail.com',   'CC','1020111029','1985-04-08','MASCULINO',  1,'FINES_DE_SEMANA','Administrador público, gestión de proyectos.',2800),
    ('Alejandra Cano Ibáñez',    'alejandra.cano@gmail.com',    'CC','1020111030','2000-07-25','FEMENINO',   2,'ENTRE_SEMANA',   'Odontóloga, salud oral comunitaria.',1680),
]

FUNDACIONES = [
    ('María del Pilar Sandoval', 'info@futurobrill.org',        'Futuro Brillante Colombia',  '900001001-1','María del Pilar Sandoval', '+57 310 100 0001','Cra 15 # 85-20, Usaquén',       1,'https://futurobrill.org',        'Educación de calidad para niños en pobreza extrema a través de tecnología e innovación pedagógica.'),
    ('Jorge Luis Espinoza',      'contacto@semillaspaz.org',    'Semillas de Paz',            '900001002-2','Jorge Luis Espinoza',      '+57 311 200 0002','Cll 72 # 10-34, Chapinero',     1,'https://semillaspaz.org',        'Reconciliación y construcción de paz en territorios afectados por el conflicto armado.'),
    ('Gloria Patricia Nieto',    'hola@aguaparodos.co',         'Agua para Todos',            '900001003-3','Gloria Patricia Nieto',    '+57 312 300 0003','Av 68 # 23-15, Teusaquillo',    1,'https://aguaparodos.co',         'Acceso a agua potable y saneamiento básico en comunidades rurales sin cobertura.'),
    ('Roberto Carlos Peña',      'info@techodigno.org',         'Fundación Techo Digno',      '900001004-4','Roberto Carlos Peña',      '+57 313 400 0004','Cll 26 # 50-30, Puente Aranda', 1,'https://techodigno.org',         'Mejoramiento de vivienda y hábitat para familias de escasos recursos en zonas periurbanas.'),
    ('Claudia Lorena Vásquez',   'info@alas.org.co',            'Alas — Mujeres Líderes',     '900001005-5','Claudia Lorena Vásquez',   '+57 314 500 0005','Cra 50 # 12-45, Mártires',     1,'https://alas.org.co',            'Empoderamiento económico y liderazgo de mujeres en situación de vulnerabilidad.'),
    ('Hernando Zuluaga',         'contacto@bosquevivo.co',      'Bosque Vivo',                '900001006-6','Hernando Zuluaga',         '+57 315 600 0006','Cll 134 # 9-72, Usaquén',       1,'https://bosquevivo.co',          'Conservación de bosques nativos y educación ambiental en comunidades rurales del Amazonas.'),
    ('Beatriz Elena Montoya',    'info@alegriamayor.org',       'Alegría Mayor',              '900001007-7','Beatriz Elena Montoya',    '+57 316 700 0007','Av Boyacá # 64-15, Engativá',   1,'https://alegriamayor.org',       'Atención integral y recreación para adultos mayores en situación de abandono y pobreza.'),
    ('Hernán Darío Cárdenas',    'hola@emprendealma.co',        'Emprende con Alma',          '900001008-8','Hernán Darío Cárdenas',    '+57 317 800 0008','Cra 30 # 45-60, Puente Aranda', 1,'https://emprendealma.co',        'Formación y financiación de emprendimientos sociales para jóvenes en situación de pobreza.'),
    ('Lina Marcela Giraldo',     'info@coloresdeinfancia.org',  'Colores de Infancia',        '900001009-9','Lina Marcela Giraldo',     '+57 318 900 0009','Cll 80 # 42-30, Kennedy',       1,'https://coloresdeinfancia.org',  'Arte, juego y creatividad como herramientas de desarrollo integral en la primera infancia.'),
    ('Jairo Alfonso Molina',     'contacto@redvida.org.co',     'Red de Vida',                '900001010-0','Jairo Alfonso Molina',     '+57 319 000 0010','Cra 7 # 32-10, Candelaria',     1,'https://redvida.org.co',         'Red de apoyo psicosocial para población migrante y desplazada.'),
    ('Paula Andrea Ríos',        'info@solanimal.co',           'Sol Animal',                 '900001011-1','Paula Andrea Ríos',        '+57 320 100 0011','Cll 170 # 20-15, Suba',         1,'https://solanimal.co',           'Rescate, rehabilitación y adopción de animales domésticos y silvestres en Bogotá.'),
    ('Gustavo Adolfo Parra',     'hola@tecnoincluye.org',       'TecnoIncluye',               '900001012-2','Gustavo Adolfo Parra',     '+57 321 200 0012','Cra 13 # 93-40, Chapinero',     1,'https://tecnoincluye.org',       'Alfabetización digital para adultos mayores y personas con discapacidad.'),
    ('Olga Lucía Bermúdez',      'info@raicescultura.org',      'Raíces y Cultura',           '900001013-3','Olga Lucía Bermúdez',      '+57 322 300 0013','Cll 45 # 28-50, Barrios Unidos',1,'https://raicescultura.org',       'Preservación del patrimonio cultural de comunidades indígenas y afrodescendientes.'),
    ('William Fernando Suárez',  'contacto@deportetransforma.co','Deporte que Transforma',    '900001014-4','William Fernando Suárez',  '+57 323 400 0014','Cra 68 # 75-20, Engativá',      1,'https://deportetransforma.co',   'Fútbol, baloncesto y atletismo como herramientas de inclusión social para jóvenes.'),
    ('Carmen Rosa Leal',         'info@siembravida.org',        'Siembra Vida',               '900001015-5','Carmen Rosa Leal',         '+57 324 500 0015','Cll 13 # 39-45, Puente Aranda', 1,'https://siembravida.org',        'Agricultura urbana y seguridad alimentaria para familias vulnerables.'),
    ('Arturo José Mejía',        'hola@horizonte.org.co',       'Fundación Horizonte',        '900001016-6','Arturo José Mejía',        '+57 325 600 0016','Av NQS # 55-30, Antonio Nariño',1,'https://horizonte.org.co',        'Rehabilitación e inclusión para personas con discapacidad visual y auditiva.'),
    ('Marcela Isabel Cano',      'info@vientosnuevos.org',      'Vientos Nuevos',             '900001017-7','Marcela Isabel Cano',      '+57 326 700 0017','Cra 24 # 15-60, Los Mártires',  1,'https://vientosnuevos.org',      'Reinserción social y acompañamiento jurídico para personas en resocialización.'),
    ('Fernando Alonso Torres',   'contacto@mareslimpios.co',    'Mares Limpios Colombia',     '900001018-8','Fernando Alonso Torres',   '+57 327 800 0018','Cll 100 # 14-20, Usaquén',      1,'https://mareslimpios.co',        'Limpieza de playas y protección de ecosistemas costeros y marinos.'),
    ('Adriana Lucía Pedroza',    'info@mentessanas.org',        'Mentes Sanas Colombia',      '900001019-9','Adriana Lucía Pedroza',    '+57 328 900 0019','Cra 11 # 74-80, Chapinero',     1,'https://mentessanas.org',        'Atención en salud mental gratuita y desestigmatización de trastornos psicológicos.'),
    ('Rodrigo Ernesto Vargas',   'hola@campoalegre.org.co',     'Campo Alegre',               '900001020-0','Rodrigo Ernesto Vargas',   '+57 329 000 0020','Cll 57 # 50-40, Teusaquillo',   1,'https://campoalegre.org.co',     'Desarrollo rural sostenible y apoyo a comunidades campesinas del Sumapaz.'),
]

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:

        print('Creando voluntarios...')
        for v in VOLUNTARIOS:
            nombre, email, tipo_doc, num_doc, fecha_nac, genero, muni, disp, exp, xp = v
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                print(f"  ⚠ Ya existe: {email}"); continue
            uid = str(uuid.uuid4())
            vid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO usuarios (id, nombre, email, password_hash, provider, rol, estado, email_verificado)
                VALUES (%s, %s, %s, %s, 'LOCAL', 'VOLUNTARIO', 'ACTIVO', true)
            """, (uid, nombre, email, HASH))
            cur.execute("""
                INSERT INTO voluntarios (id, usuario_id, tipo_documento, numero_documento,
                    fecha_nacimiento, genero, municipio_id, disponibilidad, experiencia,
                    esta_verificado, horas_acumuladas, actividades_completadas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (vid, uid, tipo_doc, num_doc, fecha_nac, genero, muni, disp, exp,
                  random.choice([True, False]), xp // 50, xp // 150))
            cur.execute("""
                INSERT INTO voluntario_puntos (voluntario_id, saldo, total_historico)
                VALUES (%s, %s, %s)
            """, (vid, xp, xp))
            print(f"  ✓ {nombre} — {xp} XP (nivel {_nivel(xp)})")

        print('\nCreando fundaciones...')
        for f in FUNDACIONES:
            nombre_u, email, nombre_f, nit, rep, tel, dir_, muni, web, desc = f
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                print(f"  ⚠ Ya existe: {email}"); continue
            uid = str(uuid.uuid4())
            fid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO usuarios (id, nombre, email, password_hash, provider, rol, estado, email_verificado)
                VALUES (%s, %s, %s, %s, 'LOCAL', 'FUNDACION', 'ACTIVO', true)
            """, (uid, nombre_u, email, HASH))
            cur.execute("""
                INSERT INTO fundaciones (id, usuario_id, nombre, nit, representante_legal,
                    telefono, direccion, municipio_id, pagina_web, descripcion,
                    tipo_organizacion, constituida_legalmente, estado_verificacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'FUNDACION', true, 'APROBADA')
            """, (fid, uid, nombre_f, nit, rep, tel, dir_, muni, web, desc))
            print(f"  ✓ {nombre_f}")

        conn.commit()
        print('\n✅ Seed completado.')
