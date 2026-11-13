"""Esquemas de la API del núcleo de práctica (/api/nucleo)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.nucleo.modos import Modo

# ─── Profesor ────────────────────────────────────────────────────────────────


class HabilitacionIn(BaseModel):
    signo: Modo = Modo.SIEMPRE
    iconos: Modo = Modo.SIEMPRE
    pistas: dict[str, bool] = Field(default_factory=lambda: {"1": True, "2": True, "3": True},
                                    description='Pistas habilitadas por nivel: {"1": true, "2": true, "3": false}')
    prioritaria: bool = False


class HabilitacionOut(BaseModel):
    leccion_id: str
    titulo: str
    grado: int
    habilitada: bool
    signo: Modo
    iconos: Modo
    pistas: dict[str, bool]
    prioritaria: bool
    tiene_generador: bool


class AsignacionIn(BaseModel):
    estudiante_id: int
    leccion_id: str


class AsignacionOut(BaseModel):
    id: int
    anio_lectivo_id: int
    estudiante_id: int
    leccion_id: str
    estado: str
    fecha_asignacion: datetime
    fecha_cierre: Optional[datetime] = None
    leccion_titulo: str = ""
    estudiante_nombre: str = ""

    model_config = {"from_attributes": True}


class LeccionSalonOut(BaseModel):
    """Lección del catálogo con su estado en el año lectivo del salón."""
    id: str
    grado: int
    unidad_numero: int
    unidad_titulo: str
    leccion_numero: int
    leccion_titulo: str
    orden_programa: int
    incluida: bool
    motivo_exclusion: Optional[str] = None
    parcial: bool
    nota_parcial: Optional[str] = None
    presentacion_especial: Optional[str] = None
    cubierta_por: Optional[str] = None
    caminos: list[str]
    prerrequisitos: list[str]              # los que se aplican en este año
    prerrequisitos_programa: list[str]     # los del currículo
    prerrequisitos_editados: bool
    tiene_generador: bool
    habilitada: bool
    signo: Modo
    iconos: Modo
    pistas: dict[str, bool]
    prioritaria: bool


class PrerrequisitosIn(BaseModel):
    prerrequisitos: list[str] = Field(default_factory=list, max_length=20)


class PrerrequisitosOut(BaseModel):
    leccion_id: str
    prerrequisitos: list[str]
    editados: bool


class AjustesIn(BaseModel):
    banco_forzado: bool


class AjustesOut(BaseModel):
    estudiante_id: int
    banco_forzado: bool

    model_config = {"from_attributes": True}


# ─── Estudiante ──────────────────────────────────────────────────────────────


class SesionOut(BaseModel):
    sesion_id: int
    estado: str
    cantidad_problemas: int
    progreso: int
    fecha_inicio: Optional[datetime] = None


class SesionActivaOut(SesionOut):
    minutos_transcurridos: int


class EstadoNucleoOut(BaseModel):
    disponible: bool = Field(description="Tiene lecciones del núcleo para practicar o una sesión a medias")
    sesion_activa: Optional[SesionActivaOut] = None


class ProblemaOut(BaseModel):
    sesion_completada: bool
    problema_sesion_id: Optional[int] = None
    orden: Optional[int] = None
    problema: Optional[dict[str, Any]] = Field(None, description="Vista pública: sin respuestas")
    intentos_restantes: Optional[int] = None
    pistas_habilitadas: Optional[dict[str, bool]] = None


class EventoIn(BaseModel):
    tipo: str = Field(pattern=r"^[a-z_]{1,40}$",
                      description="opcion_elegida, cambio_opcion, voz, ... (texto libre en minúsculas)")
    valor: Any = None
    ms: Optional[int] = Field(None, ge=0, description="ms desde que se mostró el problema")


class RespuestaIn(BaseModel):
    respuestas: dict[str, Any] = Field(description='{hueco_id: respuesta}; en ordenar, {"orden": [...]}')
    tiempo_ms: int = Field(ge=0)
    uso_voz: bool = False
    eventos: list[EventoIn] = Field(default_factory=list, max_length=500)


class RespuestaOut(BaseModel):
    correcto: bool
    huecos: dict[str, bool]
    intentos_restantes: int
    problema_terminado: bool
    solucion: Optional[dict[str, Any]] = None
    experiencia_ganada: int
    evento_dominio: Optional[str] = None
    sesion_completada: bool


class PistaIn(BaseModel):
    nivel: int = Field(ge=1, le=3)


class PistaOut(BaseModel):
    nivel: int
    texto: str
    puntos_gastados: int


class DominioLeccionOut(BaseModel):
    leccion_id: str
    titulo: str
    grado: int
    estado: str
    aciertos_recientes: int
    problemas_recientes: int
    fecha_dominio: Optional[datetime] = None
    ultima_practica: Optional[datetime] = None
    repaso_pendiente: bool
    habilitada: bool
    prioritaria: bool
    asignada: bool
    tiene_generador: bool


class DominioOut(BaseModel):
    estudiante_id: int
    ventana_dominio: int
    umbral_dominio: float
    experiencia_total: int
    lecciones: list[DominioLeccionOut]
