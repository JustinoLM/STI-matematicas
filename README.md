# Sistema de Tutoría Inteligente (STI)

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18-339933.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)
![React](https://img.shields.io/badge/React-18.2-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1.svg)

Sistema adaptativo para enseñanza de matemáticas de 5to grado con enfoque en operaciones decimales.

## Arquitectura

Este proyecto utiliza una arquitectura **monorepo** con:

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: React + TypeScript + TailwindCSS
- **LLM**: DeepSeek API (remoto) — `deepseek-chat` (V3) para enunciados y mensajes, `deepseek-reasoner` (R1) para análisis post-práctica
- **Deploy**: Railway (backend) + Vercel (frontend)

## Estructura del Proyecto
```
sti-proyecto/
├── backend/          # API REST con FastAPI
├── frontend/         # Interfaz React
├── docs/             # Documentación técnica
└── docker-compose.yml # PostgreSQL (+ pgAdmin opcional)
```

## Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Instalación

Ver instrucciones en:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

## Documentación

- [Arquitectura del backend](backend/README.md) (capas Router → Service → Repository)
- Documentación de la API: Swagger UI en `http://localhost:8000/docs` con el servidor corriendo

## Licencia

Proyecto académico - Tesis de grado
