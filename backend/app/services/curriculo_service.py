"""
Currículo como datos: lectura, validación y carga del catálogo de lecciones.

La fuente de verdad es backend/curriculo/programa_meduca.yaml (docs/DISENO_MODULAR.md,
sección 1 → Contenido). Este módulo:

1. Lee el archivo y comprueba su estructura (claves y tipos) con Pydantic.
2. Valida las reglas del catálogo y junta todos los errores antes de escribir nada:
   - ids de caminos y de lecciones únicos; numeración (grado, unidad, lección) única;
   - cada camino citado existe; una lección incluida tiene al menos un camino;
   - una lección no incluida tiene motivo; una lección parcial tiene nota;
   - presentación especial y "cubierta por" con valores admitidos;
   - cada prerrequisito existe, está incluido y no es de un grado mayor que la lección;
   - una lección no incluida no tiene prerrequisitos; no hay prerrequisitos repetidos;
   - el grafo no tiene ciclos (tampoco una lección que se exige a sí misma).
3. Carga en la base de forma idempotente: inserta o actualiza caminos y lecciones por id y
   sincroniza los caminos de cada lección y los prerrequisitos por defecto. Si una lección de la
   base ya no está en el archivo, se detiene: las lecciones no se borran.

No hace commit: lo decide quien llama (el script de carga o las pruebas).
"""

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculo import (
    CUBIERTA_POR,
    PRESENTACIONES_ESPECIALES,
    CaminoCurricular,
    LeccionCamino,
    LeccionCurricular,
    PrerrequisitoDefecto,
)

RUTA_PROGRAMA = Path(__file__).resolve().parents[2] / "curriculo" / "programa_meduca.yaml"


class ErrorCurriculo(Exception):
    """El archivo del currículo no es válido o no se puede cargar. Lleva la lista de errores."""

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("\n".join(errores))


# ─── Estructura del archivo ──────────────────────────────────────────────────

class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaminoArchivo(_Estricto):
    id: str = Field(min_length=1, max_length=60)
    conjunto: str = Field(min_length=1, max_length=30)
    habilidad: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=120)


class LeccionArchivo(_Estricto):
    id: str = Field(min_length=1, max_length=30)
    numero: int = Field(ge=1)
    titulo: str = Field(min_length=1, max_length=200)
    incluida: bool = True
    motivo: Optional[str] = None
    caminos: list[str] = []
    prerrequisitos: Optional[list[str]] = None   # None: grafo pendiente (3.º a 6.º)
    parcial: bool = False
    nota_parcial: Optional[str] = None
    presentacion: Optional[str] = None
    cubierta_por: Optional[str] = None
    notas: Optional[str] = None


class UnidadArchivo(_Estricto):
    numero: int = Field(ge=1)
    titulo: str = Field(min_length=1, max_length=200)
    lecciones: list[LeccionArchivo]


class GradoArchivo(_Estricto):
    grado: int = Field(ge=1, le=6)
    unidades: list[UnidadArchivo]


class ProgramaArchivo(_Estricto):
    version: int
    caminos: list[CaminoArchivo]
    grados: list[GradoArchivo]


# ─── Programa ya aplanado ────────────────────────────────────────────────────

@dataclass
class Leccion:
    id: str
    grado: int
    unidad_numero: int
    unidad_titulo: str
    leccion_numero: int
    leccion_titulo: str
    orden_programa: int
    incluida: bool
    motivo_exclusion: Optional[str]
    caminos: list[str]
    prerrequisitos: Optional[list[str]]
    parcial: bool
    nota_parcial: Optional[str]
    presentacion_especial: Optional[str]
    cubierta_por: Optional[str]
    notas: Optional[str]


@dataclass
class Programa:
    version: int
    caminos: list[CaminoArchivo]
    lecciones: list[Leccion]

    def leccion(self, leccion_id: str) -> Leccion:
        return next(lec for lec in self.lecciones if lec.id == leccion_id)


def programa_desde_dict(datos: Any) -> Programa:
    """Convierte el contenido del archivo en un Programa. Errores de estructura → ErrorCurriculo."""
    try:
        archivo = ProgramaArchivo.model_validate(datos)
    except ValidationError as e:
        raise ErrorCurriculo([
            f"Estructura: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
        ]) from None

    lecciones: list[Leccion] = []
    for g in archivo.grados:
        for u in g.unidades:
            for lec in u.lecciones:
                lecciones.append(Leccion(
                    id=lec.id,
                    grado=g.grado,
                    unidad_numero=u.numero,
                    unidad_titulo=u.titulo,
                    leccion_numero=lec.numero,
                    leccion_titulo=lec.titulo,
                    orden_programa=len(lecciones) + 1,
                    incluida=lec.incluida,
                    motivo_exclusion=lec.motivo,
                    caminos=list(lec.caminos),
                    prerrequisitos=None if lec.prerrequisitos is None else list(lec.prerrequisitos),
                    parcial=lec.parcial,
                    nota_parcial=lec.nota_parcial,
                    presentacion_especial=lec.presentacion,
                    cubierta_por=lec.cubierta_por,
                    notas=lec.notas,
                ))
    return Programa(version=archivo.version, caminos=archivo.caminos, lecciones=lecciones)


def leer_programa(ruta: Path = RUTA_PROGRAMA) -> Programa:
    try:
        datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ErrorCurriculo([f"YAML inválido: {e}"]) from None
    return programa_desde_dict(datos)


# ─── Validación ──────────────────────────────────────────────────────────────

def _repetidos(valores: list) -> list:
    vistos, repetidos = set(), []
    for v in valores:
        if v in vistos and v not in repetidos:
            repetidos.append(v)
        vistos.add(v)
    return repetidos


def buscar_ciclo(grafo: dict[str, list[str]]) -> Optional[list[str]]:
    """Devuelve un ciclo como lista [a, b, ..., a] si existe; None si el grafo es acíclico."""
    BLANCO, GRIS, NEGRO = 0, 1, 2
    color = {nodo: BLANCO for nodo in grafo}
    pila_camino: list[str] = []

    def visitar(nodo: str) -> Optional[list[str]]:
        color[nodo] = GRIS
        pila_camino.append(nodo)
        for sig in grafo.get(nodo, []):
            if color.get(sig, NEGRO) == GRIS:
                return pila_camino[pila_camino.index(sig):] + [sig]
            if color.get(sig) == BLANCO:
                ciclo = visitar(sig)
                if ciclo:
                    return ciclo
        pila_camino.pop()
        color[nodo] = NEGRO
        return None

    for nodo in grafo:
        if color[nodo] == BLANCO:
            ciclo = visitar(nodo)
            if ciclo:
                return ciclo
    return None


def validar_programa(programa: Programa) -> list[str]:
    """Todas las reglas del catálogo. Devuelve la lista de errores (vacía si es válido)."""
    errores: list[str] = []

    ids_caminos = [c.id for c in programa.caminos]
    for rep in _repetidos(ids_caminos):
        errores.append(f"Camino repetido: {rep}")
    for rep in _repetidos([(c.conjunto, c.habilidad) for c in programa.caminos]):
        errores.append(f"Conjunto y habilidad repetidos en dos caminos: {rep[0]}.{rep[1]}")
    caminos = set(ids_caminos)

    ids = [lec.id for lec in programa.lecciones]
    for rep in _repetidos(ids):
        errores.append(f"Id de lección repetido: {rep}")
    for rep in _repetidos([(lec.grado, lec.unidad_numero, lec.leccion_numero) for lec in programa.lecciones]):
        errores.append(f"Numeración repetida: grado {rep[0]}, unidad {rep[1]}, lección {rep[2]}")

    por_id = {lec.id: lec for lec in programa.lecciones}
    for lec in programa.lecciones:
        if lec.incluida:
            if not lec.caminos:
                errores.append(f"{lec.id}: está incluida pero no tiene camino")
        else:
            if not (lec.motivo_exclusion or "").strip():
                errores.append(f"{lec.id}: no está incluida y no tiene motivo")
            if lec.prerrequisitos:
                errores.append(f"{lec.id}: no está incluida y tiene prerrequisitos")
        for cam in lec.caminos:
            if cam not in caminos:
                errores.append(f"{lec.id}: el camino {cam} no existe")
        for rep in _repetidos(lec.caminos):
            errores.append(f"{lec.id}: camino repetido {rep}")
        if lec.parcial and not (lec.nota_parcial or "").strip():
            errores.append(f"{lec.id}: es parcial y no tiene nota_parcial")
        if not lec.parcial and lec.nota_parcial:
            errores.append(f"{lec.id}: tiene nota_parcial pero no está marcada como parcial")
        if lec.presentacion_especial and lec.presentacion_especial not in PRESENTACIONES_ESPECIALES:
            errores.append(
                f"{lec.id}: presentación '{lec.presentacion_especial}' no admitida "
                f"({', '.join(PRESENTACIONES_ESPECIALES)})"
            )
        if lec.cubierta_por and lec.cubierta_por not in CUBIERTA_POR:
            errores.append(
                f"{lec.id}: cubierta_por '{lec.cubierta_por}' no admitido ({', '.join(CUBIERTA_POR)})"
            )

        for rep in _repetidos(lec.prerrequisitos or []):
            errores.append(f"{lec.id}: prerrequisito repetido {rep}")
        for pre_id in lec.prerrequisitos or []:
            pre = por_id.get(pre_id)
            if pre is None:
                errores.append(f"{lec.id}: el prerrequisito {pre_id} no existe")
                continue
            if not pre.incluida:
                errores.append(f"{lec.id}: el prerrequisito {pre_id} no está incluido en el STI")
            if pre.grado > lec.grado:
                errores.append(
                    f"{lec.id} ({lec.grado}.º): el prerrequisito {pre_id} es de un grado mayor ({pre.grado}.º)"
                )

    grafo = {
        lec.id: [p for p in (lec.prerrequisitos or []) if p in por_id]
        for lec in programa.lecciones
    }
    ciclo = buscar_ciclo(grafo)
    if ciclo:
        errores.append(f"Ciclo de prerrequisitos: {' → '.join(ciclo)}")

    return errores


# ─── Carga en la base ────────────────────────────────────────────────────────

@dataclass
class ResumenCarga:
    caminos_creados: int = 0
    caminos_actualizados: int = 0
    caminos_eliminados: int = 0
    lecciones_creadas: int = 0
    lecciones_actualizadas: int = 0
    enlaces_camino_agregados: int = 0
    enlaces_camino_quitados: int = 0
    prerrequisitos_agregados: int = 0
    prerrequisitos_quitados: int = 0
    lecciones_total: int = 0
    lecciones_incluidas: int = 0
    detalle: list[str] = field(default_factory=list)

    @property
    def hubo_cambios(self) -> bool:
        return any(
            getattr(self, f.name) for f in fields(self)
            if f.name not in ("lecciones_total", "lecciones_incluidas", "detalle")
        )


_CAMPOS_LECCION = (
    "grado", "unidad_numero", "unidad_titulo", "leccion_numero", "leccion_titulo",
    "orden_programa", "incluida", "motivo_exclusion", "parcial", "nota_parcial",
    "presentacion_especial", "cubierta_por", "notas",
)


def _asignar(obj, valores: dict) -> bool:
    cambio = False
    for campo, valor in valores.items():
        if getattr(obj, campo) != valor:
            setattr(obj, campo, valor)
            cambio = True
    return cambio


async def cargar_programa(db: AsyncSession, programa: Programa) -> ResumenCarga:
    """Valida y carga el programa. Idempotente. No hace commit."""
    errores = validar_programa(programa)
    if errores:
        raise ErrorCurriculo(errores)

    resumen = ResumenCarga(
        lecciones_total=len(programa.lecciones),
        lecciones_incluidas=sum(1 for lec in programa.lecciones if lec.incluida),
    )

    lecciones_bd = {lec.id: lec for lec in (await db.execute(select(LeccionCurricular))).scalars()}
    ids_archivo = {lec.id for lec in programa.lecciones}
    retiradas = sorted(set(lecciones_bd) - ids_archivo)
    if retiradas:
        raise ErrorCurriculo([
            f"La lección {i} está en la base pero ya no en el archivo. Las lecciones no se borran: "
            "vuelve a ponerla en el archivo (puede quedar como no incluida, con su motivo)."
            for i in retiradas
        ])

    # Caminos
    caminos_bd = {c.id: c for c in (await db.execute(select(CaminoCurricular))).scalars()}
    for orden, cam in enumerate(programa.caminos, start=1):
        valores = {"conjunto": cam.conjunto, "habilidad": cam.habilidad, "nombre": cam.nombre, "orden": orden}
        existente = caminos_bd.get(cam.id)
        if existente is None:
            db.add(CaminoCurricular(id=cam.id, **valores))
            resumen.caminos_creados += 1
        elif _asignar(existente, valores):
            resumen.caminos_actualizados += 1
            resumen.detalle.append(f"Camino actualizado: {cam.id}")
    await db.flush()

    # Lecciones
    for lec in programa.lecciones:
        valores = {campo: getattr(lec, campo) for campo in _CAMPOS_LECCION}
        existente = lecciones_bd.get(lec.id)
        if existente is None:
            db.add(LeccionCurricular(id=lec.id, **valores))
            resumen.lecciones_creadas += 1
        elif _asignar(existente, valores):
            resumen.lecciones_actualizadas += 1
            resumen.detalle.append(f"Lección actualizada: {lec.id}")
    await db.flush()

    # Caminos de cada lección
    enlaces_bd = {
        (e.leccion_id, e.camino_id)
        for e in (await db.execute(select(LeccionCamino))).scalars()
    }
    enlaces = {(lec.id, cam) for lec in programa.lecciones for cam in lec.caminos}
    for leccion_id, camino_id in sorted(enlaces_bd - enlaces):
        await db.execute(delete(LeccionCamino).where(
            LeccionCamino.leccion_id == leccion_id, LeccionCamino.camino_id == camino_id
        ))
        resumen.enlaces_camino_quitados += 1
    for leccion_id, camino_id in sorted(enlaces - enlaces_bd):
        db.add(LeccionCamino(leccion_id=leccion_id, camino_id=camino_id))
        resumen.enlaces_camino_agregados += 1

    # Prerrequisitos por defecto
    prerreq_bd = {
        (p.leccion_id, p.prerrequisito_id)
        for p in (await db.execute(select(PrerrequisitoDefecto))).scalars()
    }
    prerreq = {(lec.id, pre) for lec in programa.lecciones for pre in (lec.prerrequisitos or [])}
    for leccion_id, pre_id in sorted(prerreq_bd - prerreq):
        await db.execute(delete(PrerrequisitoDefecto).where(
            PrerrequisitoDefecto.leccion_id == leccion_id,
            PrerrequisitoDefecto.prerrequisito_id == pre_id,
        ))
        resumen.prerrequisitos_quitados += 1
    for leccion_id, pre_id in sorted(prerreq - prerreq_bd):
        db.add(PrerrequisitoDefecto(leccion_id=leccion_id, prerrequisito_id=pre_id))
        resumen.prerrequisitos_agregados += 1
    await db.flush()

    # Caminos que ya no están en el archivo (sin lecciones, porque los enlaces ya se sincronizaron)
    for camino_id in sorted(set(caminos_bd) - {c.id for c in programa.caminos}):
        await db.execute(delete(CaminoCurricular).where(CaminoCurricular.id == camino_id))
        resumen.caminos_eliminados += 1
    await db.flush()

    return resumen


# ─── Consultas (endpoint de solo lectura) ────────────────────────────────────

async def listar_caminos(db: AsyncSession) -> list[CaminoCurricular]:
    return list((await db.execute(select(CaminoCurricular).order_by(CaminoCurricular.orden))).scalars())


async def listar_lecciones(db: AsyncSession, grado: Optional[int] = None) -> list[dict]:
    """Lecciones en el orden del programa, con sus caminos y prerrequisitos por defecto."""
    consulta = select(LeccionCurricular).order_by(LeccionCurricular.orden_programa)
    if grado is not None:
        consulta = consulta.where(LeccionCurricular.grado == grado)
    lecciones = list((await db.execute(consulta)).scalars())
    ids = [lec.id for lec in lecciones]

    caminos: dict[str, list[str]] = {i: [] for i in ids}
    filas = await db.execute(
        select(LeccionCamino.leccion_id, LeccionCamino.camino_id)
        .join(CaminoCurricular, CaminoCurricular.id == LeccionCamino.camino_id)
        .where(LeccionCamino.leccion_id.in_(ids))
        .order_by(CaminoCurricular.orden)
    )
    for leccion_id, camino_id in filas:
        caminos[leccion_id].append(camino_id)

    prerrequisitos: dict[str, list[str]] = {i: [] for i in ids}
    pre = LeccionCurricular.__table__.alias("pre")
    filas = await db.execute(
        select(PrerrequisitoDefecto.leccion_id, PrerrequisitoDefecto.prerrequisito_id)
        .join(pre, pre.c.id == PrerrequisitoDefecto.prerrequisito_id)
        .where(PrerrequisitoDefecto.leccion_id.in_(ids))
        .order_by(pre.c.orden_programa)
    )
    for leccion_id, pre_id in filas:
        prerrequisitos[leccion_id].append(pre_id)

    return [
        {
            "id": lec.id,
            **{campo: getattr(lec, campo) for campo in _CAMPOS_LECCION},
            "caminos": caminos[lec.id],
            "prerrequisitos": prerrequisitos[lec.id],
        }
        for lec in lecciones
    ]
