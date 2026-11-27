"""Seed completo: 5 fundaciones, 8 convocatorias, 15 voluntarios."""
import uuid
import psycopg
from app.core.config import get_settings
from app.core.security import hash_password

settings = get_settings()
db_url = settings.database_url.replace('postgresql+psycopg://', 'postgresql://')

# Imágenes públicas de Unsplash (no requieren auth)
IMAGENES = [
    'https://images.unsplash.com/photo-1593113598332-cd288d649433?w=800',  # voluntariado
    'https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?w=800',  # comunidad
    'https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?w=800',  # donación
    'https://images.unsplash.com/photo-1559027615-cd4628902d4a?w=800',    # naturaleza
    'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800',  # educación
    'https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=800',  # salud
    'https://images.unsplash.com/photo-1415025148099-17fe74102b28?w=800',  # animales
    'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800',  # medio ambiente
]

HASH_PASS = hash_password('Solari2026#')

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:

        # ── FUNDACIONES ──────────────────────────────────────────────────────
        fundaciones = [
            {
                'email': 'contacto@fundacionmanos.org',
                'nombre_usuario': 'Valentina Restrepo Giraldo',
                'nombre': 'Fundación Manos que Transforman',
                'nit': '900112233-1',
                'rep_legal': 'Valentina Restrepo Giraldo',
                'correo_inst': 'info@fundacionmanos.org',
                'telefono': '+57 310 234 5678',
                'direccion': 'Carrera 7 # 32-15, La Candelaria',
                'municipio_id': 1,
                'web': 'https://fundacionmanos.org',
                'descripcion': 'Somos una organización sin ánimo de lucro fundada en 2010 con el propósito de transformar vidas a través de la educación, el deporte y el arte. Trabajamos con niños y jóvenes en situación de vulnerabilidad en Bogotá, brindando espacios seguros de aprendizaje y desarrollo personal.',
                'historia': 'Fundada por un grupo de docentes comprometidos, hemos impactado más de 5.000 familias en 13 años de labor continua en los barrios más vulnerables de la capital.',
                'mision': 'Empoderar a niños y jóvenes en situación de vulnerabilidad a través de la educación integral, el deporte y las artes, fomentando el desarrollo de competencias para la vida.',
                'tipo': 'FUNDACION',
                'areas': [6, 8, 16],
            },
            {
                'email': 'info@raicesverdes.co',
                'nombre_usuario': 'Andrés Felipe Moreno',
                'nombre': 'Raíces Verdes Colombia',
                'nit': '900445566-2',
                'rep_legal': 'Andrés Felipe Moreno',
                'correo_inst': 'proyectos@raicesverdes.co',
                'telefono': '+57 315 678 9012',
                'direccion': 'Calle 45 # 28-60, Chapinero',
                'municipio_id': 1,
                'web': 'https://raicesverdes.co',
                'descripcion': 'Organización ambiental dedicada a la reforestación, educación ecológica y protección de ecosistemas en Colombia. Desde 2015 hemos plantado más de 80.000 árboles en zonas de páramo y bosque seco tropical, involucrando a comunidades locales como guardianes del territorio.',
                'historia': 'Nació de la iniciativa de un grupo de biólogos y ambientalistas que decidieron pasar de la academia a la acción. Hoy contamos con alianzas en 8 departamentos del país.',
                'mision': 'Restaurar y proteger los ecosistemas naturales de Colombia mediante la participación activa de comunidades, voluntarios y aliados estratégicos.',
                'tipo': 'FUNDACION',
                'areas': [9, 13, 14],
            },
            {
                'email': 'hola@abuelofelize.org',
                'nombre_usuario': 'Claudia Inés Vargas',
                'nombre': 'Fundación Abuelo Feliz',
                'nit': '901234567-3',
                'rep_legal': 'Claudia Inés Vargas',
                'correo_inst': 'programas@abuelofelize.org',
                'telefono': '+57 312 345 6789',
                'direccion': 'Avenida 68 # 75-23, Engativá',
                'municipio_id': 1,
                'web': 'https://abuelofelize.org',
                'descripcion': 'Dedicada al bienestar integral del adulto mayor en Colombia. Brindamos acompañamiento emocional, talleres de memoria, actividades recreativas y atención médica básica a personas mayores de 60 años en condición de soledad o pobreza. Creemos que la vejez debe vivirse con dignidad, afecto y alegría.',
                'historia': 'Fundada en 2008 por Claudia Vargas tras ver las condiciones de abandono de su propio abuelo. Hoy atendemos más de 400 adultos mayores semanalmente en 6 centros de día.',
                'mision': 'Garantizar una vejez digna y feliz para los adultos mayores más vulnerables, a través del acompañamiento integral, la salud preventiva y la recreación.',
                'tipo': 'FUNDACION',
                'areas': [1, 10, 17],
            },
            {
                'email': 'contacto@patitasfelices.co',
                'nombre_usuario': 'Sebastián Gómez Ríos',
                'nombre': 'Patitas Felices',
                'nit': '900876543-4',
                'rep_legal': 'Sebastián Gómez Ríos',
                'correo_inst': 'adopciones@patitasfelices.co',
                'telefono': '+57 316 789 0123',
                'direccion': 'Calle 134 # 52-18, Usaquén',
                'municipio_id': 1,
                'web': 'https://patitasfelices.co',
                'descripcion': 'Refugio y organización de protección animal con más de 200 perros y gatos rescatados. Trabajamos en la rescate, rehabilitación y adopción responsable de animales en situación de calle. Además, desarrollamos campañas de esterilización masiva y educación sobre tenencia responsable de mascotas en colegios y comunidades.',
                'historia': 'Empezamos en 2013 con 3 voluntarios y un garaje. Hoy somos más de 150 voluntarios activos y hemos logrado más de 3.000 adopciones exitosas.',
                'mision': 'Rescatar, rehabilitar y dar en adopción a animales en situación de vulnerabilidad, promoviendo una cultura de respeto y responsabilidad hacia los animales.',
                'tipo': 'REFUGIO',
                'areas': [12],
            },
            {
                'email': 'info@salud360.org',
                'nombre_usuario': 'Mónica Alejandra Peña',
                'nombre': 'Salud 360 Colombia',
                'nit': '900654321-5',
                'rep_legal': 'Mónica Alejandra Peña',
                'correo_inst': 'brigadas@salud360.org',
                'telefono': '+57 318 901 2345',
                'direccion': 'Carrera 50 # 20-30, Teusaquillo',
                'municipio_id': 1,
                'web': 'https://salud360colombia.org',
                'descripcion': 'Organización de salud pública que realiza brigadas médicas gratuitas en zonas rurales y comunidades marginales. Contamos con un equipo de médicos, enfermeros, odontólogos y psicólogos voluntarios que llevan atención de calidad a quienes no tienen acceso al sistema de salud. Hemos atendido más de 50.000 pacientes en 10 años.',
                'historia': 'Creada por un grupo de médicos recién graduados en 2013, con la convicción de que la salud es un derecho y no un privilegio. Hoy operamos en 12 departamentos.',
                'mision': 'Garantizar el acceso a servicios de salud de calidad para las comunidades más vulnerables de Colombia, mediante brigadas médicas, telemedicina y educación en salud.',
                'tipo': 'FUNDACION',
                'areas': [10, 15, 7],
            },
        ]

        fund_ids = {}
        for f in fundaciones:
            uid = str(uuid.uuid4())
            fid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO usuarios (id, nombre, email, password_hash, provider, rol, estado, email_verificado)
                VALUES (%s, %s, %s, %s, 'LOCAL', 'FUNDACION', 'ACTIVO', true)
            """, (uid, f['nombre_usuario'], f['email'], HASH_PASS))
            cur.execute("""
                INSERT INTO fundaciones (id, usuario_id, nombre, nit, representante_legal,
                    correo_institucional, telefono, direccion, municipio_id, pagina_web,
                    descripcion, historia, mision, tipo_organizacion, constituida_legalmente,
                    estado_verificacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'APROBADA')
            """, (fid, uid, f['nombre'], f['nit'], f['rep_legal'],
                  f['correo_inst'], f['telefono'], f['direccion'],
                  f['municipio_id'], f['web'], f['descripcion'],
                  f['historia'], f['mision'], f['tipo']))
            for area_id in f['areas']:
                cur.execute("INSERT INTO fundacion_areas (fundacion_id, area_id) VALUES (%s, %s)", (fid, area_id))
            fund_ids[f['nombre']] = fid
            print(f"  ✓ Fundación: {f['nombre']}")

        # ── CONVOCATORIAS ────────────────────────────────────────────────────
        fids = list(fund_ids.values())
        convocatorias = [
            {
                'fid': fids[0],
                'titulo': 'Tutores de Lectura — Jóvenes que Transforman',
                'descripcion': 'Buscamos voluntarios apasionados por la educación para acompañar a niños de 7 a 12 años en el fortalecimiento de sus habilidades de lectura y escritura. Trabajarás en grupos pequeños de 5 estudiantes, aplicando metodologías lúdicas y creativas que hacen del aprendizaje una aventura.',
                'objetivo': 'Mejorar el nivel de comprensión lectora de 150 niños en situación de vulnerabilidad, elevando su rendimiento académico y amor por los libros.',
                'impacto': 'Cada voluntario impactará directamente a 5 niños durante 3 meses. Al finalizar, los estudiantes mostrarán una mejora promedio del 40% en sus pruebas de lectura.',
                'actividades': 'Lectura guiada individual y en grupo, actividades de escritura creativa, talleres de expresión oral, seguimiento de progreso, comunicación con docentes y familias.',
                'perfil': 'Niños de 7 a 12 años de los barrios Usme, Ciudad Bolívar y Bosa en Bogotá.',
                'que_llevar': 'Ropa cómoda, libros de cuentos (opcionales), materiales de papelería básicos.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Calle 85 Sur # 72-14, Usme, Bogotá',
                'fecha_inicio': '2027-02-03',
                'fecha_fin': '2027-04-30',
                'hora_inicio': '08:00',
                'hora_fin': '12:00',
                'cupo': 30,
                'edad_min': 18,
                'edad_max': 35,
                'horas': 4,
                'certificado': True,
                'transporte': False,
                'alimentacion': True,
                'seguro': True,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 6,
                'imagen': IMAGENES[4],
                'contacto_nombre': 'Valentina Restrepo',
                'contacto_email': 'voluntarios@fundacionmanos.org',
                'contacto_telefono': '+57 310 234 5678',
            },
            {
                'fid': fids[0],
                'titulo': 'Arte y Creatividad para la Convivencia',
                'descripcion': 'Convocamos artistas, diseñadores y amantes del arte para facilitar talleres de pintura, dibujo y manualidades con adolescentes en riesgo social. El arte como herramienta de transformación personal y social.',
                'objetivo': 'Proporcionar espacios de expresión artística a 80 adolescentes entre 13 y 17 años, promoviendo la autoestima, la creatividad y la resolución pacífica de conflictos.',
                'impacto': 'Reducción de conductas de riesgo, mejora del clima escolar y descubrimiento de talentos artísticos en jóvenes que nunca habían tenido acceso a estas expresiones.',
                'actividades': 'Talleres de pintura acrílica, muralismo comunitario, diseño gráfico básico, fotografía con celular, exposición final de obras.',
                'perfil': 'Adolescentes de 13 a 17 años de los barrios Kennedy y Bosa.',
                'que_llevar': 'Ropa que pueda mancharse, pinceles propios si tienes.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Carrera 80 # 42-60, Kennedy, Bogotá',
                'fecha_inicio': '2027-03-10',
                'fecha_fin': '2027-06-10',
                'hora_inicio': '14:00',
                'hora_fin': '18:00',
                'cupo': 20,
                'edad_min': 18,
                'edad_max': 45,
                'horas': 4,
                'certificado': True,
                'transporte': False,
                'alimentacion': False,
                'seguro': False,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 2,
                'imagen': IMAGENES[1],
                'contacto_nombre': 'Laura Gómez',
                'contacto_email': 'arte@fundacionmanos.org',
                'contacto_telefono': '+57 310 234 5679',
            },
            {
                'fid': fids[1],
                'titulo': 'Jornada de Reforestación — Páramo de Sumapaz',
                'descripcion': 'Únete a nuestra jornada de siembra de árboles nativos en el páramo de Sumapaz, el páramo más grande del mundo. Aprenderás sobre biodiversidad, cambio climático y técnicas de restauración ecológica mientras contribuyes directamente a la recuperación de este ecosistema vital para el agua de Bogotá.',
                'objetivo': 'Plantar 2.000 árboles de especies nativas (encenillo, frailejón, arrayán) en 50 hectáreas degradadas del páramo de Sumapaz.',
                'impacto': 'Restauración de zonas de recarga hídrica que abastecen de agua a 8 millones de bogotanos. Captura de aproximadamente 400 toneladas de CO₂ en 20 años.',
                'actividades': 'Preparación de hoyos, siembra de plántulas, tutorado y protección, registro fotográfico georreferenciado, charla sobre ecosistemas de páramo.',
                'perfil': 'Comunidades rurales del municipio de Sumapaz y áreas protegidas del sur de Bogotá.',
                'que_llevar': 'Ropa abrigada (hace frío en el páramo), botas de caucho, poncho para lluvia, almuerzo y agua.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Páramo de Sumapaz — punto de encuentro: vía a Nazareth km 12',
                'fecha_inicio': '2027-01-15',
                'fecha_fin': '2027-01-15',
                'hora_inicio': '06:00',
                'hora_fin': '16:00',
                'cupo': 50,
                'edad_min': 16,
                'edad_max': 55,
                'horas': 10,
                'certificado': True,
                'transporte': True,
                'alimentacion': True,
                'seguro': True,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 9,
                'imagen': IMAGENES[3],
                'contacto_nombre': 'Andrés Moreno',
                'contacto_email': 'campo@raicesverdes.co',
                'contacto_telefono': '+57 315 678 9012',
            },
            {
                'fid': fids[2],
                'titulo': 'Compañía para Abuelitos — Visitas Domiciliarias',
                'descripcion': 'Buscamos voluntarios con vocación de servicio y empatía para acompañar a adultos mayores que viven solos. Una visita semanal de 2 horas puede cambiar radicalmente la calidad de vida de una persona mayor. Escucha su historia, comparte un tinto, juega ajedrez o simplemente acompáñalos.',
                'objetivo': 'Reducir el aislamiento social y la soledad de 60 adultos mayores mediante visitas domiciliarias semanales que fortalezcan sus vínculos afectivos y sociales.',
                'impacto': 'Mejora comprobada en indicadores de salud mental, reducción de la depresión y ansiedad en adultos mayores acompañados. Cada voluntario es asignado a 1 abuelito permanente.',
                'actividades': 'Visita domiciliaria semanal de 2 horas, actividades de estimulación cognitiva, lectura en voz alta, juegos de mesa, apoyo en gestiones básicas, reporte de bienestar.',
                'perfil': 'Adultos mayores de 65 años que viven solos en Engativá, Fontibón y Suba.',
                'que_llevar': 'Buena actitud, paciencia y ganas de escuchar. Opcionales: juegos de mesa, libros.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Domicilio del adulto mayor asignado (barrios Engativá, Fontibón y Suba)',
                'fecha_inicio': '2027-02-01',
                'fecha_fin': '2027-07-31',
                'hora_inicio': '10:00',
                'hora_fin': '12:00',
                'cupo': 60,
                'edad_min': 18,
                'edad_max': 70,
                'horas': 2,
                'certificado': True,
                'transporte': False,
                'alimentacion': False,
                'seguro': False,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 1,
                'imagen': IMAGENES[0],
                'contacto_nombre': 'Claudia Vargas',
                'contacto_email': 'voluntarios@abuelofelize.org',
                'contacto_telefono': '+57 312 345 6789',
            },
            {
                'fid': fids[2],
                'titulo': 'Talleres de Memoria y Tecnología para Adultos Mayores',
                'descripcion': 'Ayuda a nuestros abuelitos a mantenerse activos mentalmente y conectarse con el mundo digital. Enseña a usar WhatsApp, videollamadas y redes sociales a adultos mayores que quieren reencontrarse con sus familias y mantenerse informados. Incluye actividades de estimulación cognitiva y ejercicios de memoria.',
                'objetivo': 'Capacitar a 80 adultos mayores en el uso básico de smartphones y aplicaciones de comunicación, reduciendo su brecha digital y mejorando su conexión familiar.',
                'impacto': 'Adultos mayores conectados con sus familias, con mayor autonomía digital y mejor autoestima. Reducción del sentimiento de exclusión generacional.',
                'actividades': 'Clases de uso de smartphone, WhatsApp y videollamadas, juegos de memoria en tablet, fotografía básica, creación de álbumes digitales familiares.',
                'perfil': 'Adultos mayores de 60 a 85 años, sin conocimientos previos de tecnología.',
                'que_llevar': 'Paciencia, claridad para explicar, opcional: tablet propia.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Centro Día Fundación Abuelo Feliz — Avenida 68 # 75-23',
                'fecha_inicio': '2027-03-03',
                'fecha_fin': '2027-05-30',
                'hora_inicio': '09:00',
                'hora_fin': '11:00',
                'cupo': 15,
                'edad_min': 18,
                'edad_max': 50,
                'horas': 2,
                'certificado': True,
                'transporte': False,
                'alimentacion': True,
                'seguro': False,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 11,
                'imagen': IMAGENES[2],
                'contacto_nombre': 'Fernanda López',
                'contacto_email': 'tecnologia@abuelofelize.org',
                'contacto_telefono': '+57 312 345 6790',
            },
            {
                'fid': fids[3],
                'titulo': 'Voluntarios para Rescate y Rehabilitación Animal',
                'descripcion': 'Únete a nuestro equipo de rescate. Necesitamos personas comprometidas para apoyar en la atención diaria de más de 200 animales rescatados: perros, gatos y pequeñas especies. Actividades de cuidado, socialización y preparación para adopción. No se requiere experiencia veterinaria, solo amor por los animales y compromiso.',
                'objetivo': 'Garantizar la atención diaria de 200 animales rescatados, apoyar en 50 jornadas de adopción y lograr al menos 100 nuevas adopciones responsables.',
                'impacto': 'Cada voluntario contribuye directamente al bienestar de animales que esperan un hogar. El 85% de los animales bien socializados por voluntarios logran ser adoptados.',
                'actividades': 'Alimentación y limpieza de caniles, baño y cepillado, paseo de perros, socialización con animales tímidos, apoyo en jornadas de adopción, transporte a citas veterinarias.',
                'perfil': 'Animales rescatados de la calle, maltrato o abandono.',
                'que_llevar': 'Ropa que pueda ensuciarse, calzado cerrado, guantes (los tenemos disponibles).',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Refugio Patitas Felices — Calle 134 # 52-18, Usaquén',
                'fecha_inicio': '2027-01-05',
                'fecha_fin': '2027-12-31',
                'hora_inicio': '08:00',
                'hora_fin': '12:00',
                'cupo': 25,
                'edad_min': 16,
                'edad_max': 60,
                'horas': 4,
                'certificado': False,
                'transporte': False,
                'alimentacion': False,
                'seguro': True,
                'nivel': 'PRINCIPIANTE',
                'categoria_id': 12,
                'imagen': IMAGENES[6],
                'contacto_nombre': 'Sebastián Gómez',
                'contacto_email': 'voluntarios@patitasfelices.co',
                'contacto_telefono': '+57 316 789 0123',
            },
            {
                'fid': fids[4],
                'titulo': 'Brigada Médica Rural — Boyacá',
                'descripcion': 'Convocamos a médicos, enfermeros, odontólogos, optómetras y psicólogos para nuestra brigada de salud en municipios rurales de Boyacá. Durante 3 días atenderemos a comunidades campesinas que no tienen acceso regular al sistema de salud. Una experiencia transformadora que cambiará tu perspectiva profesional y de vida.',
                'objetivo': 'Atender a 500 pacientes en los municipios de Soatá, Tipacoque y Boavita con servicios de medicina general, odontología, optometría y psicología.',
                'impacto': 'Acceso a salud para comunidades rurales con tasas de cobertura del sistema inferiores al 40%. Diagnósticos tempranos que salvan vidas.',
                'actividades': 'Consulta médica general, control prenatal, optometría y entrega de gafas, extracciones y limpiezas dentales, consulta psicológica, toma de muestras de laboratorio, charlas de salud preventiva.',
                'perfil': 'Comunidades campesinas de los municipios de Soatá, Tipacoque y Boavita en el norte de Boyacá.',
                'que_llevar': 'Equipo médico personal, ropa cómoda, calzado cerrado. Alojamiento y alimentación cubiertos por la fundación.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 29,
                'direccion': 'Municipio de Soatá, Boyacá — punto de concentración en la plaza principal',
                'fecha_inicio': '2027-04-11',
                'fecha_fin': '2027-04-13',
                'hora_inicio': '07:00',
                'hora_fin': '18:00',
                'cupo': 40,
                'edad_min': 22,
                'edad_max': 65,
                'horas': 11,
                'certificado': True,
                'transporte': True,
                'alimentacion': True,
                'seguro': True,
                'nivel': 'EXPERTO',
                'categoria_id': 10,
                'imagen': IMAGENES[5],
                'contacto_nombre': 'Mónica Peña',
                'contacto_email': 'brigadas@salud360.org',
                'contacto_telefono': '+57 318 901 2345',
            },
            {
                'fid': fids[4],
                'titulo': 'Educadores en Salud — Escuelas Saludables',
                'descripcion': 'Buscamos voluntarios para llevar educación en salud a colegios públicos de Bogotá. Talleres sobre nutrición, salud mental, prevención de enfermedades, higiene y educación sexual responsable para estudiantes de bachillerato. Una oportunidad para aplicar tus conocimientos en salud y hacer la diferencia en la vida de los jóvenes.',
                'objetivo': 'Capacitar a 2.000 estudiantes de 10 colegios públicos de Bogotá en hábitos saludables, salud mental y prevención de enfermedades crónicas.',
                'impacto': 'Reducción de conductas de riesgo, mejora en hábitos alimenticios y mayor conciencia sobre salud mental en la población estudiantil.',
                'actividades': 'Talleres de nutrición saludable, charlas de salud mental y manejo del estrés, educación en salud sexual y reproductiva, primeros auxilios básicos, feria de salud.',
                'perfil': 'Estudiantes de grados 8° a 11° de colegios públicos de Suba, Usaquén y Chapinero.',
                'que_llevar': 'Materiales didácticos (los podemos proveer), ropa formal o de la fundación.',
                'modalidad': 'PRESENCIAL',
                'municipio_id': 1,
                'direccion': 'Colegios públicos asignados en Suba, Usaquén y Chapinero, Bogotá',
                'fecha_inicio': '2027-02-17',
                'fecha_fin': '2027-06-27',
                'hora_inicio': '07:00',
                'hora_fin': '13:00',
                'cupo': 20,
                'edad_min': 20,
                'edad_max': 45,
                'horas': 6,
                'certificado': True,
                'transporte': False,
                'alimentacion': False,
                'seguro': False,
                'nivel': 'INTERMEDIO',
                'categoria_id': 10,
                'imagen': IMAGENES[7],
                'contacto_nombre': 'Diana Ruiz',
                'contacto_email': 'escuelas@salud360.org',
                'contacto_telefono': '+57 318 901 2346',
            },
        ]

        for c in convocatorias:
            cid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO publicaciones (
                    id, fundacion_id, titulo, descripcion, categoria_id, modalidad,
                    municipio_id, direccion_exacta, fecha_inicio, fecha_fin,
                    hora_inicio, hora_fin, cupo_maximo, edad_minima, edad_maxima,
                    horas_reconocidas, otorga_certificado, incluye_transporte,
                    incluye_alimentacion, incluye_seguro, nivel_experiencia,
                    objetivo, impacto_esperado, actividades_voluntario,
                    perfil_beneficiarios, que_llevar, imagen, estado,
                    contacto_nombre, contacto_email, contacto_telefono,
                    fecha_limite_postulacion, dificultad, urgente, oculta_por_admin
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, 'PUBLICADA',
                    %s, %s, %s, %s, 'FACIL', false, false
                )
            """, (
                cid, c['fid'], c['titulo'], c['descripcion'], c['categoria_id'],
                c['modalidad'], c['municipio_id'], c['direccion'],
                c['fecha_inicio'], c['fecha_fin'], c['hora_inicio'], c['hora_fin'],
                c['cupo'], c['edad_min'], c['edad_max'], c['horas'],
                c['certificado'], c['transporte'], c['alimentacion'], c['seguro'],
                c['nivel'], c['objetivo'], c['impacto'], c['actividades'],
                c['perfil'], c['que_llevar'], c['imagen'],
                c['contacto_nombre'], c['contacto_email'], c['contacto_telefono'],
                c['fecha_inicio'],
            ))
            print(f"  ✓ Convocatoria: {c['titulo'][:50]}...")

        # ── VOLUNTARIOS ──────────────────────────────────────────────────────
        voluntarios = [
            ('Santiago Herrera Molina',    'santiago.herrera@gmail.com',   'CC', '1001234567', '2000-03-15', 'MASCULINO',   1, 'FLEXIBLE',       'Estudiante de ingeniería de sistemas con experiencia en programación y robótica educativa. He apoyado en campamentos de ciencia para niños.'),
            ('Mariana López Castillo',     'mariana.lopez@hotmail.com',    'CC', '1002345678', '1998-07-22', 'FEMENINO',    2, 'FINES_DE_SEMANA', 'Psicóloga recién graduada con interés en trabajo comunitario y salud mental. He participado en programas de atención a víctimas del conflicto.'),
            ('Daniela Muñoz Torres',       'daniela.munoz@gmail.com',      'CC', '1003456789', '2001-11-08', 'FEMENINO',    3, 'ENTRE_SEMANA',    'Estudiante de trabajo social. Me apasiona trabajar con niños y comunidades vulnerables. Tengo experiencia en ludotecas comunitarias.'),
            ('Camilo Rodríguez Peña',      'camilo.rodriguez@outlook.com', 'CC', '1004567890', '1995-05-30', 'MASCULINO',   1, 'FINES_DE_SEMANA', 'Médico general con 3 años de experiencia. Participo en brigadas de salud rural desde la universidad. Hablo inglés y portugués básico.'),
            ('Valentina García Cruz',      'vale.garcia@gmail.com',        'CC', '1005678901', '2002-09-14', 'FEMENINO',    4, 'FLEXIBLE',        'Bióloga en formación con pasión por la conservación ambiental. He participado en proyectos de monitoreo de aves y reforestación.'),
            ('Juan David Morales',         'juandavid.m@gmail.com',        'CC', '1006789012', '1993-12-03', 'MASCULINO',   5, 'ENTRE_SEMANA',    'Veterinario con especialización en animales domésticos. Apoyo en clínicas veterinarias comunitarias y jornadas de vacunación.'),
            ('Isabella Ramírez Vargas',    'isa.ramirez@gmail.com',        'CC', '1007890123', '1999-04-20', 'FEMENINO',    1, 'FINES_DE_SEMANA', 'Diseñadora gráfica y artista plástica. Me encanta usar el arte como herramienta de transformación social. Doy clases de dibujo a niños.'),
            ('Sebastián Ortiz Jiménez',    'seba.ortiz@hotmail.com',       'CC', '1008901234', '1997-08-11', 'MASCULINO',   6, 'FLEXIBLE',        'Licenciado en educación física. Creo en el deporte como transformador social. He liderado equipos de fútbol en barrios vulnerables.'),
            ('Laura Mendoza Silva',        'laura.mendoza@gmail.com',      'CC', '1009012345', '2003-01-25', 'FEMENINO',    7, 'ENTRE_SEMANA',    'Estudiante de nutrición y dietética. Quiero contribuir a mejorar los hábitos alimenticios de comunidades vulnerables.'),
            ('Andrés Felipe Suárez',       'andres.suarez@gmail.com',      'CC', '1000123456', '1991-06-17', 'MASCULINO',   8, 'FINES_DE_SEMANA', 'Ingeniero ambiental con maestría en gestión de recursos naturales. 5 años de experiencia en proyectos de sostenibilidad.'),
            ('Natalia Vargas Ospina',      'nati.vargas@gmail.com',        'CC', '1011234567', '2000-10-05', 'FEMENINO',    9, 'FLEXIBLE',        'Comunicadora social especializada en periodismo comunitario. Creo en el poder de las historias para generar cambios sociales.'),
            ('Miguel Ángel Castro',        'miguel.castro@outlook.com',    'CC', '1012345678', '1988-02-28', 'MASCULINO',   1, 'ENTRE_SEMANA',    'Contador público con experiencia en finanzas para organizaciones sin ánimo de lucro. Me interesa el fortalecimiento institucional de fundaciones.'),
            ('Sofía Pardo Nieto',          'sofia.pardo@gmail.com',        'CC', '1013456789', '2001-07-19', 'FEMENINO',    2, 'FINES_DE_SEMANA', 'Estudiante de medicina en quinto año. Me apasiona la medicina preventiva y la atención primaria en salud para comunidades marginadas.'),
            ('Tomás Guerrero Blanco',      'tomas.guerrero@gmail.com',     'CC', '1014567890', '1996-03-07', 'MASCULINO',   3, 'FLEXIBLE',        'Arquitecto con experiencia en diseño de espacios comunitarios. He participado en proyectos de vivienda social y mejoramiento de barrios.'),
            ('Alejandra Ruiz Medina',      'ale.ruiz@gmail.com',           'CC', '1015678901', '1994-11-12', 'FEMENINO',    1, 'ENTRE_SEMANA',    'Enfermera con 4 años de experiencia en urgencias. Me interesa el voluntariado en zonas rurales y la atención a población desplazada.'),
        ]

        for v in voluntarios:
            nombre, email, tipo_doc, num_doc, fecha_nac, genero, muni, disp, exp = v
            uid = str(uuid.uuid4())
            vid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO usuarios (id, nombre, email, password_hash, provider, rol, estado, email_verificado)
                VALUES (%s, %s, %s, %s, 'LOCAL', 'VOLUNTARIO', 'ACTIVO', true)
            """, (uid, nombre, email, HASH_PASS))
            cur.execute("""
                INSERT INTO voluntarios (id, usuario_id, tipo_documento, numero_documento,
                    fecha_nacimiento, genero, municipio_id, disponibilidad, experiencia,
                    esta_verificado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, false)
            """, (vid, uid, tipo_doc, num_doc, fecha_nac, genero, muni, disp, exp))
            print(f"  ✓ Voluntario: {nombre}")

        conn.commit()
        print('\n✅ Seed completo exitosamente.')
