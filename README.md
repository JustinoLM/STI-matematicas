# Sistema de Tutoría Inteligente (STI)

Sistema adaptativo para enseñanza de matemáticas de 5to grado con enfoque en operaciones decimales.

## 🏗️ Arquitectura

Este proyecto utiliza una arquitectura **monorepo** con:

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: React + TypeScript + TailwindCSS
- **LLM**: DeepSeek API (remoto) — `deepseek-chat` (V3) para enunciados y mensajes, `deepseek-reasoner` (R1) para análisis post-práctica
- **Deploy**: Railway (backend) + Vercel (frontend)

## 📁 Estructura del Proyecto
```
sti-proyecto/
├── backend/          # API REST con FastAPI
├── frontend/         # Interfaz React
├── docs/             # Documentación técnica
└── docker-compose.yml # PostgreSQL (+ pgAdmin opcional)
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Instalación

Ver instrucciones en:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

## 📚 Documentación

- [Arquitectura del backend](backend/README.md) (capas Router → Service → Repository)
- Documentación de la API: Swagger UI en `http://localhost:8000/docs` con el servidor corriendo

## 📄 Licencia

Proyecto académico - Tesis de grado
