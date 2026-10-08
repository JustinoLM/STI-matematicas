"""
Script para inicializar la base de datos.

Crea todas las tablas definidas en los modelos SQLAlchemy.
Útil para desarrollo local y testing.
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine, Base
from app.core.config import settings

# Importar todos los modelos para que SQLAlchemy los registre
from app.models import (
    Usuario, Estudiante, Profesor,
    Narrativa,
    Grupo, EstudianteGrupo,
    Problema, ConfiguracionPractica, Intento,
    PerfilEstudiante,
    Medalla, EstudianteMedalla,
    CategoriaDesbloqueable, Desbloqueable, EstudianteDesbloqueable, PersonalizacionEstudiante,
    DesafioGrupal, GrupoDesafio,
    ErrorComun, EstudianteError,
)


async def init_db():
    """Crear todas las tablas en la base de datos."""
    print("=" * 60)
    print("INICIALIZANDO BASE DE DATOS")
    print("=" * 60)
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print()
    
    # Verificar que estamos en desarrollo
    if settings.ENVIRONMENT == "production":
        confirm = input("⚠️  ADVERTENCIA: Estás en PRODUCCIÓN. ¿Continuar? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Operación cancelada.")
            return
    
    print("🔨 Creando tablas...")
    
    async with engine.begin() as conn:
        # Eliminar todas las tablas existentes (cuidado en producción!)
        await conn.run_sync(Base.metadata.drop_all)
        print("  ✓ Tablas existentes eliminadas")
        
        # Crear todas las tablas
        await conn.run_sync(Base.metadata.create_all)
        print("  ✓ Tablas creadas")
    
    print()
    print("=" * 60)
    print("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
    print("=" * 60)
    print()
    print("Próximo paso: Ejecutar seed_data.py para insertar datos iniciales")


if __name__ == "__main__":
    asyncio.run(init_db())
