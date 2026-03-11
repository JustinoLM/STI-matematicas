"""
Endpoints para la colección de animaciones paso a paso del estudiante.

POST /animaciones/guardar  → guarda una animación en la colección (máx 10)
GET  /animaciones/coleccion → lista las animaciones guardadas
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import CurrentStudent, DBSession
from app.repositories.animaciones_repository import AnimacionesRepository, MAX_ANIMACIONES

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GuardarAnimacionRequest(BaseModel):
    problema_id: int
    operacion: str
    numero1: str
    numero2: str
    nivel_dificultad: int


class AnimacionResponse(BaseModel):
    id: int
    problema_id: int
    operacion: str
    numero1: str
    numero2: str
    nivel_dificultad: int
    guardado_en: datetime


class GuardarAnimacionResponse(BaseModel):
    animacion: AnimacionResponse
    guardadas_total: int
    maximo: int
    ya_existia: bool


class ColeccionResponse(BaseModel):
    animaciones: list[AnimacionResponse]
    total: int
    maximo: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/guardar", response_model=GuardarAnimacionResponse, status_code=status.HTTP_200_OK)
async def guardar_animacion(
    body: GuardarAnimacionRequest,
    current_student: CurrentStudent,
    db: DBSession,
) -> GuardarAnimacionResponse:
    """Guarda una animación en la colección del estudiante."""
    repo = AnimacionesRepository(db)

    # Comprobar si ya existía antes de guardar
    existente = await repo.get_por_problema(current_student.id, body.problema_id)
    ya_existia = existente is not None

    animacion, _ = await repo.guardar(
        estudiante_id=current_student.id,
        problema_id=body.problema_id,
        operacion=body.operacion,
        numero1=body.numero1,
        numero2=body.numero2,
        nivel_dificultad=body.nivel_dificultad,
    )
    total = await repo.count(current_student.id)

    return GuardarAnimacionResponse(
        animacion=AnimacionResponse(
            id=animacion.id,
            problema_id=animacion.problema_id,
            operacion=animacion.operacion,
            numero1=animacion.numero1,
            numero2=animacion.numero2,
            nivel_dificultad=animacion.nivel_dificultad,
            guardado_en=animacion.guardado_en,
        ),
        guardadas_total=total,
        maximo=MAX_ANIMACIONES,
        ya_existia=ya_existia,
    )


@router.delete("/{animacion_id}", status_code=status.HTTP_200_OK)
async def eliminar_animacion(
    animacion_id: int,
    current_student: CurrentStudent,
    db: DBSession,
) -> dict:
    """Elimina una animación de la colección del estudiante."""
    repo = AnimacionesRepository(db)
    eliminada = await repo.eliminar(current_student.id, animacion_id)
    if not eliminada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animación no encontrada",
        )
    return {"ok": True}


@router.get("/coleccion", response_model=ColeccionResponse)
async def get_coleccion(
    current_student: CurrentStudent,
    db: DBSession,
) -> ColeccionResponse:
    """Lista las animaciones guardadas del estudiante."""
    repo = AnimacionesRepository(db)
    coleccion = await repo.get_coleccion(current_student.id)

    return ColeccionResponse(
        animaciones=[
            AnimacionResponse(
                id=a.id,
                problema_id=a.problema_id,
                operacion=a.operacion,
                numero1=a.numero1,
                numero2=a.numero2,
                nivel_dificultad=a.nivel_dificultad,
                guardado_en=a.guardado_en,
            )
            for a in coleccion
        ],
        total=len(coleccion),
        maximo=MAX_ANIMACIONES,
    )
