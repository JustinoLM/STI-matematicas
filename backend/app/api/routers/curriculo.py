"""
Catálogo de lecciones (solo lectura).

Endpoints (prefijo /api/curriculo), para profesores y para el administrador:
- GET /caminos                 Caminos (conjunto numérico + habilidad) en orden
- GET /lecciones?grado=N       Lecciones del programa, en su orden, con caminos y prerrequisitos
                               por defecto. Sin grado: todas.

El contenido se carga desde backend/curriculo/programa_meduca.yaml con
scripts/cargar_curriculo.py; aquí no se edita nada.
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.api.dependencies import DBSession, ProfesorOAdmin
from app.schemas.curriculo import CaminoOut, LeccionCatalogoOut
from app.services.curriculo_service import listar_caminos, listar_lecciones

router = APIRouter()


@router.get("/caminos", response_model=list[CaminoOut])
async def caminos(db: DBSession, _: ProfesorOAdmin):
    return await listar_caminos(db)


@router.get("/lecciones", response_model=list[LeccionCatalogoOut])
async def lecciones(
    db: DBSession,
    _: ProfesorOAdmin,
    grado: Optional[int] = Query(None, ge=1, le=6, description="Grado de 1 a 6; sin él, todas"),
):
    return await listar_lecciones(db, grado)
