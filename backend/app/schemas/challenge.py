"""
Schemas Pydantic para desafíos desde la perspectiva del estudiante.
"""

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class ContribuidorInfo(BaseModel):
    """Contribuidor del grupo al desafío."""
    nombre: str
    sesiones: int   # Sesiones completadas en la ventana del desafío


class DesafioEstudianteResponse(BaseModel):
    """Desafío grupal visto desde el lado del estudiante.

    Tipos (de más fácil a más difícil):
    - problemas_resueltos   ⭐     → X problemas correctos en grupo
    - sesiones_completadas  ⭐⭐   → X prácticas completadas en grupo
    - practicas_sin_errores ⭐⭐⭐  → X prácticas con ≤ Y errores (parametro_adicional=Y)
    - problemas_rapidos     ⭐⭐⭐⭐ → X problemas respondidos en ≤ Y seg/problema
    - practicas_rapidas     ⭐⭐⭐⭐⭐→ X prácticas completadas en ≤ Y minutos
    """

    id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo: str
    objetivo_cantidad: int
    parametro_adicional: Optional[int] = None   # Parámetro Y según tipo
    recompensa_texto: Optional[str] = None
    recompensa_puntos: Optional[int] = None      # Monedas a ganar al completar
    fecha_creacion: datetime
    fecha_limite: Optional[datetime] = None
    completado: bool

    # Progreso del grupo al que pertenece el estudiante
    grupo_id: int
    grupo_nombre: str
    progreso_actual: int
    porcentaje: float       # 0.0 – 100.0 (ya acotado)
    grupo_completado: bool

    # Calculados en el servidor
    dias_restantes: Optional[int] = None   # None = sin fecha límite
    esta_expirado: bool = False

    # Participación individual del estudiante (para saber si recibirá la recompensa)
    mi_sesiones_en_ventana: int = 0     # Sesiones propias completadas en la ventana
    califica_recompensa: bool = False    # True si supera el umbral mínimo de sesiones
    sesiones_para_calificar: int = 0    # Cuántas sesiones le faltan para calificar

    # Top contribuidores del grupo (por sesiones en la ventana)
    top_contribuidores: List[ContribuidorInfo] = []

    model_config = {"from_attributes": True}
