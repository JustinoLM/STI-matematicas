# Backend - STI (Sistema de Tutoría Inteligente)

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1.svg)
![Poetry](https://img.shields.io/badge/poetry-dependency%20management-60A5FA.svg)

API REST construida con FastAPI para el sistema de tutoría adaptativa.

## Arquitectura de 3 Capas
```
Routers (API Layer)  →  Service (Business Logic)  →  Repository (Data Access)  →  Database
```

### Estructura de Carpetas
```
app/
├── api/
│   ├── routers/        # Endpoints HTTP
│   └── dependencies.py # Auth, DB injection
├── core/
│   ├── config.py       # Settings
│   ├── database.py     # SQLAlchemy setup
│   └── security.py     # JWT, password hashing
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic request/response
├── services/           # Business logic
└── repositories/       # Data access layer
```

## Inicio Rápido

### 1. Instalar Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Instalar dependencias
```bash
cd backend
poetry install
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus valores
```

### 4. Iniciar base de datos (Docker)
```bash
# Desde la raíz del proyecto
docker-compose up -d postgres
```

### 5. Ejecutar migraciones
```bash
poetry run alembic upgrade head
```

### 6. Iniciar servidor de desarrollo
```bash
poetry run uvicorn app.main:app --reload
```

La API estará disponible en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Testing
```bash
# Ejecutar todos los tests
poetry run pytest

# Con coverage
poetry run pytest --cov=app --cov-report=html

# Solo un archivo
poetry run pytest tests/test_auth.py
```

## Linting y Formateo
```bash
# Formatear código con Black
poetry run black app/

# Lint con Ruff
poetry run ruff check app/

# Auto-fix
poetry run ruff check app/ --fix
```

## Agregar Dependencias
```bash
# Dependencia de producción
poetry add nombre-paquete

# Dependencia de desarrollo
poetry add --group dev nombre-paquete
```

## Migraciones de Base de Datos
```bash
# Crear nueva migración
poetry run alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
poetry run alembic upgrade head

# Revertir última migración
poetry run alembic downgrade -1
```

## Generar SECRET_KEY
```bash
openssl rand -hex 32
```

## Documentación de la API

La documentación se genera automáticamente con FastAPI:

- **Swagger UI** (interactiva): http://localhost:8000/docs
- **ReDoc** (documentación estática): http://localhost:8000/redoc

## Deployment

### Railway (Producción)

1. Conectar repositorio a Railway
2. Configurar variables de entorno
3. Deploy automático en cada push a `main`

## Licencia

Proyecto académico - Tesis de grado
