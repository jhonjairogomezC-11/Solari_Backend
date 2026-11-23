# Solari — Documento de Sustentación del Proyecto

> Plataforma web que conecta **voluntarios** y **fundaciones** para gestionar
> convocatorias de voluntariado, con piloto en Bogotá D.C.
>
> Este documento describe el sistema **tal como está construido hoy en el código**:
> qué hace, para quién, con qué tecnologías, cómo está organizado, qué datos
> maneja y qué decisiones de arquitectura y seguridad se tomaron. Está pensado
> como material de apoyo para la sustentación ante el jurado.

---

## 1. Resumen ejecutivo

**Solari** es un ecosistema digital de voluntariado. Resuelve un problema real:
las personas que quieren ser voluntarias no tienen un lugar centralizado y
confiable para encontrar oportunidades afines a sus intereses, postularse,
hacer seguimiento a su participación y construir una trayectoria; y las
fundaciones carecen de un canal ordenado para publicar convocatorias, recibir
postulaciones y confirmar la asistencia de los voluntarios.

La plataforma tiene **tres tipos de usuario**:

- **Voluntario** — descubre convocatorias, se postula, guarda favoritos, acumula
  experiencia (XP) y logros, consulta su trayectoria y se comunica con soporte.
- **Organización** (fundación, refugio, colectivo o iniciativa ciudadana, con o
  sin constitución legal) — publica convocatorias individuales o recurrentes,
  revisa postulaciones con el porcentaje de compatibilidad, decide, confirma la
  asistencia, mantiene un perfil público y puede solicitar objetos o servicios
  gratuitos a los voluntarios. En el resto del documento se usa "fundación"
  como sinónimo.
- **Administrador** — supervisa usuarios, fundaciones, convocatorias,
  postulaciones y catálogos del sistema.

**Cobertura geográfica:** el piloto del proyecto de grado es en **Bogotá D.C.**
Los datos geográficos ya están cargados también para Cundinamarca, pensando en la
expansión: la base tiene **2 departamentos** (Bogotá D.C., Cundinamarca) y
**34 municipios** (Bogotá, Soacha, Chía, Cajicá, Zipaquirá, Facatativá, Funza,
Mosquera, Madrid, Fusagasugá, Girardot, La Calera, Sopó, Tocancipá, etc.).
Operar fuera de Bogotá queda como trabajo futuro.

---

## 2. Problema, objetivo y propuesta de valor

### 2.1 Problema
- Dispersión de la oferta de voluntariado: no hay un punto único de encuentro.
- Falta de verificación: no se sabe si una fundación es legítima ni si el
  voluntario realmente asistió.
- Nula retroalimentación y reconocimiento al voluntario.
- Procesos manuales (correos, formularios sueltos) propensos a error.

### 2.2 Objetivo general
Construir una plataforma web segura y funcional que conecte voluntarios y
fundaciones, permitiendo publicar convocatorias, postularse, gestionar el ciclo
completo de participación y reconocer la trayectoria del voluntario.

### 2.3 Propuesta de valor
- **Para el voluntario:** descubrimiento personalizado por intereses,
  trazabilidad de su participación, gamificación (XP, logros, ranking) y un canal
  de soporte directo.
- **Para la fundación:** publicación rica de convocatorias, control de cupos y
  postulaciones, verificación institucional.
- **Para el administrador:** control, moderación y gobierno de datos.

---

## 3. Arquitectura general del sistema

Solari está dividido en dos aplicaciones independientes que se comunican por
una **API REST** sobre HTTP/JSON.

```
┌──────────────────────────┐        HTTPS / JSON        ┌──────────────────────────┐
│   FRONTEND (Solari web)   │  ───────────────────────▶  │   BACKEND (Solari API)    │
│   React 19 + Vite + TS    │   Authorization: Bearer    │   FastAPI (Python 3.14)   │
│   Tailwind CSS v4         │  ◀───────────────────────  │   SQLAlchemy 2 (async)    │
└──────────────────────────┘        token JWT            └────────────┬─────────────┘
                                                                        │ psycopg 3 (async)
                                                                        ▼
                                                          ┌──────────────────────────┐
                                                          │   PostgreSQL (voluntapp)  │
                                                          │   Tipos ENUM, UUID, FKs   │
                                                          └──────────────────────────┘
```

### 3.1 Contexto de migración (importante para la sustentación)
El proyecto **nació en Laravel/PHP** y la base de datos PostgreSQL fue creada por
ese backend. El sistema actual es una **migración a Python/FastAPI** que opera
sobre **la misma base de datos**, de forma **aditiva y no destructiva**:

- No se renombran ni se eliminan tablas/columnas existentes.
- Las nuevas funcionalidades se añaden con **migraciones Alembic aditivas**
  (columnas nuevas *nullable* o con *default*, y tablas nuevas).
- Los JWT son compatibles (mismo secreto y algoritmo HS256), de modo que ambos
  backends podrían coexistir durante la transición.

Esta decisión está documentada en `docs/ADR-001-arquitectura-y-migracion.md`.

---

## 4. Stack tecnológico (lo que está realmente en el código)

### 4.1 Backend — `Solari backend/`
| Componente | Tecnología | Rol |
|---|---|---|
| Lenguaje | **Python 3.14** | Base del backend |
| Framework web | **FastAPI** (>=0.115) | API REST + documentación OpenAPI automática |
| Validación | **Pydantic v2** / pydantic-settings | Esquemas de entrada/salida y configuración |
| ORM | **SQLAlchemy 2** (async) | Acceso a datos con consultas parametrizadas |
| Driver BD | **psycopg 3** (async) | Conexión a PostgreSQL |
| Migraciones | **Alembic** | Evolución del esquema de forma versionada |
| Contraseñas | **Argon2id** (argon2-cffi) + bcrypt heredado | Hash seguro + rehash perezoso |
| Tokens | **PyJWT** (HS256) | Autenticación con JWT |
| Rate limiting | **slowapi** | Protección contra abuso/fuerza bruta |
| Autenticación social | **google-auth** | Inicio de sesión con Google (OIDC) |
| Servidor | **uvicorn** | Servidor ASGI |

### 4.2 Frontend — `Solari frontend/`
| Componente | Tecnología | Rol |
|---|---|---|
| Librería UI | **React 19** | Interfaz de usuario |
| Bundler | **Vite** | Desarrollo y build |
| Lenguaje | **TypeScript** | Tipado estático |
| Estilos | **Tailwind CSS v4** | Diseño (tema "solar" claro/oscuro) |
| Rutas | **React Router 7** | Navegación y rutas protegidas |
| Datos | **Axios** (TanStack Query instalado, aún sin uso) | Llamadas a la API y refresh automático de token |
| Formularios | **React Hook Form + Zod** | Formularios y validación en cliente |
| Animación / iconos | **Framer Motion + lucide-react** | Microinteracciones e iconografía |

### 4.3 Base de datos
- **PostgreSQL** (base `voluntapp`).
- Usa **tipos ENUM nativos** (roles, estados, modalidades, dificultad…),
  **UUID** como clave primaria en las entidades principales, **llaves foráneas**
  con `ON DELETE CASCADE/RESTRICT/SET NULL`, índices y restricciones `CHECK`.

---

## 5. Actores y casos de uso

### 5.1 Voluntario
1. Registrarse y completar su perfil (datos personales, documento, municipio,
   disponibilidad, intereses, etc.).
2. Subir foto de perfil y documento de identidad para verificación.
3. Seleccionar sus **intereses** (de un catálogo de ~36) para recibir
   recomendaciones personalizadas.
4. **Explorar** convocatorias con filtros (categoría, modalidad, municipio,
   búsqueda) y ver **recomendaciones** afines.
5. Ver el **detalle enriquecido** de una convocatoria.
6. **Postularse** y hacer seguimiento del estado (pendiente, en revisión,
   aceptada, rechazada, lista de espera, retirada, asistió…); retirarse con
   confirmación si ya fue aceptado.
7. Elegir entre **3 y 10 habilidades**; cada convocatoria muestra el porcentaje
   de compatibilidad (ordena el listado, nunca impide postularse).
8. Guardar **favoritos** (convocatorias y fundaciones).
9. Consultar su **trayectoria** (actividades, horas, fundaciones, historial).
10. Ver su **experiencia (XP)**, **nivel**, **logros** y posición en el **ranking**.
11. Publicar **objetos o servicios gratuitos** y coordinar la entrega con las
    organizaciones interesadas.
12. **Reseñar** a una organización tras una participación confirmada.
13. Abrir **tickets de soporte** y **solicitudes de cuenta/privacidad**.
14. Configurar **preferencias de notificación**.

### 5.2 Fundación
1. Registrarse (queda en estado `PENDIENTE` de verificación).
2. Completar el perfil institucional (representante legal; NIT y documento legal
   solo si está legalmente constituida).
3. **Crear convocatorias** (borrador) con información rica y entre 3 y 10
   habilidades requeridas; o una **actividad recurrente** (máximo 3 convocatorias
   por ciclo, con pausa hasta que la organización autorice el siguiente).
4. **Publicar**, **editar** o **cancelar** convocatorias.
5. Revisar las **postulaciones** con resumen de cupos, perfil del voluntario
   (sin datos sensibles), compatibilidad y habilidades coincidentes.
6. **Aceptar, poner en revisión, en lista de espera o rechazar** (el voluntario
   recibe un mensaje con plantilla respetuosa).
7. **Confirmar la asistencia** con calificación de 1 a 5 (esto otorga XP).
8. Mantener el **perfil público** (historia, misión, áreas, galería, contacto
   visible a elección) y responder reseñas.
9. Subir documentos privados y **solicitar la verificación** (la insignia la
   otorga un administrador).
10. Pedir objetos o servicios con "Me interesa".

### 5.3 Administrador
1. Gestionar usuarios, voluntarios y fundaciones.
2. Aprobar / rechazar / suspender fundaciones.
3. Supervisar convocatorias y postulaciones.
4. Gestionar catálogos.
5. **Responder tickets de soporte** (el usuario recibe notificación).
6. Resolver **solicitudes de privacidad** (aprobar no ejecuta; la ejecución exige
   una orden explícita).
7. **Verificar organizaciones** revisando documentos privados.
8. **Moderar reseñas**.
9. Consultar la **auditoría**: toda acción administrativa queda registrada.

---

## 6. Módulos funcionales (estado actual del código)

### 6.1 Autenticación y cuentas
- Registro de voluntario y de fundación (endpoints separados y uno compatible).
- Login local con **Argon2id** y verificación de hashes **bcrypt** heredados con
  *rehash perezoso* (si el usuario tenía contraseña antigua, al iniciar sesión se
  actualiza al nuevo algoritmo).
- Login con **Google (OIDC)**.
- **Refresh token** con rotación y un solo uso.
- Verificación de correo y recuperación/restablecimiento de contraseña.
- Aceptación de **documentos legales** (términos y política de datos) con registro
  de evidencia (versión, fecha, IP, user-agent) conforme a la **Ley 1581 de 2012**.

### 6.2 Perfil del voluntario
- Datos de identidad **inmutables** tras el registro (documento, fecha de
  nacimiento, género): no se pueden cambiar desde el perfil; requieren solicitud
  a soporte. Esto protege la integridad de los datos.
- Datos editables: dirección, teléfono, nivel educativo, profesión, idiomas,
  preferencia de modalidad, contacto de emergencia, descripción, experiencia.
- **Foto de perfil y documento de identidad** almacenados de forma persistente en
  el servidor (no en el navegador), con validación de tipo real por *magic bytes*,
  límite de tamaño y nombre aleatorio (previene archivos maliciosos y colisiones).

### 6.3 Convocatorias (publicaciones)
Cada convocatoria puede incluir: título, descripción, categoría (área de impacto),
modalidad (presencial / virtual / híbrida), municipio y dirección, enlace virtual,
fechas y horarios, cupos, rango de edad, requisitos, habilidades deseadas,
contacto, y **campos enriquecidos**: objetivo, impacto social esperado,
actividades del voluntario, perfil de beneficiarios, qué llevar, recomendaciones,
política de cancelación, si incluye transporte/alimentación/seguro, si otorga
certificado, horas reconocidas, nivel de experiencia, fecha límite de postulación,
dificultad y marca de urgente.

Estados de una convocatoria: `BORRADOR`, `PENDIENTE_APROBACION`, `PUBLICADA`,
`CERRADA`, `CANCELADA`, `COMPLETADA`, `FINALIZADA`.

### 6.4 Postulaciones
- Un voluntario se postula a una convocatoria publicada.
- **Control de cupos con bloqueo de fila** (`SELECT ... FOR UPDATE`): evita la
  condición de carrera cuando varios voluntarios intentan ocupar el último cupo
  al mismo tiempo. Si el cupo está lleno, la postulación entra en **lista de espera**.
- **No se permiten postulaciones duplicadas** a la misma convocatoria.
- No se permite postular después de la **fecha límite**.
- Estados: `PENDIENTE`, `EN_REVISION`, `ACEPTADO`, `RECHAZADO`, `LISTA_ESPERA`,
  `RETIRADO`, `CANCELADO_FUNDACION`, `ASISTIO`, `NO_ASISTIO`.
- La fundación responde (acepta/rechaza) y luego **confirma asistencia**.

### 6.5 Intereses y recomendaciones
- Catálogo de **36 intereses** (protección animal, medio ambiente, educación,
  infancia, salud, derechos humanos, tecnología, etc.).
- El voluntario elige sus intereses (ideal 10) y se guardan en la BD.
- **Motor de recomendación por afinidad** (puntuación explicable): suma puntos por
  coincidencia de categoría con los intereses, por municipio del voluntario, por
  modalidad accesible, por cupo disponible y por proximidad de la fecha. Descarta
  convocatorias no publicadas, ya iniciadas o con fecha límite vencida.

### 6.6 Gamificación (experiencia, logros y ranking)
- **XP (puntos):** se otorgan **únicamente** cuando la fundación confirma la
  asistencia (`ASISTIO`). Nunca por registrarse, iniciar sesión ni postularse.
  Esto es un diseño **antifraude**.
- Fórmula actual: **50 XP base por asistencia + 5 XP por cada hora reconocida**.
  Desbloquear un logro **no** otorga XP adicional.
- **Niveles:** 8 niveles calculados desde el XP total (Chispa, Destello,
  Amanecer, Resplandor, Aurora, Sol naciente, Sol pleno, Supernova). Son solo un
  reconocimiento visual: no desbloquean funcionalidades.
- **Idempotencia:** una misma participación nunca otorga XP dos veces (se verifica
  por transacción asociada a la postulación).
- **Logros:** catálogo de 11 logros (por participaciones, por puntos, por
  dificultad, por convocatorias urgentes). Un logro se desbloquea **una sola vez**
  (restricción de unicidad en la BD).
- **Historial de XP:** cada movimiento queda registrado para trazabilidad.
- **Ranking:** top 1000 calculado con `ROW_NUMBER()` sobre el XP histórico; el
  voluntario ve su posición real aunque esté fuera del top.

### 6.7 Favoritos
- El voluntario guarda **convocatorias** y **fundaciones**.
- Persisten en BD, vinculados al voluntario; sin duplicados; se mantienen entre
  sesiones.

### 6.8 Notificaciones
- Se generan ante **eventos reales**: nueva postulación, aceptada/rechazada,
  asistencia confirmada, retiro, XP obtenido, logro desbloqueado, respuesta de
  soporte, etc.
- El usuario puede marcarlas como leídas (una o todas) y configurar sus
  **preferencias** por tipo de evento; el sistema las respeta al generar cada
  notificación. Las notificaciones son internas (no se envían por correo).

### 6.9 Centro de ayuda y privacidad
- **Tickets de soporte** con categoría, asunto, descripción, número consecutivo
  legible, estado (abierto, en revisión, pendiente de información, resuelto,
  cerrado) e hilo de mensajes voluntario ↔ administrador. El administrador
  responde desde su panel (`/admin/gestion`) y el usuario recibe una notificación.
- **Solicitudes de cuenta/privacidad** (bloqueo temporal, inhabilitación,
  eliminación de cuenta, eliminación de datos, reporte de acceso sospechoso…).
  Estas solicitudes **no se ejecutan automáticamente**: quedan `PENDIENTE` para
  revisión administrativa, y el sistema impide duplicados en curso. Aprobar una
  solicitud tampoco la ejecuta: hace falta una orden explícita del administrador,
  que no puede resolver sus propias solicitudes. La anonimización conserva las
  postulaciones y los puntos. Alineado con la **Ley 1581 de 2012** (habeas data).

### 6.10 Trayectoria del voluntario
- Resumen de actividades completadas, horas acumuladas, fundaciones con las que
  colaboró y XP total, más el historial de todas sus participaciones con su estado,
  horas y disponibilidad de certificado.

### 6.11 Habilidades y compatibilidad
- Catálogo de **108 habilidades** en 7 categorías (19 marcadas como profesionales).
- Cada voluntario elige entre 3 y 10; cada convocatoria exige entre 3 y 10 al publicarse.
- Compatibilidad = habilidades coincidentes / requeridas × 100. **Ordena** el
  listado y se muestra en la tarjeta y el detalle, pero nunca excluye a nadie.

### 6.12 Actividades recurrentes
- Una organización define un intervalo (días, semanas o meses) y una plantilla.
- Se publican **hasta 3 convocatorias por ciclo**; después la programación queda
  **pausada** hasta que la organización la autorice de forma explícita.

### 6.13 Objetos y servicios gratuitos
- Un voluntario publica un **objeto** (con cantidad) o un **servicio** (con
  habilidades). No hay precios ni pagos: el sistema rechaza textos de venta.
- La organización pulsa "Me interesa"; coordinan por mensajes dentro de la
  solicitud (se detectan y bloquean datos personales) y la entrega se completa
  solo cuando **ambas partes la confirman**.

### 6.14 Perfil público, verificación y reseñas
- Perfil público de la organización: historia, misión, áreas, galería (con
  indicación de menores y autorización de imagen), contacto visible a elección y
  **estadísticas calculadas con registros reales** (actividades realizadas vs.
  creadas, participaciones confirmadas).
- **Verificación documental:** los documentos se guardan en una carpeta privada
  (solo el dueño y los administradores pueden descargarlos). La insignia la
  otorga un administrador, puede revocarla, y siempre se muestra con un aviso de
  que no es garantía absoluta.
- **Reseñas:** solo de voluntarios con participación confirmada; la organización
  puede responder; un administrador puede ocultarlas con motivo.

---

## 7. Modelo de datos (entidades principales)

> Todas las entidades principales usan **UUID** como identificador. Los campos de
> estado usan **ENUM** nativos de PostgreSQL.

| Entidad | Descripción | Relaciones clave |
|---|---|---|
| `usuarios` | Cuenta base (nombre, email, rol, estado, proveedor) | 1:1 con voluntario o fundación |
| `voluntarios` | Perfil del voluntario (documento, municipio, disponibilidad, intereses, horas, foto…) | pertenece a `usuarios`; FK a `municipios` |
| `fundaciones` | Perfil institucional (NIT, representante, verificación) | pertenece a `usuarios` |
| `publicaciones` | Convocatorias de voluntariado | pertenece a `fundaciones`; FK a `areas_impacto` y `municipios`; N:M con `habilidades` |
| `postulaciones` | Postulación de un voluntario a una convocatoria | FK a `publicaciones` y `voluntarios` |
| `voluntario_favoritos` | Favoritos (convocatoria o fundación) | FK a `voluntarios`, `publicaciones`, `fundaciones` |
| `notificaciones` | Avisos a los usuarios | FK a `usuarios` |
| `intereses` / `voluntario_intereses` | Catálogo y selección de intereses | N:M voluntario–interés |
| `logros` / `voluntario_logros` | Catálogo de logros y los obtenidos | N:M voluntario–logro (único) |
| `voluntario_puntos` / `transacciones_puntos` | Saldo de XP e historial de movimientos | 1:1 y 1:N con `voluntarios` |
| `tickets_soporte` / `ticket_mensajes` | Soporte y su conversación | FK a `usuarios` |
| `solicitudes_cuenta` | Solicitudes de privacidad/cuenta | FK a `usuarios` |
| `preferencias_notificacion` | Preferencias por usuario | 1:1 con `usuarios` |
| `auditoria_perfil` | Registro de cambios sensibles | FK a `usuarios` |
| `documentos_legales` / `documento_legal_versiones` / `usuario_aceptaciones_legales` | Términos legales y evidencia de aceptación | Ley 1581/2012 |
| Catálogos: `departamentos`, `municipios`, `areas_impacto`, `habilidades` | Datos maestros | — |

### Catálogos cargados (datos maestros reales)
- **Departamentos (2):** Bogotá D.C., Cundinamarca.
- **Municipios (34):** Bogotá, Soacha, Chía, Cajicá, Zipaquirá, Facatativá,
  Funza, Mosquera, Madrid, Fusagasugá, Girardot, La Calera, Sopó, Tocancipá,
  Gachancipá, Tabio, Tenjo, Cota, Sibaté, Arbeláez, entre otros.
- **Áreas de impacto (11):** Educación, Salud, Medio Ambiente, Derechos Humanos,
  Infancia, Adulto Mayor, Discapacidad, Cultura, Deportes, Tecnología,
  Inclusión Social.
- **Habilidades:** Educación, Tecnología, Salud, Medio Ambiente, Arte, Deportes,
  Comunicación, Liderazgo, Idiomas, Cocina, etc.
- **Intereses (36)** y **Logros (11)**.

---

## 8. Flujo completo de uso (ciclo de vida de una participación)

```
1. La FUNDACIÓN se registra  ──▶  queda PENDIENTE de verificación
2. El ADMIN aprueba la fundación
3. La FUNDACIÓN crea una convocatoria (BORRADOR) y la PUBLICA
4. El VOLUNTARIO completa su perfil y elige sus intereses
5. El sistema RECOMIENDA convocatorias afines al voluntario
6. El VOLUNTARIO se postula  ──▶  PENDIENTE (o LISTA_ESPERA si no hay cupo)
7. La FUNDACIÓN revisa y ACEPTA o RECHAZA  ──▶  notificación al voluntario
8. Tras la actividad, la FUNDACIÓN CONFIRMA ASISTENCIA (ASISTIO)
9. El sistema OTORGA XP al voluntario (50 + horas×5), evalúa LOGROS y actualiza
   su TRAYECTORIA, HORAS y posición en el RANKING
10. El VOLUNTARIO ve su historial, logros y certificados disponibles
```

---

## 9. Seguridad (controles implementados)

| Riesgo | Mitigación en Solari |
|---|---|
| Inyección SQL | ORM con consultas **parametrizadas**; sin concatenación de SQL |
| Asignación masiva | Pydantic `extra="forbid"`; el **rol y estado los fija el backend** |
| Escalada de privilegios | El `rol` enviado por el cliente se ignora; nunca concede ADMIN |
| Fuerza bruta | **Rate limiting** por IP en login y endpoints sensibles |
| Enumeración de cuentas | Mensajes genéricos en login/registro/recuperación |
| Robo/reuso de tokens | Refresh **hasheado (SHA-256)**, con **rotación** y **un solo uso** |
| Contraseñas | **Argon2id** + rehash perezoso de bcrypt heredado |
| JWT inseguro | Algoritmo **fijado (HS256)**, rechazo de `none`, claims requeridos |
| Condición de carrera (cupos) | **Bloqueo de fila** `SELECT ... FOR UPDATE` |
| Integridad de identidad | Documento/fecha nacimiento/género **inmutables** tras registro |
| Fraude de gamificación | XP **solo** por asistencia confirmada; logros **únicos**; historial auditable |
| Archivos maliciosos | Validación por **magic bytes**, límite de tamaño, nombre aleatorio |
| Filtración en errores | Manejador central: nunca expone trazas ni SQL |
| CORS inseguro | Orígenes **explícitos** por configuración (sin comodín con credenciales) |
| Protección de datos | Aceptaciones legales con evidencia; solicitudes de privacidad con flujo administrativo |

---

## 10. Estructura del código

### 10.1 Backend (`Solari backend/app/`)
Arquitectura por capas, con separación clara de responsabilidades:

```
app/
├── main.py            # Arranque de FastAPI, CORS, routers, archivos estáticos
├── core/              # Configuración, seguridad (hash/JWT), excepciones, rate limit
├── db/                # Motor y sesión async de SQLAlchemy
├── models/            # Mapeo ORM de las tablas (usuario, voluntario, publicación…)
├── schemas/           # Esquemas Pydantic (entrada/salida de la API)
├── repositories/      # Acceso a datos (consultas)
├── services/          # Reglas de negocio (auth, postulación, gamificación…)
├── api/v1/            # Endpoints REST agrupados por módulo
└── email/             # Envío de correos
alembic/               # Migraciones de base de datos (versionadas)
```

**Patrón:** el *endpoint* (api) recibe la petición → delega en un *service*
(reglas de negocio) → que usa *repositories* (datos) sobre *models* → y responde
con *schemas*. Esto hace el código mantenible y testeable.

### 10.2 Frontend (`Solari frontend/src/`)
```
src/
├── auth/              # Contexto de sesión (token, usuario autenticado)
├── components/
│   ├── ui/            # Botones, inputs, alerts, badges, logo… (reutilizables)
│   ├── layout/        # Layout de la app, del admin y de autenticación
│   ├── convocatorias/ # Tarjeta de convocatoria, botón de favorito
│   └── routing/       # Guardias de rutas (pública / protegida / admin)
├── pages/
│   ├── app/           # Dashboard, Explorar, Detalle, Perfil, Favoritos,
│   │                  # Intereses, Logros, Ranking, Trayectoria, Soporte,
│   │                  # Notificaciones, Mis postulaciones, Crear convocatoria…
│   └── admin/         # Panel de administración
├── services/          # Llamadas a la API (auth, convocatorias, voluntario)
├── types/             # Tipos TypeScript del dominio
├── hooks/             # useFavoritos, useTheme
└── lib/               # Cliente Axios (refresh automático), config, utilidades
```

---

## 11. API — endpoints principales (base `/api/v1`)

| Área | Método y ruta | Descripción |
|---|---|---|
| Auth | `POST /auth/register` · `/login` · `/refresh` · `/logout` | Registro, sesión, tokens |
| Auth | `POST /auth/google` · `/forgot-password` · `/reset-password` | Google y recuperación |
| Perfil | `GET/PUT /perfil/voluntario` · `/perfil/fundacion` | Ver y editar perfil |
| Perfil | `POST /perfil/voluntario/foto` · `/documento` · `/fundacion/logo` | Subida de archivos |
| Convocatorias | `GET /publicaciones` · `GET /publicaciones/{id}` | Explorar y detalle |
| Convocatorias | `POST/PUT /publicaciones` · `/publicar` · `/cancelar` | Gestión (fundación) |
| Postulaciones | `POST /postulaciones` · `GET /mis-postulaciones` · `/retirar` | Voluntario |
| Postulaciones | `PUT /postulaciones/{id}/responder` · `/confirmar-asistencia` | Fundación |
| Favoritos | `GET/POST /favoritos/...` (convocatorias y fundaciones) | Favoritos |
| Gamificación | `GET /gamificacion/resumen` · `/logros` · `/xp/historial` | XP y logros |
| Ranking | `GET /ranking` | Ranking top 1000 |
| Intereses | `GET /intereses` · `GET/PUT /mis-intereses` | Catálogo y selección |
| Trayectoria | `GET /voluntario/trayectoria` · `/recomendaciones` | Historial y recomendación |
| Notificaciones | `GET /notificaciones` · `/no-leidas` · `marcar-leida(s)` | Avisos |
| Soporte | `GET/POST /soporte/tickets` · `/responder` · `/cerrar` | Centro de ayuda |
| Privacidad | `GET/POST /soporte/solicitudes-cuenta` | Solicitudes de cuenta |
| Cuenta | `GET/PUT /cuenta/preferencias-notificacion` | Preferencias |
| Catálogos | `GET /catalogos/departamentos` · `municipios` · `areas-impacto` · `habilidades` | Datos maestros |
| Legal | `GET /legal/documentos` | Documentos legales vigentes |
| Salud | `GET /health` | Verificación de app + BD |

> La documentación interactiva completa (OpenAPI/Swagger) se genera automáticamente
> en `/docs` al ejecutar el backend.

---

## 12. Cómo ejecutar el proyecto (demostración)

### 12.1 Requisitos
- **PostgreSQL** con la base `voluntapp` creada y accesible.
- **Python 3.14** con `uv` (gestor de entornos/paquetes).
- **Node.js 20+** para el frontend.

### 12.2 Backend
```powershell
cd "Solari backend"
uv venv --python 3.14
uv sync
copy .env.example .env          # configurar DATABASE_URL y JWT_SECRET
uv run alembic upgrade head     # aplica las migraciones
uv run python run.py            # arranca en http://127.0.0.1:8080
```
> En Windows se usa `run.py` porque fija el *event loop* compatible con psycopg
> async. El puerto por defecto es **8080** (configurable con `SOLARI_PORT`).
> La documentación de la API queda en `http://127.0.0.1:8080/docs`.

### 12.3 Frontend
```powershell
cd "Solari frontend"
npm install
copy .env.example .env          # VITE_API_BASE_URL apuntando al backend
npm run dev                     # http://localhost:5173
```

### 12.4 Estado de los datos (entorno de desarrollo)
La base de datos de desarrollo ya está poblada con datos de prueba que permiten
demostrar el sistema de inmediato:

| Tabla | Registros |
|---|---|
| Usuarios | 209 (157 voluntarios, 46 fundaciones, 6 administradores) |
| Publicaciones (convocatorias) | 257 |
| Postulaciones | 3 857 |
| Habilidades (catálogo) | 108 |
| Intereses (catálogo) | 36 |
| Logros (catálogo) | 11 |
| Municipios | 34 |

Son **datos sintéticos de demostración**, no resultados del piloto.

---

## 13. Decisiones de diseño destacadas (para defender ante el jurado)

1. **Migración no destructiva y coexistencia.** Se reutilizó la base de datos
   existente sin romperla, mediante migraciones aditivas y JWT compatibles. Esto
   demuestra manejo de un sistema real heredado, no un proyecto desde cero ideal.

2. **Arquitectura por capas.** Endpoints → servicios → repositorios → modelos.
   Facilita el mantenimiento, las pruebas y el crecimiento del sistema.

3. **Seguridad por diseño.** No es una capa agregada al final: está en el hash de
   contraseñas, el manejo de tokens, el rate limiting, la validación estricta, el
   control de concurrencia y la protección de datos personales.

4. **Gamificación justa y verificable.** La experiencia solo se gana con
   participación **confirmada por la fundación**, es idempotente y auditable. No
   se puede "inflar" el XP registrándose o postulándose en masa.

5. **Integridad de datos sensibles.** El documento de identidad y otros datos
   críticos no se pueden alterar libremente; los cambios pasan por un flujo
   controlado y auditable.

6. **Cumplimiento normativo.** Registro de aceptación de términos y solicitudes de
   privacidad alineados con la **Ley 1581 de 2012** de protección de datos
   personales en Colombia.

---

## 14. Alcance actual y trabajo futuro

### Implementado y funcional
Autenticación completa, perfiles, convocatorias enriquecidas, postulaciones con
control de cupos y lista de espera, habilidades y compatibilidad, actividades
recurrentes, intereses y recomendaciones, gamificación (XP, niveles, logros,
ranking), objetos y servicios gratuitos, perfil público con verificación
documental y reseñas, favoritos, notificaciones con preferencias, trayectoria,
soporte (voluntario y administrador), solicitudes de privacidad, panel de
administración con auditoría. Verificado con 66 pruebas automáticas del backend;
el frontend compila y pasa el lint, sin pruebas automáticas de interfaz.

### Trabajo futuro sugerido
- Certificados de participación en **PDF** descargables.
- **Mensajería** general voluntario ↔ organización (hoy solo existe dentro de una
  solicitud de objetos o servicios).
- Autorización de representantes para **menores de edad**.
- Operación en Cundinamarca (los datos geográficos ya están cargados).
- **Calendario** de actividades y recordatorios automáticos.
- Verificación de identidad reforzada y **autenticación multifactor (MFA)**.
- Gestión de **sesiones/dispositivos** activos y alertas de seguridad.
- Evaluación de actividades y reputación de fundaciones.
- Notificaciones en tiempo real (WebSocket) en lugar de sondeo.

---

## 15. Glosario rápido

- **Convocatoria / Publicación:** oferta de voluntariado creada por una fundación.
- **Postulación:** solicitud de un voluntario para participar en una convocatoria.
- **XP (experiencia):** puntos que acumula el voluntario por participación verificada.
- **Logro:** reconocimiento que se desbloquea al cumplir una condición.
- **Ranking:** clasificación de voluntarios por XP acumulado.
- **Modalidad:** presencial, virtual o híbrida.
- **Área de impacto / Categoría:** temática de la convocatoria (educación, salud…).
- **ENUM:** tipo de dato con un conjunto cerrado de valores válidos.
- **UUID:** identificador único universal usado como clave primaria.
- **JWT:** token firmado que acredita la sesión del usuario.
- **Migración (Alembic):** cambio versionado y reversible del esquema de la BD.

---

*Documento generado como material de sustentación. Describe el estado del código
y la base de datos del proyecto Solari (backend FastAPI + frontend React) a la
fecha de su elaboración.*
