"""
Router de importación de Excel completo para el panel de administración.

Endpoints:
  POST /admin/import/excel  → importa las 8 hojas del export a una
                               organización sandbox elegida por el admin.
"""

from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import openpyxl

from app.api.dependencies import AdminImportServiceDep
from app.schemas.admin_import import ImportResumen

router = APIRouter()


@router.post("/admin/import/excel", response_model=ImportResumen)
async def importar_excel(
    import_service: AdminImportServiceDep,
    organizacion_nombre: str = Form(..., min_length=3, max_length=255),
    archivo: UploadFile = File(...),
):
    """
    Importa un Excel con el mismo esquema del exportador (Estudiantes,
    Diagnóstico, Sesiones, Niveles Actuales, Medallas, Tienda) hacia la
    organización indicada — se crea si no existe. Nunca toca organizaciones
    ya existentes con otro nombre, así que es seguro reimportar sin afectar
    datos reales.
    """
    if not archivo.filename or not archivo.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo debe ser .xlsx")

    contenido = await archivo.read()
    try:
        wb = openpyxl.load_workbook(BytesIO(contenido), data_only=True)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo leer el archivo — ¿es un .xlsx válido?")

    return await import_service.importar_excel(wb, organizacion_nombre.strip())
