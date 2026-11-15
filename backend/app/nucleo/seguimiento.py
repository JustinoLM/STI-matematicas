"""
Seguimiento del profesor (fase 6b): tabla de dominio del salón, alertas por lección y plan por
trimestre. Todo es puro: recibe una "foto del salón" ya cargada (servicios/seguimiento.py la arma
con pocas consultas fijas) y devuelve diccionarios listos para la API.

- El dominio del salón se calcula a partir del de cada estudiante; no se guarda aparte.
- Estados visibles: dominado, en repaso (dominada con repaso pendiente), en progreso, no iniciado.
- Las alertas comparan con el salón solo para avisar al profesor; el reparto nunca las lee.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Iterable, Mapping, Optional, Sequence

from app.models.nucleo import (
    ALERTA_DIFICULTAD,
    ALERTA_EXCELENCIA,
    DOMINIO_DOMINADO,
    DOMINIO_PROVISIONAL,
    NO_INICIADO,
)
from app.nucleo import dominio as reglas
from app.nucleo.dominio import EstadoDominio, Resultado
from app.nucleo.parametros import ParametrosNucleo

DOMINADO = "dominado"
REPASO = "repaso"
EN_PROGRESO = "en_progreso"
SIN_EMPEZAR = "no_iniciado"
ESTADOS_VISIBLES = (DOMINADO, REPASO, EN_PROGRESO, SIN_EMPEZAR)

MOTIVO_REFUERZO = "refuerzo_insuficiente"   # ya tuvo refuerzo del prerrequisito y sigue por debajo
MOTIVO_SIN_REFUERZO = "sin_refuerzo"        # no hay prerrequisito que se pueda reforzar
MOTIVO_SALON = "detras_del_salon"           # la mayoría del salón ya la domina y él no
MOTIVO_EXTENSION = "extension"


@dataclass(frozen=True)
class EstudianteFoto:
    id: int
    nombre: str
    codigo: str


@dataclass(frozen=True)
class LeccionFoto:
    id: str
    titulo: str
    grado: int
    unidad_numero: int
    unidad_titulo: str
    leccion_numero: int
    orden: int
    caminos: tuple[str, ...] = ()


@dataclass
class FotoSalon:
    estudiantes: list[EstudianteFoto]
    lecciones: dict[str, LeccionFoto]
    habilitadas: set[str]
    prioritarias: set[str]
    asignadas: dict[int, set[str]]                           # estudiante → lecciones activas
    dominios: dict[tuple[int, str], EstadoDominio]
    resultados: dict[tuple[int, str], list[Resultado]]       # sin extensión, cronológicos
    extension: dict[tuple[int, str], list[Resultado]]        # solo zona de extensión
    refuerzo_reciente: dict[tuple[int, str], int]            # problemas de refuerzo en la ventana
    prerrequisitos: dict[str, tuple[str, ...]]               # grafo del año lectivo
    ocultas: dict[tuple[int, str, str], datetime] = field(default_factory=dict)


def estado_visible(e: Optional[EstadoDominio], ahora: datetime, p: ParametrosNucleo) -> str:
    if e is None or e.estado == NO_INICIADO:
        return SIN_EMPEZAR
    if e.estado in (DOMINIO_DOMINADO, DOMINIO_PROVISIONAL):
        return REPASO if reglas.repaso_pendiente(e, ahora, p) else DOMINADO
    return EN_PROGRESO


def _domina(estado: str) -> bool:
    return estado in (DOMINADO, REPASO)


def _redondear(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 3)


# ─── Tabla del salón ─────────────────────────────────────────────────────────

def lecciones_de_la_tabla(foto: FotoSalon) -> list[str]:
    """Habilitadas para el salón y, al final, las asignadas solo a algunos estudiantes."""
    asignadas = set().union(*foto.asignadas.values()) if foto.asignadas else set()
    ids = [i for i in foto.habilitadas | asignadas if i in foto.lecciones]
    return sorted(ids, key=lambda i: (i not in foto.habilitadas, foto.lecciones[i].orden))


def tabla_por_leccion(foto: FotoSalon, ahora: datetime, p: ParametrosNucleo) -> list[dict]:
    filas = []
    for lec_id in lecciones_de_la_tabla(foto):
        lec = foto.lecciones[lec_id]
        habilitada = lec_id in foto.habilitadas
        participantes = [e for e in foto.estudiantes
                         if habilitada or lec_id in foto.asignadas.get(e.id, set())]
        por_estado: dict[str, list[int]] = {s: [] for s in ESTADOS_VISIBLES}
        for e in participantes:
            por_estado[estado_visible(foto.dominios.get((e.id, lec_id)), ahora, p)].append(e.id)
        total = len(participantes)
        dominan = len(por_estado[DOMINADO]) + len(por_estado[REPASO])
        filas.append({
            "leccion_id": lec_id, "titulo": lec.titulo, "grado": lec.grado,
            "unidad_numero": lec.unidad_numero, "unidad_titulo": lec.unidad_titulo,
            "leccion_numero": lec.leccion_numero, "caminos": list(lec.caminos),
            "habilitada": habilitada, "prioritaria": lec_id in foto.prioritarias,
            "total": total, "dominan": dominan,
            "porcentaje_dominan": _redondear(dominan / total) if total else None,
            "conteos": {s: len(v) for s, v in por_estado.items()},
            "estudiantes": por_estado,
        })
    return filas


def proporcion_dominan(foto: FotoSalon, lec_id: str, ahora: datetime, p: ParametrosNucleo) -> tuple[int, int]:
    estados = [estado_visible(foto.dominios.get((e.id, lec_id)), ahora, p) for e in foto.estudiantes]
    return sum(_domina(s) for s in estados), len(estados)


def tabla_por_estudiante(foto: FotoSalon, alertas: Sequence[dict], ahora: datetime, p: ParametrosNucleo) -> list[dict]:
    dificultad = Counter(a["estudiante_id"] for a in alertas if a["tipo"] == ALERTA_DIFICULTAD)
    excelencia = Counter(a["estudiante_id"] for a in alertas if a["tipo"] == ALERTA_EXCELENCIA)
    filas = []
    for e in foto.estudiantes:
        lecciones = sorted(foto.habilitadas | foto.asignadas.get(e.id, set()))
        conteos = Counter(estado_visible(foto.dominios.get((e.id, lec)), ahora, p) for lec in lecciones)
        filas.append({
            "estudiante_id": e.id, "nombre": e.nombre, "codigo": e.codigo, "total": len(lecciones),
            "conteos": {s: conteos.get(s, 0) for s in ESTADOS_VISIBLES},
            "alertas_dificultad": dificultad.get(e.id, 0), "alertas_excelencia": excelencia.get(e.id, 0),
        })
    # Primero quien necesita atención: más alertas de dificultad, menos dominadas
    filas.sort(key=lambda f: (-f["alertas_dificultad"],
                              (f["conteos"][DOMINADO] + f["conteos"][REPASO]) / f["total"] if f["total"] else 1,
                              f["nombre"]))
    return filas


# ─── Alertas ─────────────────────────────────────────────────────────────────

def _oculta(foto: FotoSalon, clave: tuple[int, str, str], ahora: datetime, p: ParametrosNucleo) -> bool:
    fecha = foto.ocultas.get(clave)
    return fecha is not None and ahora - fecha < timedelta(days=p.alerta_dias_oculta)


def alertas(
    foto: FotoSalon,
    ahora: datetime,
    p: ParametrosNucleo,
    tiene_generador: Callable[[str], bool],
    incluir_ocultas: bool = False,
) -> list[dict]:
    """Alertas de dificultad y de excelencia, siempre con estudiante y lección."""
    resultado: list[dict] = []
    salon: dict[str, tuple[int, int]] = {}

    def estado(est_id: int, lec_id: str) -> str:
        return estado_visible(foto.dominios.get((est_id, lec_id)), ahora, p)

    def titulo(lec_id: Optional[str]) -> Optional[str]:
        return foto.lecciones[lec_id].titulo if lec_id in foto.lecciones else lec_id

    for e in foto.estudiantes:
        asignadas = foto.asignadas.get(e.id, set())
        en_practica = foto.habilitadas | asignadas

        # ── Dificultad ──────────────────────────────────────────────────────
        for lec_id in sorted(en_practica, key=lambda i: foto.lecciones[i].orden if i in foto.lecciones else 0):
            if lec_id not in foto.lecciones or estado(e.id, lec_id) != EN_PROGRESO:
                continue
            todos = foto.resultados.get((e.id, lec_id), [])
            if len(todos) < p.alerta_dificultad_min_problemas:
                continue
            prec = reglas.precision(reglas.recientes(todos, p))
            if lec_id not in salon:
                salon[lec_id] = proporcion_dominan(foto, lec_id, ahora, p)
            dominan, total = salon[lec_id]

            motivo, pre_id, prec_pre, refuerzo = None, None, None, 0
            if prec is not None and prec < p.alerta_dificultad_umbral:
                debiles = [pre for pre in foto.prerrequisitos.get(lec_id, ())
                           if not _domina(estado(e.id, pre))]
                for pre in debiles:
                    recibido = foto.refuerzo_reciente.get((e.id, pre), 0)
                    prec_p = reglas.precision(reglas.recientes(foto.resultados.get((e.id, pre), []), p))
                    if recibido >= p.alerta_dificultad_min_refuerzo and (prec_p is None or prec_p < p.alerta_dificultad_umbral):
                        motivo, pre_id, prec_pre, refuerzo = MOTIVO_REFUERZO, pre, prec_p, recibido
                        break
                if motivo is None and not any(tiene_generador(pre) for pre in debiles):
                    motivo = MOTIVO_SIN_REFUERZO
            if (motivo is None and total >= p.alerta_salon_min_estudiantes
                    and dominan / total >= p.alerta_salon_proporcion):
                motivo = MOTIVO_SALON
            if motivo is None:
                continue
            clave = (e.id, lec_id, ALERTA_DIFICULTAD)
            if not incluir_ocultas and _oculta(foto, clave, ahora, p):
                continue
            sugerencia = None
            if pre_id and pre_id not in foto.habilitadas and pre_id not in asignadas and tiene_generador(pre_id):
                sugerencia = {"accion": "asignar", "leccion_id": pre_id, "titulo": titulo(pre_id)}
            resultado.append({
                "tipo": ALERTA_DIFICULTAD, "motivo": motivo,
                "estudiante_id": e.id, "estudiante_nombre": e.nombre,
                "leccion_id": lec_id, "leccion_titulo": titulo(lec_id),
                "precision": _redondear(prec), "problemas": len(todos),
                "prerrequisito_id": pre_id, "prerrequisito_titulo": titulo(pre_id) if pre_id else None,
                "precision_prerrequisito": _redondear(prec_pre), "refuerzo_recibido": refuerzo,
                "prerrequisito_asignado": bool(pre_id) and pre_id in asignadas,
                "dominan_salon": dominan, "total_salon": total,
                "sugerencia": sugerencia, "oculta": _oculta(foto, clave, ahora, p),
            })

        # ── Excelencia en la extensión ──────────────────────────────────────
        for (est_id, lec_id), ext in sorted(foto.extension.items()):
            if est_id != e.id or lec_id in en_practica or _domina(estado(e.id, lec_id)):
                continue
            if len(ext) < p.alerta_excelencia_min_problemas:
                continue
            prec = reglas.precision(reglas.recientes(ext, p))
            if prec is None or prec < p.alerta_excelencia_umbral:
                continue
            clave = (e.id, lec_id, ALERTA_EXCELENCIA)
            if not incluir_ocultas and _oculta(foto, clave, ahora, p):
                continue
            resultado.append({
                "tipo": ALERTA_EXCELENCIA, "motivo": MOTIVO_EXTENSION,
                "estudiante_id": e.id, "estudiante_nombre": e.nombre,
                "leccion_id": lec_id, "leccion_titulo": titulo(lec_id),
                "precision": _redondear(prec), "problemas": len(ext),
                "prerrequisito_id": None, "prerrequisito_titulo": None, "precision_prerrequisito": None,
                "refuerzo_recibido": 0, "prerrequisito_asignado": False, "dominan_salon": None, "total_salon": None,
                "sugerencia": {"accion": "habilitar", "leccion_id": lec_id, "titulo": titulo(lec_id)},
                "oculta": _oculta(foto, clave, ahora, p),
            })

    # Dificultad primero; dentro de cada tipo, por estudiante y orden del programa
    def orden(a: dict):
        lec = foto.lecciones.get(a["leccion_id"])
        return (a["tipo"] != ALERTA_DIFICULTAD, a["estudiante_nombre"], lec.orden if lec else 0)
    return sorted(resultado, key=orden)


# ─── Cortes por periodo (trimestre) ──────────────────────────────────────────

@dataclass(frozen=True)
class Periodo:
    numero: int
    inicio: date
    fin: date

    def contiene(self, momento: datetime, p: ParametrosNucleo) -> bool:
        return self.inicio <= reglas.fecha_local(momento, p) <= self.fin


def tabla_del_periodo(
    foto: FotoSalon,
    periodo: Periodo,
    dominadas: Iterable[tuple[int, str, datetime]],      # (estudiante, lección, fecha) de leccion_dominada
    p: ParametrosNucleo,
) -> list[dict]:
    """Por lección: quiénes la dominaron en el periodo, quiénes la practicaron y su acierto."""
    dominaron: dict[str, set[int]] = {}
    for est, lec, fecha in dominadas:
        if periodo.contiene(fecha, p):
            dominaron.setdefault(lec, set()).add(est)
    ids_salon = {e.id for e in foto.estudiantes}
    filas = []
    for lec_id in lecciones_de_la_tabla(foto) + sorted(set(dominaron) - set(lecciones_de_la_tabla(foto))):
        if lec_id not in foto.lecciones:
            continue
        lec = foto.lecciones[lec_id]
        practicaron, problemas, aciertos = set(), 0, 0
        for e in foto.estudiantes:
            rs = [r for r in foto.resultados.get((e.id, lec_id), []) if periodo.contiene(r.fecha, p)]
            if rs:
                practicaron.add(e.id)
                problemas += len(rs)
                aciertos += sum(r.acierto for r in rs)
        quienes = sorted(dominaron.get(lec_id, set()) & ids_salon)
        if not practicaron and not quienes:
            continue
        filas.append({
            "leccion_id": lec_id, "titulo": lec.titulo, "grado": lec.grado,
            "unidad_numero": lec.unidad_numero, "unidad_titulo": lec.unidad_titulo,
            "leccion_numero": lec.leccion_numero, "habilitada": lec_id in foto.habilitadas,
            "dominaron": quienes, "practicaron": len(practicaron), "problemas": problemas,
            "precision": _redondear(aciertos / problemas) if problemas else None,
        })
    return filas


# ─── Plan por trimestre ──────────────────────────────────────────────────────

def trimestre_vigente(trimestres: Sequence[Periodo], hoy: date) -> Optional[int]:
    """El último trimestre que ya empezó (en las vacaciones sigue el anterior). Antes del T1, None."""
    vigente = None
    for t in sorted(trimestres, key=lambda t: t.inicio):
        if t.inicio <= hoy:
            vigente = t.numero
    return vigente


def cambios_del_plan(
    plan: Mapping[str, set[int]],
    habilitaciones: Mapping[str, tuple[bool, bool]],     # lección → (habilitada, ajuste_manual)
    vigente: Optional[int],
) -> list[tuple[str, bool]]:
    """(lección, habilitar) para las lecciones del plan sin ajuste manual cuyo estado no coincide
    con el trimestre vigente. Sin trimestre vigente no hay cambios."""
    if vigente is None:
        return []
    cambios = []
    for lec_id, trimestres in sorted(plan.items()):
        habilitada, manual = habilitaciones.get(lec_id, (False, False))
        if manual:
            continue
        debe = vigente in trimestres
        if debe != habilitada:
            cambios.append((lec_id, debe))
    return cambios


# ─── Ficha ───────────────────────────────────────────────────────────────────

def errores_frecuentes(codigos: Iterable[str], descripciones: Mapping[str, str], limite: int = 6) -> list[dict]:
    """Errores clasificados más frecuentes, con su descripción para docentes (nunca el código solo)."""
    conteo = Counter(codigos)
    return [
        {"codigo": c, "descripcion": descripciones.get(c, "Otro error (sin clasificar)"),
         "camino": c.rsplit(".", 1)[0] if c.count(".") == 2 else None, "veces": n}
        for c, n in conteo.most_common(limite)
    ]


def dominio_por_camino(
    lecciones: Sequence[LeccionFoto], estados: Mapping[str, str]
) -> list[dict]:
    """Por camino: cuántas de sus lecciones (de las del estudiante) domina."""
    por_camino: dict[str, list[str]] = {}
    for lec in lecciones:
        for c in lec.caminos:
            por_camino.setdefault(c, []).append(lec.id)
    return [
        {"camino": c, "total": len(ids), "dominadas": sum(_domina(estados.get(i, SIN_EMPEZAR)) for i in ids),
         "en_progreso": sum(estados.get(i) == EN_PROGRESO for i in ids)}
        for c, ids in por_camino.items()
    ]

