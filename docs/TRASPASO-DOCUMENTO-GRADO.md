# Traspaso para el agente del documento de grado

Este archivo describe el estado **real y verificado** del código de Solari a noviembre de 2026. Sirve para completar los campos `[Confirmar…]`, la Tabla 12 y las secciones 4.3, 4.10, 4.11 y 4.12 del Proyecto Aplicado. Todo lo que figura aquí como "implementado" existe en el repositorio y se puede ejecutar. Lo que no se pudo comprobar está marcado como **no verificado**.

---

## 1. Qué se verificó y cómo

| Comprobación | Resultado |
|---|---|
| Pruebas del backend (`pytest`) | 66 aprobadas (24 de autenticación, 21 unitarias, 21 de integración contra PostgreSQL real) |
| Compilación del frontend (`tsc -b`) | Sin errores |
| Lint del frontend (`eslint --max-warnings 0`) | Sin errores ni advertencias |
| Build del frontend (`vite build`) | Correcto |
| Rutas HTTP registradas en FastAPI | 115 |
| Migraciones Alembic | Cabeza en `0004_notif_post` (0001 base, 0002 módulo voluntario, 0003 alineación con el documento, 0004 notificación de postulación actualizada) |

**No verificado:** no se hicieron pruebas automáticas del frontend (ni unitarias ni de extremo a extremo con navegador). Las pantallas nuevas compilan y su contrato con el backend se revisó contra los esquemas, pero no se recorrieron manualmente en un navegador. El documento no debe afirmar "pruebas de interfaz" hasta que el autor las haga.

---

## 2. Tabla 12 actualizada (estado final de cada funcionalidad)

| Funcionalidad | Estado real | Dónde está |
|---|---|---|
| Registro y login (voluntario, organización, admin) | Implementado | `api/v1/auth.py`, `AuthService` |
| Habilidades y coincidencia | Implementado: 108 habilidades en 7 categorías, 3–10 por voluntario y por actividad, % = coincidentes / requeridas × 100, ordena sin excluir | `services/coincidencia.py`, `habilidad_service.py` |
| Actividades recurrentes | Implementado: intervalo en días, semanas o meses; máximo 3 convocatorias por ciclo; pausa hasta autorización explícita | `programacion_service.py` |
| Estados de postulación | Implementado: PENDIENTE, EN_REVISION, LISTA_ESPERA, ACEPTADO, RECHAZADO, RETIRADO, CANCELADO_FUNDACION, ASISTIO, NO_ASISTIO | `postulacion_service.py` |
| Cupos y lista de espera | Implementado con bloqueo de fila (`SELECT … FOR UPDATE`); el cupo se valida al aceptar | `postulacion_service.py` |
| Historial de cambios con actor | Implementado (`postulacion_historial`) | `GET /postulaciones/{id}/historial` |
| Objetos y servicios (donación gratuita) | Implementado: objetos con cantidad, servicios con habilidades, "Me interesa", mensajería, confirmación de ambas partes | `ofrecimiento_service.py` |
| Mensajería | Implementada solo dentro de una solicitud de interés (no hay chat general) | `mensajes_interes` |
| Perfil público de la organización | Implementado: historia, misión, áreas, galería, privacidad de contacto, estadísticas | `organizacion_service.py` |
| Verificación documental | Implementada: documentos privados, solicitud, aprobación, rechazo, petición de información y revocación por un administrador | `organizacion_service.py`, `admin_gestion_service.py` |
| Reseñas | Implementadas: solo con participación confirmada, respuesta de la organización, moderación del administrador | `organizacion_service.py` |
| Gamificación | Implementada: 50 XP + 5 por hora reconocida, solo con asistencia confirmada, sin bono por logro; 8 niveles solo visuales; 11 logros; ranking top 1000 | `gamificacion_service.py` |
| Soporte (voluntario y administrador) | Implementado en ambos lados: tickets, respuesta del administrador con notificación | `soporte_service.py`, `admin_gestion_service.py` |
| Solicitudes de privacidad (Ley 1581) | Implementadas: aprobar no ejecuta; la ejecución exige una orden explícita; un administrador no resuelve sus propias solicitudes; la anonimización conserva postulaciones y puntos | `admin_gestion_service.py` |
| Auditoría de acciones administrativas | Implementada: toda acción del panel queda en `admin_acciones` | `auditoria_service.py` |
| Preferencias de notificación | Implementadas y aplicadas al generar cada notificación. No existe canal de correo para notificaciones (se retiró el interruptor porque no estaba conectado) | `notificacion_service.py` |
| Autenticación con Google | Implementada en backend (`google-auth`) | `auth_service.py` |
| Certificados en PDF | **No implementado** | — |
| Pagos o intercambios comerciales | **No existen, por diseño (R1)**; el validador rechaza precios en los ofrecimientos | `schemas/ofrecimiento.py` |

---

## 3. Correcciones a la Tabla 7 (tecnologías)

- **TanStack Query** está instalado (`@tanstack/react-query` 5.104) y montado en `main.tsx`, pero **ninguna pantalla usa `useQuery`**. Los datos se cargan con axios desde `services/*`. El documento no debe decir que TanStack Query gestiona el estado del servidor; puede decir "instalado para uso futuro".
- La arquitectura es **por capas** (API → servicios → repositorios → modelos) **inspirada en arquitectura limpia**, sin aplicarla de forma estricta. Evitar "arquitectura limpia" a secas.
- Versiones reales (de `pyproject.toml` y `package.json`):

| Componente | Versión declarada |
|---|---|
| Python | ≥ 3.14 |
| FastAPI | ≥ 0.115 |
| SQLAlchemy (asíncrono) | ≥ 2.0.36 |
| psycopg | ≥ 3.2 |
| Alembic | ≥ 1.14 |
| Pydantic | ≥ 2.9 |
| Argon2 / bcrypt | argon2-cffi ≥ 23.1 / bcrypt ≥ 4.2 |
| slowapi (límite de peticiones) | ≥ 0.1.9 |
| pytest | ≥ 8.3 |
| PostgreSQL | base `voluntapp` (versión del servidor local; confirmar con `SELECT version();`) |
| React | ^19.3 |
| Vite | ^8.3 |
| TypeScript | ~6.0 |
| Tailwind CSS | ^4.3 |
| React Router | ^7.18 |
| axios | ^1.20 |
| React Hook Form + Zod | ^7.91 + ^4.6 |
| Framer Motion | ^14.6 |

Las versiones con `≥` son mínimos declarados; la versión instalada exacta está en `uv.lock` y `package-lock.json`.

---

## 4. Reglas R1–R13 → implementación y prueba

| Regla | Implementación | Prueba que la respalda |
|---|---|---|
| R1 Gratuito, sin pagos | No hay pasarela; `OfrecimientoCreate` rechaza precios | `test_ofrecimiento_gratuito_rechaza_precios`, `test_ofrecimiento_gratuito_valido` |
| R2 La coincidencia ordena, no restringe | `coincidencia.py` solo calcula el porcentaje; el listado ordena y no filtra | `test_coincidencia_ejemplo_del_documento`, `test_coincidencia_sin_requeridas_es_cero`, `test_r2_la_coincidencia_ordena_pero_no_excluye` |
| R3 Entre 3 y 10 habilidades | Validación al guardar habilidades y al publicar | `test_r3_voluntario_entre_3_y_10_habilidades`, `test_publicar_exige_entre_3_y_10_habilidades`, `test_servicio_requiere_habilidades` |
| R4 Máximo 3 convocatorias recurrentes y pausa hasta autorización | `programacion_service.py` | `test_r4_recurrente_genera_tres_y_se_pausa_hasta_autorizar`, `test_siguiente_fecha_dias_semanas_meses` |
| R5 Cupos postulados vs. aceptados sin exceder | Bloqueo de fila al aceptar | `test_r5_r7_r8_cupos_lista_espera_retiro_e_historial` |
| R6 Decisión de la organización con plantillas respetuosas | `notificacion_service.py` y plantillas `msg_*` | `test_plantilla_de_rechazo_es_respetuosa`, `test_notificaciones_respetan_preferencias` |
| R7 Retiro con confirmación y libera el cupo | `retirar(confirmar=True)` si está ACEPTADO | `test_r5_r7_r8_cupos_lista_espera_retiro_e_historial` |
| R8 Historial de cambios con actor | `postulacion_historial` | `test_r5_r7_r8_cupos_lista_espera_retiro_e_historial` |
| R9 Entrega completada solo con confirmación de ambas partes | `ofrecimiento_service.confirmar` | `test_cantidades_se_controlan_y_la_entrega_requiere_ambas_confirmaciones`, `test_cancelar_libera_la_cantidad_reservada` |
| R10 Documentos privados e insignia solo por administrador | Carpeta `private_uploads/`, endpoint autenticado `/archivos/privado/…` | `test_r10_documentos_privados_solo_para_el_dueno_y_admin`, `test_verificacion_documental_flujo_completo_con_auditoria` |
| R11 Estadísticas con registros reales | `organizacion_service.estadisticas` | `test_r11_estadisticas_distinguen_publicadas_de_realizadas` |
| R12 Reseñas solo con participación confirmada | `crear_resena` | `test_r12_resenas_solo_con_participacion_confirmada_y_moderacion` |
| R13 Organizaciones sin constitución legal | NIT y documento opcionales si `constituida_legalmente = false` | `test_r13_organizacion_sin_constitucion_legal_puede_registrarse`, `test_organizacion_sin_constitucion_no_exige_nit`, `test_organizacion_constituida_exige_nit_y_documento` |

Pruebas adicionales: XP solo por asistencia (`test_xp_solo_por_asistencia_50_mas_5_por_hora_sin_bono_de_logro`), niveles (`test_niveles`), mensajería sin datos personales (`test_mensajeria_no_expone_datos_personales`), privacidad del perfil público (`test_perfil_publico_respeta_privacidad_de_contacto`), soporte del administrador (`test_admin_responde_ticket_notifica_y_audita`), solicitudes de cuenta (`test_solicitud_de_eliminacion_no_se_ejecuta_sin_controles_y_conserva_registros`, `test_admin_no_resuelve_solicitudes_propias`), auditoría (`test_panel_admin_deja_rastro_de_auditoria`).

Comando para reproducir: `cd "Solari backend"` y luego `.venv\Scripts\python.exe -m pytest tests -q -p no:warnings`.

---

## 5. Datos para las Figuras 1–4

**Figura 1 (arquitectura).** Navegador (React + Vite) → HTTPS/JSON → FastAPI (`/api/v1`) → servicios → repositorios → SQLAlchemy asíncrono → PostgreSQL `voluntapp`. Lateral: almacenamiento de archivos (`uploads/` público para fotos y logos; `private_uploads/` para documentos, servido solo con sesión), correo SMTP, Google Sign-In, Alembic para migraciones.

**Figura 2 (casos de uso).**
- Voluntario: registrarse, completar perfil, elegir habilidades e intereses, explorar convocatorias ordenadas por compatibilidad, postularse, retirarse, ver historial, publicar objetos o servicios, reseñar organizaciones, consultar logros y ranking, abrir tickets de soporte, solicitar privacidad.
- Organización: registrarse (con o sin constitución legal), completar perfil público, crear convocatorias (individuales o recurrentes), decidir postulaciones (aceptar, revisión, lista de espera, rechazar), confirmar asistencia con calificación, solicitar objetos o servicios ("Me interesa"), subir documentos y pedir verificación, responder reseñas.
- Administrador: gestionar usuarios, verificar voluntarios y organizaciones, moderar reseñas, responder tickets, resolver solicitudes de privacidad, consultar la auditoría.

**Figura 3 (modelo entidad-relación).** Núcleo: `usuarios` 1—1 `voluntarios` / `fundaciones` / `admin_perfiles`; `fundaciones` 1—N `publicaciones`; `publicaciones` N—M `habilidades`; `voluntarios` N—M `habilidades` e `intereses`; `voluntarios` 1—N `postulaciones` N—1 `publicaciones`; `postulaciones` 1—N `postulacion_historial`; `programaciones_recurrentes` 1—N `publicaciones`; `voluntarios` 1—N `ofrecimientos` 1—N `solicitudes_interes` N—1 `fundaciones`; `solicitudes_interes` 1—N `mensajes_interes`; `fundaciones` 1—N `fundacion_galeria`, `fundacion_documentos`, `resenas_organizacion`; `voluntarios` 1—N `transacciones_puntos`, `voluntario_logros`; `usuarios` 1—N `tickets_soporte` 1—N `ticket_mensajes`; `usuarios` 1—N `solicitudes_cuenta`; `admin_perfiles` 1—N `admin_acciones`. **Detalle importante:** `admin_acciones.admin_id` e `historial_estados_voluntario.admin_id` referencian `admin_perfiles.id`, no `usuarios.id`.

**Figura 4 (endpoints por módulo, base `/api/v1`).** Autenticación y perfil; catálogos (`/catalogos/*`); habilidades (`/mis-habilidades`); publicaciones (`/publicaciones`, `/mis-publicaciones`); programaciones (`/programaciones`, `/mis-programaciones`); postulaciones (`/postulaciones`, `/mis-postulaciones`, `…/responder`, `…/confirmar-asistencia`, `…/historial`); ofrecimientos (`/ofrecimientos`, `/mis-ofrecimientos`, `/solicitudes-interes`); organizaciones (`/organizaciones/{id}`, `/organizaciones/{id}/resenas`, `/perfil/fundacion/*`); gamificación; favoritos; notificaciones; soporte; archivos privados (`/archivos/privado/…`); administración (`/admin/*`, incluidos `/admin/soporte/tickets`, `/admin/solicitudes-cuenta`, `/admin/verificaciones`, `/admin/resenas`, `/admin/auditoria`). Total: 115 rutas. La lista exacta está en `http://127.0.0.1:8080/docs`.

---

## 6. Catálogos reales

| Catálogo | Cantidad | Detalle |
|---|---|---|
| Departamentos | 2 | Bogotá D.C. y Cundinamarca |
| Municipios | 34 | Incluye Bogotá, Soacha, Chía, Cajicá, Zipaquirá, Facatativá |
| Áreas de impacto | 11 | Adulto Mayor, Cultura, Deportes, Derechos Humanos, Discapacidad, Educación, Inclusión Social, Infancia, Medio Ambiente, Salud, Tecnología |
| Habilidades | 108 (19 marcadas como profesionales) | Apoyo social 16, Construcción y mantenimiento 14, Cuidado animal 14, Educación 17, Medio ambiente 15, Salud y bienestar 16, Tecnología y comunicación 16 |
| Intereses | 36 | Sembrados con `scripts/seed_intereses.py` |
| Logros | 11 | Valiente, Primer Paso, Héroe (umbral 1), Siempre Presente (3), Comprometido (5), Voluntario Activo (10), Impacto Social (25), Leyenda Solidaria (50), Acumulador (100), Veterano (500), Élite (1000) |
| Niveles | 8 | Chispa 0, Destello 100, Amanecer 300, Resplandor 600, Aurora 1000, Sol naciente 1800, Sol pleno 3000, Supernova 5000 (XP mínimo). Solo reconocimiento visual |

**Cobertura geográfica.** La base contiene Bogotá D.C. y 33 municipios de Cundinamarca. El documento de grado fija el piloto en **Bogotá**. Decisión del autor: redactar Cundinamarca como "datos geográficos ya cargados para la expansión" o limitar el catálogo; el código soporta ambas opciones.

---

## 7. Cifras de datos sintéticos (entorno de desarrollo)

| Dato | Valor |
|---|---|
| Usuarios | 209 (157 voluntarios, 46 organizaciones, 6 administradores) |
| Convocatorias | 257 (cada una con 3–5 habilidades requeridas) |
| Postulaciones | 3.857 |

Son **datos sintéticos generados para demostración**, no participantes reales. No deben presentarse como resultados del piloto. El piloto del documento (5 organizaciones, 50 voluntarios) aún no se ejecutó con usuarios reales.

---

## 8. Decisiones pendientes del autor (el código no las resuelve)

1. **Menores de edad (14–17 años) y Ley 1581.** El registro hoy valida la fecha de nacimiento y las convocatorias pueden fijar edad mínima y máxima. No hay flujo de autorización de representantes. Decidir: excluir menores del piloto, o diseñar el consentimiento. Mientras tanto, la galería exige marcar si hay menores y si existe autorización de imagen.
2. **Cronograma real** (fechas de las fases).
3. **GUANE** (repositorio institucional): requisitos y formato de entrega.
4. **Código estudiantil** y datos de portada.
5. **Instrumentos del piloto:** encuesta de usabilidad, formato de observación, métricas de éxito.
6. **Plan de pruebas:** el documento puede citar las 66 pruebas automáticas del backend; las pruebas de interfaz y de aceptación con usuarios quedan por hacer.
7. **Cobertura inicial:** solo Bogotá o Bogotá y Cundinamarca (ver sección 6).

---

## 9. Texto sugerido

**4.3 Arquitectura.** "Solari se compone de una aplicación web de una sola página (React, TypeScript y Vite) y una API REST (FastAPI sobre Python) que persiste en PostgreSQL. El backend se organiza por capas: rutas, servicios con las reglas de negocio, repositorios de acceso a datos y modelos relacionales. Las reglas R1 a R13 se aplican en la capa de servicios, de modo que ninguna se puede omitir desde la interfaz. Los cambios de esquema se versionan con Alembic."

**4.10 Seguridad y privacidad.** "Las contraseñas se almacenan con Argon2id; las sesiones usan tokens JWT de corta duración con renovación. Los endpoints limitan la frecuencia de peticiones. Los documentos de identidad y de verificación se guardan en una carpeta no pública y solo los descarga su dueño o un administrador autenticado. Los datos sensibles del voluntario (documento, fecha de nacimiento, dirección, teléfono y contacto de emergencia) no se muestran a las organizaciones al evaluar postulaciones. Las solicitudes de acceso, corrección o eliminación de datos (Ley 1581 de 2012) se gestionan por un flujo con respuesta obligatoria, sin ejecución automática y con registro de auditoría."

**4.11 Pruebas.** "Se desarrollaron 66 pruebas automáticas con pytest: 24 de autenticación, 21 unitarias (coincidencia de habilidades, niveles, recurrencia, moderación, validaciones) y 21 de integración contra PostgreSQL que cubren las reglas R2 a R13 y los flujos de administración. Todas se ejecutaron y aprobaron. El frontend se valida con el compilador de TypeScript y ESLint sin errores. Las pruebas de usabilidad con usuarios reales se realizarán durante el piloto." *(Ajustar la última frase según lo que el autor decida en el punto 5 de la sección 8.)*

**4.12 Limitaciones.** "El prototipo no incluye certificados en PDF, notificaciones por correo electrónico (las notificaciones son internas), mensajería general entre usuarios (solo dentro de una solicitud de objetos o servicios), autorización de representantes para menores de edad ni pruebas automáticas de interfaz. Los datos de demostración son sintéticos."

---

## 10. Limitaciones honestas (resumen)

- Sin pruebas automáticas del frontend; las pantallas nuevas no se recorrieron en navegador.
- TanStack Query instalado pero sin uso.
- El correo solo se usa para verificación de cuenta y recuperación de contraseña; las notificaciones son internas.
- La verificación de organizaciones depende de que un administrador revise los documentos manualmente.
- La vista de ranking limita a 1000 posiciones; el voluntario fuera del top ve su posición real.
- Los datos masivos son sintéticos.
- El servidor de desarrollo escucha en el puerto 8080; puede haber una instancia anterior en ejecución que conviene detener antes de la demostración.
