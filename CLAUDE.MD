# CLAUDE.MD - Sistema de Tutoría Inteligente (STI)

## Resumen del Proyecto

Sistema de Tutoría Inteligente (STI) adaptativo para la enseñanza de matemáticas de 5to grado, con enfoque en operaciones con decimales. Este es un proyecto de tesis académica que implementa un sistema de aprendizaje personalizado con gamificación, detección de tramposos, y contenido adaptativo.

**Estado Actual:** En desarrollo activo - Completadas secciones 4.3.4, 4.3.5, 4.4.1 y 4.4.2

## Stack Tecnológico

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy
- **Base de Datos:** PostgreSQL
- **Gestión de Dependencias:** Poetry
- **Migraciones:** Alembic
- **Testing:** pytest
- **Linting/Formato:** Black, Ruff

### Frontend
- **Framework:** React 18+ con TypeScript
- **Estilo:** TailwindCSS
- **Estado:** Zustand (en migración desde Context API)
- **Data Fetching:** React Query (TanStack Query)
- **Build Tool:** Vite
- **Routing:** React Router

### IA/ML
- **LLM:** Ollama + DeepSeek-R1:7B (local)
- **Uso:** Generación de pistas pedagógicas adaptativas

### Deployment
- **Backend:** Railway
- **Frontend:** Vercel
- **BD Desarrollo:** Docker Compose (PostgreSQL + Ollama)

## Arquitectura

### Backend - 3 Capas
```
Routers (API Layer) → Service (Business Logic) → Repository (Data Access) → Database
```

**Estructura:**
```
backend/app/
├── api/
│   ├── routers/          # Endpoints HTTP
│   └── dependencies.py   # Auth, DB injection
├── core/
│   ├── config.py         # Settings
│   ├── database.py       # SQLAlchemy setup
│   └── security.py       # JWT, password hashing
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response
├── services/             # Business logic
└── repositories/         # Data access layer
```

### Frontend - Arquitectura por Capas
```
frontend/src/
├── components/
│   ├── problems/         # Componentes de ejercicios (refactorizado)
│   │   ├── atoms/        # Componentes UI atómicos reutilizables
│   │   ├── SumaRestaGrid.tsx
│   │   ├── MultiplicacionGrid.tsx
│   │   ├── DivisionGrid.tsx
│   │   └── ProblemGrid.tsx  # Orquestador (~60 líneas)
│   └── ui/               # Componentes UI genéricos (shadcn/ui style)
├── hooks/                # Custom React hooks
├── pages/
│   ├── student/          # Dashboard, Profile, Practice, Shop, etc.
│   └── teacher/          # Gestión de grupos, estudiantes
├── services/             # API clients
│   ├── api.ts            # Axios instance
│   ├── authService.ts
│   ├── studentService.ts
│   └── teacherService.ts
├── store/                # Zustand stores
├── types/                # TypeScript types
└── utils/                # Utilidades
```

## Módulos Principales

### 1. Sistema Adaptativo
- **Componente de Práctica:** Generación dinámica de problemas
- **Niveles:** 5 niveles de dificultad por operación (suma, resta, multiplicación, división)
- **Progresión:** Basada en rendimiento (precisión + velocidad)
- **Regla Especial:** Nivel 5 requiere dominio de todas las operaciones en nivel 4

### 2. Gamificación (Sección 4.3.5)
- **Puntos (XP):** Por respuestas correctas
- **Monedas:** Economía virtual para tienda
- **Avatares:** Sistema de desbloqueo por logros
- **Badges:** Insignias por hitos
- **Leaderboard:** Ranking global y por grupo
- **Tienda:** Compra de avatares y cosméticos

### 3. Gestión de Prácticas (Sección 4.3.4)
- **Intentos:** Tracking de cada intento de problema
- **Detección de Tramposos:**
  - Análisis de patrones de tiempo
  - Detección de respuestas instantáneas
  - Flags automáticos para revisión manual
- **Historial:** Seguimiento completo del progreso

### 4. Contenido Adaptativo
- **Pistas:** Generadas por LLM según contexto del error
- **Videos:** Tutoriales vinculados a operaciones
- **Hints Progresivos:** Ayuda incremental sin dar respuesta directa

### 5. Roles de Usuario
- **Estudiantes:** Práctica, perfil, tienda, desafíos
- **Profesores:** Dashboard, gestión de grupos, reportes

## Flujo de Pruebas

**NO usar seed data.** El sistema se prueba desde cero de forma manual:
- Los usuarios, grupos y datos se crean directamente desde la UI o el panel de admin (`/admin`)
- `backend/scripts/seed_data.py` existe pero **no se usa en el flujo actual**
- Las migraciones se siguen aplicando con `alembic upgrade head` cuando hay cambios de esquema

## Comandos Importantes

### Backend
```bash
cd backend
poetry install                           # Instalar deps
poetry run uvicorn app.main:app --reload # Dev server
poetry run pytest                        # Tests
poetry run alembic upgrade head          # Migraciones
poetry run black app/                    # Formatear
poetry run ruff check app/ --fix         # Lint
```

### Frontend
```bash
cd frontend
npm install                              # Instalar deps
npm run dev                              # Dev server (Vite)
npm run build                            # Build producción
npm run preview                          # Preview build
```

### Docker (Base de Datos + Ollama)
```bash
docker-compose up -d postgres            # Solo BD
docker-compose up -d                     # BD + Ollama
docker-compose down                      # Detener todo
```

## Flujo de Verificación de Cambios

**NUNCA** usar herramientas de automatización de Chrome (preview_*, Claude in Chrome) para probar el sistema.

Cuando se completan cambios de código:
1. Informar al usuario qué archivos se modificaron y qué se cambió
2. Indicar claramente que los cambios están listos para probar
3. Esperar a que el usuario pruebe manualmente y dé feedback

El usuario prueba en su propio navegador y reporta los resultados.

## Patrones de Desarrollo

### Backend
1. **Siempre usar 3 capas:** Router → Service → Repository
2. **Schemas Pydantic:** Para validación de entrada/salida
3. **Dependency Injection:** Para DB session y auth
4. **Async/Await:** Para operaciones I/O
5. **Error Handling:** HTTPException con códigos apropiados

### Frontend
1. **Componentes Atómicos:** Reutilizar componentes pequeños
2. **Custom Hooks:** Extraer lógica reutilizable
3. **React Query:** Para data fetching y caching
4. **TypeScript Strict:** Tipar todo explícitamente
5. **Separación de Concerns:** UI, lógica, estado

### Refactorización Reciente
El componente `ProblemGrid.tsx` (originalmente ~550 líneas) fue refactorizado en:
- 3 Custom Hooks (lógica reutilizable)
- 6 Componentes Atómicos (UI)
- 3 Componentes Especializados (por operación)
- 1 Orquestador (~60 líneas)

Ver `frontend/MIGRATION_GUIDE.md` para detalles.

## Estado del Proyecto (Git)

**Branch Actual:** master
**Archivos Modificados:**
- Frontend: migraciones a React Query, Zustand, refactorización de componentes
- Nuevos componentes: ChallengesPage, GroupChallengePage, SettingsPage, VideosPage

**Archivos Sin Track:**
- `.claude/` (configuración de Claude Code)
- `frontend/src/components/problems/` (componentes refactorizados)
- `frontend/src/hooks/` (custom hooks)
- `frontend/src/store/` (Zustand stores)
- Varios componentes de UI (badge, progress, tabs)

**Commits Recientes:**
1. Parte 4.4.1 y 4.4.2 completada
2. Estructura base del Backend completada
3. Sistema de gamificación (4.3.5)
4. Gestión de prácticas con detección de tramposos (4.3.4)
5. Regla especial nivel 5

## Notas para Desarrollo

### Seguridad
- **JWT:** Tokens de autenticación con expiración
- **CORS:** Configurado para frontend específico
- **Password Hashing:** bcrypt
- **Validación:** Pydantic en backend, Zod en frontend

### Performance
- **DB:** Índices en columnas frecuentes (user_id, practice_id, etc.)
- **Frontend:** React.memo, useMemo, useCallback donde corresponde
- **API:** Paginación en endpoints que retornan listas
- **Caché:** React Query con staleTime configurado

### Testing
- **Backend:** pytest con fixtures para DB
- **Frontend:** (Por implementar) Vitest + React Testing Library

### Documentación API
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Consideraciones Pedagógicas

Este es un proyecto **educativo** (tesis), por lo tanto:
1. **Justificación Pedagógica:** Cada decisión debe tener base teórica
2. **Accesibilidad:** Interfaz simple y clara para niños de 10-11 años
3. **Feedback Constructivo:** No punitivo, orientado al aprendizaje
4. **Adaptación Real:** El algoritmo debe ajustarse al nivel real del estudiante
5. **Gamificación Balanceada:** Motivar sin distraer del aprendizaje

## Roadmap Futuro

- [ ] Implementar tests frontend (Vitest)
- [ ] Dashboard del profesor con analytics
- [ ] Reportes de progreso descargables
- [ ] Desafíos entre estudiantes
- [ ] Sistema de narrativa gamificada
- [ ] Integración con LMS (Moodle/Canvas)
- [ ] App móvil (React Native)

## Contacto y Recursos

- **Repositorio:** (Agregar URL si existe)
- **Documentación Técnica:** `docs/`
- **API Docs:** `docs/api/`
- **Arquitectura:** `docs/architecture/`

---

**Última Actualización:** 2026-02-28
**Versión:** Capítulo 4 - Secciones 4.3.4, 4.3.5, 4.4.1, 4.4.2 completadas
