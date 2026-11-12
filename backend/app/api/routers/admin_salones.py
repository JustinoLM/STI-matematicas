"""
Organización escolar para el administrador.

Endpoints (prefijo /api, requieren token de administrador):
- GET  /admin/organizations/{org_id}/salones                Salones con su año lectivo más reciente
- GET  /admin/organizations/{org_id}/trimestres/{anio}      Fechas de los 3 trimestres
- PUT  /admin/organizations/{org_id}/trimestres/{anio}      Cambiar las fechas (para toda la organización)
- POST /admin/organizations/{org_id}/anios/{anio}/cerrar    Cerrar el año lectivo de todos los salones

Hoy hay un único administrador global; edita los trimestres de cada organización por separado.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import DBSession, require_admin
from app.models.organization import Organizacion
from app.schemas.school import CierreAnioResult, SalonOrganizacion, TrimestreOut, TrimestresUpdate
from app.services.school_service import SchoolService

router = APIRouter(dependencies=[Depends(require_admin)])


async def _org_o_404(db, org_id: int) -> Organizacion:
    org = await db.get(Organizacion, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    return org


@router.get("/admin/organizations/{org_id}/salones", response_model=List[SalonOrganizacion])
async def salones_organizacion(org_id: int, db: DBSession):
    await _org_o_404(db, org_id)
    return await SchoolService(db).salones_de_organizacion(org_id)


@router.get("/admin/organizations/{org_id}/trimestres/{anio}", response_model=List[TrimestreOut])
async def obtener_trimestres(org_id: int, anio: int, db: DBSession):
    """Trimestres del año; si aún no existen se crean con las fechas por defecto."""
    await _org_o_404(db, org_id)
    trimestres = await SchoolService(db).trimestres(org_id, anio)
    await db.commit()
    return trimestres


@router.put("/admin/organizations/{org_id}/trimestres/{anio}", response_model=List[TrimestreOut])
async def actualizar_trimestres(org_id: int, anio: int, data: TrimestresUpdate, db: DBSession):
    await _org_o_404(db, org_id)
    trimestres = await SchoolService(db).actualizar_trimestres(
        org_id, anio, [(t.fecha_inicio, t.fecha_fin) for t in data.trimestres]
    )
    await db.commit()
    return trimestres


@router.post("/admin/organizations/{org_id}/anios/{anio}/cerrar", response_model=CierreAnioResult)
async def cerrar_anio(org_id: int, anio: int, db: DBSession):
    """
    Cierra el año lectivo de todos los salones de la organización: quedan de solo lectura con
    sus grupos, y los desafíos sin terminar pasan a "no completado" (los puntos ya otorgados se
    conservan). No se borra nada. Para el año siguiente, cada profesor abre su salón de nuevo.
    """
    await _org_o_404(db, org_id)
    resultado = await SchoolService(db).cerrar_anio(org_id, anio)
    await db.commit()
    return CierreAnioResult(anio=anio, **resultado)
