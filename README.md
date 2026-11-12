# Sistema de Tutoría Inteligente (STI) de matemáticas para primaria

Sistema web de tutoría inteligente para que estudiantes panameños de primaria practiquen matemáticas. Hoy cubre las operaciones con números decimales de sexto grado (suma, resta, multiplicación y división) y se está reestructurando para incorporar los temas numéricos del programa de MEDUCA de primero a sexto grado. El sistema adapta cada práctica al desempeño del estudiante y le da al docente un panel para seguir el progreso de sus salones.

La versión 1.0 se desarrolló como trabajo de graduación de la Licenciatura en Ingeniería de Software de la Universidad Tecnológica de Panamá (UTP), Facultad de Ingeniería de Sistemas Computacionales, y se validó con estudiantes reales en una escuela pública panameña.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?logo=vite&logoColor=white)

> **Estado del proyecto.** En desarrollo. La versión 1.0, limitada a las operaciones con decimales de sexto grado y validada con estudiantes, está archivada en la etiqueta `v1.0-tesis`. Ahora el sistema se reestructura para admitir varios temas, empezando por primero y segundo grado; el diseño y sus fases están en [`docs/DISENO_MODULAR.md`](docs/DISENO_MODULAR.md). Ya están terminadas la preparación (pruebas en PostgreSQL e integración continua) , la organización escolar (salones, años lectivos y trimestres) y el currículo como datos (catálogo de lecciones de MEDUCA). No hay una demo en línea.

---

## Contenido

- [Qué hace](#qué-hace)
- [Qué lo hace adaptativo](#qué-lo-hace-adaptativo)
- [Resultados de la validación](#resultados-de-la-validación)
- [Capturas](#capturas)
- [Arquitectura](#arquitectura)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Instalación local](#instalación-local)
- [Pruebas](#pruebas)
- [Despliegue](#despliegue)
- [Privacidad y seguridad](#privacidad-y-seguridad)
- [Trabajo futuro](#trabajo-futuro)
- [Autor](#autor)

---

## Qué hace

### Para el estudiante

- **Prueba diagnóstica inicial** de ocho problemas que asigna un nivel (1 a 5) en cada operación.
- **Prácticas generadas automáticamente**: el estudiante presiona "Practicar" y el sistema decide qué operaciones incluir, en qué proporción y con qué dificultad.
- **Cuadrículas de resolución** que imitan el procedimiento en papel (llevadas, productos parciales, división paso a paso) y un teclado virtual pensado para tabletas.
- **Pistas en tres niveles**: estrategia general, paso a paso y una pista generada por el modelo de lenguaje que orienta hacia el error cometido sin revelar la respuesta.
- **Animaciones paso a paso** que muestran la resolución completa cuando se agotan los tres intentos de un problema.
- **Enunciados narrativos** según el tema elegido (piratas, astronautas, magos, caballeros, vaqueros o inventores), que presentan cada operación dentro de una historia.
- **Gamificación sin rankings**: puntos, una tienda de 62 artículos estéticos (temas, fondos, colores, música y efectos), 25 medallas y desafíos grupales cooperativos.

### Para el docente

- Salones con un año lectivo por año: el docente crea su salón, asigna y quita estudiantes (también desde Excel) y, si quiere, los organiza en grupos dentro del salón.
- Configuración de la práctica por salón: operaciones, niveles, rangos numéricos, decimales y pistas habilitadas.
- Estadísticas del salón y de cada grupo: perfiles de aprendizaje, niveles por operación, actividad y precisión semanal.
- Alertas automáticas: estudiantes rezagados, inactivos, estancados, sobresalientes, con ascensos rápidos o con patrones de respuesta anómalos.
- Un análisis pedagógico del grupo, generado por el modelo de lenguaje bajo demanda.
- Desafíos cooperativos dentro de un salón, entre sus grupos o con el salón completo como un solo equipo, con metas colectivas y recompensas.

### Para el administrador

- Panel protegido para crear escuelas y usuarios, importar y exportar datos y reentrenar los modelos de Machine Learning.
- Salones de cada escuela, calendario de trimestres editable (por defecto, del primer lunes de marzo a mediados de diciembre) y cierre del año lectivo, que deja el año anterior en solo lectura.

---

## Qué lo hace adaptativo

El sistema combina reglas pedagógicas, modelos de Machine Learning y un modelo de lenguaje. Cada uno cumple una función distinta:

| Componente | Técnica | Qué hace |
|---|---|---|
| Diagnóstico y niveles | Reglas | Asigna un nivel por operación, de modo que un estudiante puede estar en nivel 4 en sumas y en nivel 2 en multiplicaciones. |
| Prerrequisitos | Reglas | Habilita la multiplicación y la división solo cuando el estudiante domina las operaciones de las que dependen. |
| Generación de la práctica | Reglas | Concentra la mayor parte de los problemas en la operación más débil y ajusta la proporción entre problemas fáciles y desafiantes según el nivel. |
| Ajuste de nivel | Reglas | Sube de nivel tras una racha de aciertos consecutivos y baja si la precisión de la sesión cae por debajo de 50%. |
| Perfiles de aprendizaje | **K-means** (scikit-learn) | Agrupa a los estudiantes de cada escuela en cuatro perfiles (rápido y preciso, cuidadoso y metódico, impulsivo, en desarrollo) y adapta la racha necesaria para subir de nivel (de 7 a 15 aciertos). |
| Probabilidad de avance | **Regresión logística** (scikit-learn) | Estima la probabilidad de que el estudiante suba de nivel en las próximas tres sesiones y se la muestra al docente. |
| Tipo de error | Reglas | Clasifica cada respuesta incorrecta (desalineación de decimales, punto mal colocado, operación confundida, orden invertido, error de tabla o cálculo general). |
| Contenido generado | **DeepSeek** (API) | Genera enunciados narrativos (con verificación de que contengan exactamente los números del problema), la pista de nivel 3 a partir del tipo de error, mensajes motivacionales y análisis de la práctica y del grupo. |

Los modelos de Machine Learning se reentrenan cada día con los datos acumulados. Mientras no hay datos suficientes, el sistema usa reglas heurísticas de respaldo.

| Modelo de DeepSeek | Uso |
|---|---|
| `deepseek-chat` | Enunciados narrativos, pistas de nivel 3 y mensajes motivacionales |
| `deepseek-reasoner` | Análisis posterior a cada práctica y análisis del grupo |

---

## Resultados de la validación

Corresponden a la versión 1.0, que se validó entre mayo y julio de 2026 con estudiantes de tres secciones de sexto grado de una escuela pública panameña.

| Indicador | Resultado |
|---|---|
| Estudiantes participantes | 74 (65 completaron al menos una práctica) |
| Sesiones de práctica completadas | 710, en dos meses |
| Pre-test → post-test (n = 63, de 0 a 8 aciertos) | 1.83 → 2.56 aciertos en promedio |
| Prueba de Wilcoxon | p = 0.0012; tamaño del efecto mediano (r = 0.41) |
| Usabilidad percibida por los estudiantes (escala SUS, n = 70) | 70.1 de 100 |
| Estudiantes que usaron la tienda (de quienes practicaron) | 92% |

El uso del sistema estuvo asociado a una mejora estadísticamente significativa, de magnitud moderada. Como el estudio no tuvo grupo de control, la mejora no puede atribuirse exclusivamente al sistema.

---

## Capturas

| Inicio del estudiante | Práctica | Panel del docente |
|---|---|---|
| ![Inicio del estudiante](docs/capturas/inicio-estudiante.png) | ![Práctica](docs/capturas/practica.png) | ![Panel del docente](docs/capturas/panel-docente.png) |

---

## Arquitectura

```
React + TypeScript  ──HTTPS / JSON──▶  FastAPI  ──▶  PostgreSQL
                                                     │
                                                     └──▶  API de DeepSeek
```

El backend sigue una arquitectura en tres capas: **Router → Service → Repository**.

| Capa | Tecnologías |
|---|---|
| Frontend | React 18, TypeScript 5, Vite 5, Tailwind CSS, shadcn/ui, React Router 6, Zustand, TanStack Query, Axios, Chart.js |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (asíncrono, asyncpg), Alembic, Pydantic, APScheduler |
| Machine Learning | scikit-learn (K-means, regresión logística), NumPy |
| Seguridad | JWT (python-jose, HS256), Argon2 (passlib) |
| Base de datos | PostgreSQL 14 o superior (la integración continua usa la 15) |
| Modelo de lenguaje | API de DeepSeek |
| Despliegue | Durante la validación de la versión 1.0: Railway (backend y base de datos) y Vercel (frontend); hoy no hay un despliegue activo |

---

## Estructura del repositorio

```
STI-matematicas/
├── .github/workflows/      # Integración continua (pruebas en cada push y pull request)
├── backend/
│   ├── app/
│   │   ├── api/            # Routers y dependencias de FastAPI
│   │   ├── core/           # Configuración, base de datos, seguridad y registros
│   │   ├── models/         # Modelos ORM de SQLAlchemy
│   │   ├── repositories/   # Acceso a datos
│   │   ├── schemas/        # Esquemas Pydantic
│   │   └── services/       # Lógica de negocio, ML y modelo de lenguaje
│   ├── alembic/            # Migraciones
│   ├── scripts/            # Carga inicial, evaluación de K y utilidades
│   └── tests/              # Pruebas con pytest
├── frontend/
│   └── src/
│       ├── components/     # Componentes (ui, layout, problems, practice, routing)
│       ├── pages/          # Vistas del estudiante, el docente y el administrador
│       ├── services/       # Cliente HTTP y servicios por dominio
│       ├── store/          # Estado global con Zustand
│       └── __tests__/      # Pruebas con Vitest
├── docs/                   # Diseño del STI modular y capturas
├── docker-compose.yml      # PostgreSQL y pgAdmin en Docker (opcional)
└── deploy.sh               # Despliegue manual de la versión 1.0
```

Cada carpeta principal tiene su propio README con más detalle.

---

## Instalación local

### Requisitos

- Python 3.11 y [Poetry](https://python-poetry.org/)
- Node.js 18 o superior y npm
- PostgreSQL 14 o superior, instalado en el sistema (por ejemplo con Homebrew) o en Docker
- Una clave de API de [DeepSeek](https://platform.deepseek.com/) (opcional: sin ella, el sistema usa textos de respaldo)

### 1. Base de datos

Hacen falta dos bases: una de desarrollo (por ejemplo `sti_db`) y otra para las pruebas, cuyo nombre debe contener "test" (por defecto `sti_test`).

Con PostgreSQL instalado en el sistema:

```bash
createdb sti_db
createdb sti_test
```

O con Docker:

```bash
cp .env.example .env          # define POSTGRES_PASSWORD y PGADMIN_PASSWORD
docker compose up -d
```

Las dos opciones usan el puerto 5432, así que no se pueden tener encendidas a la vez.

### 2. Backend

```bash
cd backend
cp .env.example .env          # completa DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD y DEEPSEEK_API_KEY
poetry install
poetry run alembic upgrade head
poetry run python scripts/seed_data.py
poetry run python scripts/cargar_curriculo.py   # catálogo de lecciones desde backend/curriculo/
poetry run uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`, y su documentación interactiva, en `http://localhost:8000/docs` (solo en desarrollo). Para generar `SECRET_KEY` y `ADMIN_PASSWORD`, `.env.example` incluye los comandos recomendados.

### 3. Frontend

```bash
cd frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000/api
npm install
npm run dev
```

La aplicación queda en `http://localhost:5173`.

### 4. Primeros usuarios

No hay registro público: el administrador crea las escuelas, los docentes y los estudiantes desde `http://localhost:5173/admin`, con la contraseña definida en `ADMIN_PASSWORD`. Los estudiantes inician sesión con un código y una contraseña asignados.

---

## Pruebas

```bash
cd backend && ./test.sh       # ruff + pytest con cobertura
cd frontend && ./test.sh      # ESLint + Vitest + compilación
```

Las pruebas del backend corren solo contra PostgreSQL. Usan la base de `TEST_DATABASE_URL` o, si no está definida, `postgresql+asyncpg://localhost:5432/sti_test`. Por seguridad, el nombre de la base debe contener "test", porque se vacía en cada prueba.

| Componente | Pruebas | Cobertura |
|---|---|---|
| Backend (pytest, PostgreSQL) | 259 | 61% de líneas (medida con 223) |
| Frontend (Vitest) | 65 | 9.7% de sentencias |

Las pruebas del backend cubren la autenticación y el control de acceso, la organización escolar (salones, matrículas, años lectivos, trimestres y cierre del año), la validación de respuestas, la generación de problemas, las reglas adaptativas, los modelos de ML, la detección de errores, las pistas, las medallas y la integración con el modelo de lenguaje. Las del frontend se concentran en la validación de respuestas, la generación de animaciones y la protección de rutas.

El workflow [`.github/workflows/pruebas.yml`](.github/workflows/pruebas.yml) corre las pruebas del backend (con un servicio de PostgreSQL 15) y las del frontend en cada push y pull request a `master`.

---

## Despliegue

Durante la validación de la versión 1.0 el backend y la base de datos estuvieron en Railway y el frontend en Vercel. Esa infraestructura se dio de baja al terminar la validación y la integración de Vercel con GitHub está suspendida, así que **un push a `master` no despliega nada**. Los archivos de configuración se conservan como referencia para volver a publicar el sistema, en esas plataformas o en cualquier otra con PostgreSQL:

- **Backend:** `backend/railway.toml` y `backend/nixpacks.toml` (Python 3.11). El comando de arranque aplica las migraciones y levanta Uvicorn: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log`. `GET /health` comprueba la conexión a la base de datos y responde 503 si falla. Variables obligatorias: `DATABASE_URL`, `SECRET_KEY` y `ADMIN_PASSWORD` (ver `backend/.env.example`).
- **Frontend:** se compila con `tsc && vite build` (salida en `dist`) y necesita `VITE_API_BASE_URL` con la URL del backend. `frontend/vercel.json` redirige todas las rutas a `index.html` para el enrutamiento del lado del cliente.
- **CORS:** los orígenes permitidos se toman de `BACKEND_CORS_ORIGINS` (lista JSON).
- `deploy.sh` es el script de despliegue manual de la validación: ejecuta las pruebas y publica con las herramientas de Railway y Vercel (`railway up` y `vercel --prod`), por lo que solo sirve si se vuelven a configurar esas cuentas.

En producción, `ENVIRONMENT=production` oculta la documentación de la API (`/docs`, `/redoc` y `/openapi.json`).

---

## Privacidad y seguridad

Este sistema se usó con menores de edad, por lo que:

- **El repositorio no contiene datos de estudiantes.** Los datos de la validación no se publican.
- Las contraseñas se almacenan solo como hash Argon2.
- Las funciones de administración exigen un token de administrador verificado en el servidor.
- Los *prompts* enviados a DeepSeek no incluyen nombres de estudiantes: se usan marcadores y etiquetas anónimas que se sustituyen en el servidor.
- Cada docente solo accede a sus salones, a sus grupos y a los estudiantes de su escuela.

Si encuentras un problema de seguridad, repórtalo de forma privada al autor en lugar de abrir un issue público.

---

## Trabajo futuro

La reestructuración modular está en curso; su diseño y sus fases están en [`docs/DISENO_MODULAR.md`](docs/DISENO_MODULAR.md).

- [x] Fase 0: pruebas en PostgreSQL e integración continua.
- [x] Fase 1: organización escolar (salones, años lectivos, matrículas, trimestres y grupos dentro del salón).
- [x] Fase 2: currículo como datos (catálogo de las lecciones de MEDUCA de 1.º a 6.º y grafo de prerrequisitos de 1.º y 2.º).
- [ ] Fases 3 a 8: núcleo de práctica genérico, pantalla para primeros grados, lecciones de primero y segundo grado, nuevo flujo del docente, diagnóstico adaptativo y motivación.
- [ ] Llevar los decimales y el módulo experimental de regla de tres al núcleo genérico.
- [ ] Demo pública con datos ficticios.
- [ ] Pruebas de extremo a extremo de los flujos completos de práctica y del panel docente.
- [ ] Nueva validación con grupo de control y un instrumento de motivación.

---

## Autor

**Justin Gabriel Williams Kennion**, Licenciatura en Ingeniería de Software, Universidad Tecnológica de Panamá.

Trabajo de graduación asesorado por la Dra. Gema Castillo, con la coasesoría del Dr. Ismael Camargo.

## Licencia

Todos los derechos reservados.