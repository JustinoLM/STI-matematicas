"""
Router de exportación de datos para el panel de administración.

Endpoints:
  GET /admin/export/estudiantes  → listado completo de estudiantes
  GET /admin/export/diagnostico  → comparación pre-test vs post-test por estudiante
  GET /admin/export/sesiones     → historial de sesiones de práctica
  GET /admin/export/niveles      → evolución de niveles por estudiante
  GET /admin/export/medallas     → medallas obtenidas
  GET /admin/export/tienda       → transacciones de la tienda
  GET /admin/export/resumen      → resumen por organización
  GET /admin/export/desafios     → desafíos grupales por grupo (progreso y estado)
  GET /admin/export/participacion → participación de cada estudiante en los desafíos

Privacidad: por defecto las columnas de nombre salen vacías; el panel las pide solo
con `con_nombres=true`. Las columnas se conservan en su posición porque la importación
del Excel completo lee por posición.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select

from app.api.dependencies import DBSession, require_admin
from app.models.adaptive import (
    EstadoSesion,
    PerfilEstudiante,
    PruebaDiagnostica,
    ResultadoPostTest,
    SesionPractica,
)
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.gamification import EstudianteMedalla, Medalla, TipoTransaccion, TransaccionPuntos
from app.models.group import EstudianteGrupo, Grupo
from app.models.organization import Organizacion
from app.models.user import Estudiante
from app.repositories.adaptive_repository import (
    MIN_SESIONES_PARTICIPACION_DESAFIO,
    AdaptiveRepository,
)

# Todos los endpoints exigen token de administrador (POST /api/auth/admin-login)
router = APIRouter(dependencies=[Depends(require_admin)])


# ─── helpers ─────────────────────────────────────────────────────────────────

def _fmt(val) -> str:
    """Convierte None a cadena vacía para exports limpios."""
    if val is None:
        return ""
    return str(val)


def _nombre(est, con_nombres: bool) -> str:
    """Nombre del estudiante solo si el administrador lo pidió explícitamente."""
    return (est.nombre_completo or "") if con_nombres else ""


def _pct(correctos, total) -> str:
    if not total:
        return ""
    return f"{round(correctos / total * 100, 1)}%"


# ─── Estudiantes ──────────────────────────────────────────────────────────────

@router.get("/admin/export/estudiantes")
async def exportar_estudiantes(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """Listado completo de estudiantes con datos básicos y estado de cuenta."""
    stmt = (
        select(Estudiante, Organizacion)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
        .order_by(Organizacion.nombre, Estudiante.grado_academico, Estudiante.nombre_completo)
    )
    if org_id:
        stmt = stmt.where(Estudiante.organizacion_id == org_id)
    rows = (await db.execute(stmt)).all()

    data = [
        {
            "codigo_estudiante": est.codigo_estudiante,
            "nombre_completo": _nombre(est, con_nombres),
            "genero": est.genero.value if est.genero else "",
            "grado_academico": _fmt(est.grado_academico),
            "edad": _fmt(est.edad),
            "organizacion": org.nombre if org else "",
            "puntos_actuales": est.puntos_totales or 0,
            "activo": "Sí" if est.activo else "No",
            "fecha_creacion": _fmt(est.fecha_creacion),
            "ultimo_acceso": _fmt(est.ultimo_acceso),
        }
        for est, org in rows
    ]

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


# ─── Pre-test vs Post-test ────────────────────────────────────────────────────

@router.get("/admin/export/diagnostico")
async def exportar_diagnostico(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """
    Comparación pre-test (PruebaDiagnostica) vs post-test (ResultadoPostTest)
    por estudiante. Una fila por estudiante con resultados de ambas pruebas
    y el delta de mejora por operación.
    """
    # Obtener todos los estudiantes de la org
    stmt_est = (
        select(Estudiante, Organizacion)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
    )
    if org_id:
        stmt_est = stmt_est.where(Estudiante.organizacion_id == org_id)
    stmt_est = stmt_est.order_by(Estudiante.grado_academico, Estudiante.nombre_completo)
    estudiantes = (await db.execute(stmt_est)).all()

    # Pre-test por estudiante
    stmt_pre = select(PruebaDiagnostica)
    if org_id:
        stmt_pre = stmt_pre.join(Estudiante, Estudiante.id == PruebaDiagnostica.estudiante_id).where(Estudiante.organizacion_id == org_id)
    pre_tests = {p.estudiante_id: p for p in (await db.execute(stmt_pre)).scalars().all()}

    # Post-test por estudiante
    stmt_post = select(ResultadoPostTest)
    if org_id:
        stmt_post = stmt_post.where(ResultadoPostTest.org_id == org_id)
    post_tests = {p.estudiante_id: p for p in (await db.execute(stmt_post)).scalars().all()}

    def bool_to_int(v):
        if v is None:
            return None
        return 1 if v else 0

    def correctos_pre(pre, op):
        """Suma los dos niveles de la operación (0, 1 o 2 correctos)."""
        if pre is None:
            return None
        n1 = bool_to_int(getattr(pre, f"{op}_nivel1_correcto"))
        n2 = bool_to_int(getattr(pre, f"{op}_nivel2_correcto"))
        if n1 is None and n2 is None:
            return None
        return (n1 or 0) + (n2 or 0)

    def correctos_post(post, op):
        if post is None or not post.completado:
            return None
        n1 = bool_to_int(getattr(post, f"{op}_nivel1_correcto"))
        n2 = bool_to_int(getattr(post, f"{op}_nivel2_correcto"))
        if n1 is None and n2 is None:
            return None
        return (n1 or 0) + (n2 or 0)

    def delta(pre_val, post_val):
        if pre_val is None or post_val is None:
            return ""
        return post_val - pre_val

    OPERACIONES = ["suma", "resta", "mult", "div"]

    data = []
    for est, org in estudiantes:
        pre  = pre_tests.get(est.id)
        post = post_tests.get(est.id)

        pre_completado  = pre is not None and pre.estado == "completado"
        post_completado = post is not None and post.completado

        # Total correctos (sobre 8 problemas)
        pre_total  = sum((correctos_pre(pre, op) or 0)  for op in OPERACIONES) if pre_completado  else None
        post_total = sum((correctos_post(post, op) or 0) for op in OPERACIONES) if post_completado else None

        row = {
            "codigo_estudiante":    est.codigo_estudiante,
            "nombre_estudiante":    _nombre(est, con_nombres),
            "grado":                _fmt(est.grado_academico),
            "organizacion":         org.nombre if org else "",
            # — Pre-test —
            "pre_completado":       "Sí" if pre_completado else "No",
            "pre_fecha":            _fmt(pre.fecha_fin) if pre_completado else "",
            "pre_suma_correctos":   _fmt(correctos_pre(pre, "suma"))  if pre_completado else "",
            "pre_resta_correctos":  _fmt(correctos_pre(pre, "resta")) if pre_completado else "",
            "pre_mult_correctos":   _fmt(correctos_pre(pre, "mult"))  if pre_completado else "",
            "pre_div_correctos":    _fmt(correctos_pre(pre, "div"))   if pre_completado else "",
            "pre_total_correctos":  _fmt(pre_total) if pre_completado else "",
            "pre_nivel_suma":       _fmt(pre.nivel_suma_asignado)    if pre_completado else "",
            "pre_nivel_resta":      _fmt(pre.nivel_resta_asignado)   if pre_completado else "",
            "pre_nivel_mult":       _fmt(pre.nivel_mult_asignado)    if pre_completado else "",
            "pre_nivel_div":        _fmt(pre.nivel_div_asignado)     if pre_completado else "",
            # — Post-test —
            "post_completado":      "Sí" if post_completado else "No",
            "post_fecha":           _fmt(post.fecha_fin) if post_completado else "",
            "post_suma_correctos":  _fmt(correctos_post(post, "suma"))  if post_completado else "",
            "post_resta_correctos": _fmt(correctos_post(post, "resta")) if post_completado else "",
            "post_mult_correctos":  _fmt(correctos_post(post, "mult"))  if post_completado else "",
            "post_div_correctos":   _fmt(correctos_post(post, "div"))   if post_completado else "",
            "post_total_correctos": _fmt(post_total) if post_completado else "",
            # — Delta (mejora) —
            "delta_suma":           _fmt(delta(correctos_pre(pre, "suma"),  correctos_post(post, "suma"))),
            "delta_resta":          _fmt(delta(correctos_pre(pre, "resta"), correctos_post(post, "resta"))),
            "delta_mult":           _fmt(delta(correctos_pre(pre, "mult"),  correctos_post(post, "mult"))),
            "delta_div":            _fmt(delta(correctos_pre(pre, "div"),   correctos_post(post, "div"))),
            "delta_total":          _fmt(delta(pre_total, post_total)),
            # — Uso del sistema —
            "sesiones_completadas": 0,  # se llena abajo
        }
        data.append((est.id, row))

    # Contar sesiones completadas por estudiante
    stmt_ses = select(SesionPractica.estudiante_id, SesionPractica.id).where(SesionPractica.estado == EstadoSesion.COMPLETADA)
    if org_id:
        stmt_ses = stmt_ses.join(Estudiante, Estudiante.id == SesionPractica.estudiante_id).where(Estudiante.organizacion_id == org_id)
    sesiones_rows = (await db.execute(stmt_ses)).all()
    sesiones_count = {}
    for est_id, _ in sesiones_rows:
        sesiones_count[est_id] = sesiones_count.get(est_id, 0) + 1

    final_data = []
    for est_id, row in data:
        row["sesiones_completadas"] = sesiones_count.get(est_id, 0)
        final_data.append(row)

    return {"columnas": list(final_data[0].keys()) if final_data else [], "filas": final_data}


# ─── Sesiones ─────────────────────────────────────────────────────────────────

@router.get("/admin/export/sesiones")
async def exportar_sesiones(
    db: DBSession,
    org_id: Optional[int] = Query(None, description="Filtrar por organización"),
    con_nombres: bool = Query(False, description="Incluir el nombre de cada estudiante"),
):
    """
    Devuelve el historial completo de sesiones de práctica completadas.
    Incluye: estudiante, organización, fecha, duración, precisión,
             nivel inicial, puntos ganados, práctica perfecta.
    """
    stmt = (
        select(SesionPractica, Estudiante, Organizacion)
        .join(Estudiante, Estudiante.id == SesionPractica.estudiante_id)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
        .where(SesionPractica.estado == EstadoSesion.COMPLETADA)
    )
    if org_id:
        stmt = stmt.where(Estudiante.organizacion_id == org_id)

    stmt = stmt.order_by(SesionPractica.fecha_inicio)
    rows = (await db.execute(stmt)).all()

    data = []
    for sesion, est, org in rows:
        duracion = ""
        if sesion.fecha_inicio and sesion.fecha_fin:
            secs = int((sesion.fecha_fin - sesion.fecha_inicio).total_seconds())
            duracion = f"{secs // 60}m {secs % 60}s"

        total = (sesion.problemas_correctos or 0) + (sesion.problemas_incorrectos or 0)
        data.append({
            "sesion_id": sesion.id,
            "codigo_estudiante": est.codigo_estudiante,
            "nombre_estudiante": _nombre(est, con_nombres),
            "organizacion": org.nombre if org else "",
            "fecha_inicio": _fmt(sesion.fecha_inicio),
            "fecha_fin": _fmt(sesion.fecha_fin),
            "duracion": duracion,
            "problemas_total": total,
            "problemas_correctos": sesion.problemas_correctos or 0,
            "problemas_incorrectos": sesion.problemas_incorrectos or 0,
            "precision": _pct(sesion.problemas_correctos, total),
            "nivel_al_iniciar": sesion.nivel_actual_inicio or "",
            "puntos_ganados": sesion.puntos_ganados or 0,
            "practica_perfecta": "Sí" if sesion.es_practica_perfecta else "No",
            "operaciones": _fmt(sesion.operaciones_incluidas),
        })

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


# ─── Evolución de niveles ──────────────────────────────────────────────────────

@router.get("/admin/export/niveles")
async def exportar_niveles(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """
    Devuelve la evolución de niveles por sesión completada.
    Permite graficar el progreso de cada estudiante a lo largo del tiempo.
    También incluye el nivel actual (snapshot del perfil).
    """
    stmt = (
        select(SesionPractica, Estudiante, Organizacion)
        .join(Estudiante, Estudiante.id == SesionPractica.estudiante_id)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
        .where(SesionPractica.estado == EstadoSesion.COMPLETADA)
    )
    if org_id:
        stmt = stmt.where(Estudiante.organizacion_id == org_id)
    stmt = stmt.order_by(Estudiante.id, SesionPractica.fecha_fin)
    rows = (await db.execute(stmt)).all()

    # Nivel actual por estudiante (snapshot más reciente)
    perfil_stmt = select(PerfilEstudiante)
    if org_id:
        perfil_stmt = perfil_stmt.join(
            Estudiante, Estudiante.id == PerfilEstudiante.estudiante_id
        ).where(Estudiante.organizacion_id == org_id)
    perfiles = {p.estudiante_id: p for p in (await db.execute(perfil_stmt)).scalars().all()}

    data = []
    for sesion, est, org in rows:
        cambios = sesion.cambios_nivel or {}
        data.append({
            "codigo_estudiante": est.codigo_estudiante,
            "nombre_estudiante": _nombre(est, con_nombres),
            "organizacion": org.nombre if org else "",
            "fecha": _fmt(sesion.fecha_fin),
            "nivel_general": sesion.nivel_actual_inicio or "",
            "nivel_suma": sesion.nivel_suma_inicio or "",
            "nivel_resta": sesion.nivel_resta_inicio or "",
            "nivel_multiplicacion": sesion.nivel_multiplicacion_inicio or "",
            "nivel_division": sesion.nivel_division_inicio or "",
            "cambios_en_sesion": _fmt(cambios) if cambios else "Ninguno",
        })

    # Agregar fila de nivel actual por estudiante
    actuales = []
    for est_id, perfil in perfiles.items():
        est_row = next((e for _, e, _ in rows if e.id == est_id), None)
        org_row = next((o for _, e, o in rows if e.id == est_id), None)
        if est_row:
            actuales.append({
                "codigo_estudiante": est_row.codigo_estudiante,
                "nombre_estudiante": _nombre(est_row, con_nombres),
                "organizacion": org_row.nombre if org_row else "",
                "nivel_actual_suma": perfil.nivel_suma,
                "nivel_actual_resta": perfil.nivel_resta,
                "nivel_actual_multiplicacion": perfil.nivel_multiplicacion,
                "nivel_actual_division": perfil.nivel_division,
                "nivel_actual_general": perfil.nivel_actual,
                "total_sesiones": perfil.total_sesiones,
                "precision_ultimos_15": _pct(
                    round(float(perfil.precision_ultimos_15 or 0) * 15),
                    15
                ),
            })

    return {
        "historial": {
            "columnas": list(data[0].keys()) if data else [],
            "filas": data,
        },
        "nivel_actual": {
            "columnas": list(actuales[0].keys()) if actuales else [],
            "filas": actuales,
        },
    }


# ─── Medallas ─────────────────────────────────────────────────────────────────

@router.get("/admin/export/medallas")
async def exportar_medallas(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """Historial de medallas obtenidas por estudiantes."""
    stmt = (
        select(EstudianteMedalla, Estudiante, Medalla, Organizacion)
        .join(Estudiante, Estudiante.id == EstudianteMedalla.estudiante_id)
        .join(Medalla, Medalla.id == EstudianteMedalla.medalla_id)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
    )
    if org_id:
        stmt = stmt.where(Estudiante.organizacion_id == org_id)
    stmt = stmt.order_by(EstudianteMedalla.fecha_obtencion)
    rows = (await db.execute(stmt)).all()

    data = [
        {
            "codigo_estudiante": est.codigo_estudiante,
            "nombre_estudiante": _nombre(est, con_nombres),
            "organizacion": org.nombre if org else "",
            "medalla": medalla.nombre,
            "categoria": medalla.categoria.value if hasattr(medalla.categoria, "value") else str(medalla.categoria),
            "descripcion": medalla.descripcion,
            "fecha_obtencion": _fmt(em.fecha_obtencion),
        }
        for em, est, medalla, org in rows
    ]

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


# ─── Tienda ───────────────────────────────────────────────────────────────────

@router.get("/admin/export/tienda")
async def exportar_tienda(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """Historial de compras en la tienda (transacciones de tipo 'compra')."""
    stmt = (
        select(TransaccionPuntos, Estudiante, Organizacion)
        .join(Estudiante, Estudiante.id == TransaccionPuntos.estudiante_id)
        .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
        .where(TransaccionPuntos.tipo == TipoTransaccion.GASTO)
    )
    if org_id:
        stmt = stmt.where(Estudiante.organizacion_id == org_id)
    stmt = stmt.order_by(TransaccionPuntos.fecha)
    rows = (await db.execute(stmt)).all()

    data = [
        {
            "codigo_estudiante": est.codigo_estudiante,
            "nombre_estudiante": _nombre(est, con_nombres),
            "organizacion": org.nombre if org else "",
            "item_comprado": tx.concepto,
            "puntos_gastados": abs(tx.cantidad),
            "saldo_resultante": tx.saldo_resultante,
            "fecha": _fmt(tx.fecha),
        }
        for tx, est, org in rows
    ]

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


# ─── Resumen por organización ─────────────────────────────────────────────────

@router.get("/admin/export/resumen")
async def exportar_resumen(db: DBSession):
    """
    Resumen agregado por organización:
    estudiantes activos, total sesiones, precisión promedio,
    medallas otorgadas, compras realizadas.
    """
    orgs = (await db.execute(select(Organizacion))).scalars().all()

    data = []
    for org in orgs:
        # Estudiantes
        est_ids_res = await db.execute(
            select(Estudiante.id).where(Estudiante.organizacion_id == org.id)
        )
        est_ids = [r for r, in est_ids_res.all()]
        if not est_ids:
            continue

        # Sesiones completadas
        ses_res = await db.execute(
            select(SesionPractica).where(
                and_(
                    SesionPractica.estudiante_id.in_(est_ids),
                    SesionPractica.estado == EstadoSesion.COMPLETADA,
                )
            )
        )
        sesiones = ses_res.scalars().all()
        total_ses = len(sesiones)
        precision_avg = ""
        if total_ses:
            totales = [(s.problemas_correctos or 0) + (s.problemas_incorrectos or 0) for s in sesiones]
            correctos = [s.problemas_correctos or 0 for s in sesiones]
            total_probs = sum(totales)
            total_corr = sum(correctos)
            precision_avg = _pct(total_corr, total_probs)

        # Medallas
        med_count = len(
            (await db.execute(
                select(EstudianteMedalla.id).where(
                    EstudianteMedalla.estudiante_id.in_(est_ids)
                )
            )).all()
        )

        # Compras
        compras_count = len(
            (await db.execute(
                select(TransaccionPuntos.id).where(
                    and_(
                        TransaccionPuntos.estudiante_id.in_(est_ids),
                        TransaccionPuntos.tipo == TipoTransaccion.GASTO,
                    )
                )
            )).all()
        )

        # Desafíos grupales de los grupos con estudiantes de la organización
        desafios_org = (await db.execute(
            select(
                func.count(func.distinct(GrupoDesafio.desafio_id)),
                func.count(func.distinct(GrupoDesafio.desafio_id)).filter(GrupoDesafio.puntos_otorgados.is_(True)),
            )
            .join(DesafioGrupal, DesafioGrupal.id == GrupoDesafio.desafio_id)
            .join(EstudianteGrupo, EstudianteGrupo.grupo_id == GrupoDesafio.grupo_id)
            .where(and_(EstudianteGrupo.estudiante_id.in_(est_ids), DesafioGrupal.eliminado.is_(False)))
        )).one()

        data.append({
            "organizacion": org.nombre,
            "codigo": org.codigo,
            "total_estudiantes": len(est_ids),
            "total_sesiones": total_ses,
            "precision_promedio": precision_avg,
            "medallas_otorgadas": med_count,
            "compras_realizadas": compras_count,
            "desafios_asignados": desafios_org[0],
            "desafios_completados": desafios_org[1],
        })

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


# ─── Desafíos grupales ────────────────────────────────────────────────────────

async def _filas_desafios(db, org_id: Optional[int]):
    """
    Una fila por (desafío, grupo) con los miembros activos del grupo.
    Con `org_id` solo cuentan los grupos con al menos un estudiante de esa organización.
    Devuelve [(desafio, grupo_desafio, grupo, [(estudiante, organizacion)])].
    """
    stmt = (
        select(DesafioGrupal, GrupoDesafio, Grupo)
        .join(GrupoDesafio, GrupoDesafio.desafio_id == DesafioGrupal.id)
        .join(Grupo, Grupo.id == GrupoDesafio.grupo_id)
        .where(DesafioGrupal.eliminado.is_(False))
        .order_by(DesafioGrupal.fecha_creacion, DesafioGrupal.id, Grupo.nombre)
    )
    filas = []
    for desafio, gd, grupo in (await db.execute(stmt)).all():
        miembros_stmt = (
            select(Estudiante, Organizacion)
            .join(EstudianteGrupo, EstudianteGrupo.estudiante_id == Estudiante.id)
            .outerjoin(Organizacion, Organizacion.id == Estudiante.organizacion_id)
            .where(and_(EstudianteGrupo.grupo_id == grupo.id, EstudianteGrupo.activo.is_(True)))
            .order_by(Estudiante.codigo_estudiante)
        )
        if org_id:
            miembros_stmt = miembros_stmt.where(Estudiante.organizacion_id == org_id)
        miembros = (await db.execute(miembros_stmt)).all()
        if org_id and not miembros:
            continue
        filas.append((desafio, gd, grupo, miembros))
    return filas


@router.get("/admin/export/desafios")
async def exportar_desafios(
    db: DBSession,
    org_id: Optional[int] = Query(None),
):
    """
    Desafíos grupales: una fila por desafío y grupo, con su ventana de fechas, el progreso
    del grupo, si lo completó y cuántos miembros participaron (completaron al menos
    MIN_SESIONES_PARTICIPACION_DESAFIO sesiones dentro de la ventana).
    """
    repo = AdaptiveRepository(db)
    data = []
    for desafio, gd, grupo, _miembros in await _filas_desafios(db, org_id):
        participantes = await repo.get_participantes_desafio(grupo.id, desafio)
        data.append({
            "id_desafio": desafio.id,
            "nombre": desafio.nombre,
            "tipo": desafio.tipo,
            "grupo": grupo.nombre,
            "objetivo": desafio.objetivo_cantidad,
            "parametro_adicional": _fmt(desafio.parametro_adicional),
            "fecha_inicio": _fmt(desafio.fecha_creacion),
            "fecha_fin": _fmt(desafio.fecha_limite),
            "progreso_grupo": gd.progreso_actual,
            "completado": "Sí" if gd.puntos_otorgados else "No",
            "estudiantes_participantes": len(participantes),
            "recompensa_puntos": _fmt(desafio.recompensa_puntos),
            "recompensa_texto": _fmt(desafio.recompensa_texto),
        })

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}


@router.get("/admin/export/participacion")
async def exportar_participacion(
    db: DBSession,
    org_id: Optional[int] = Query(None),
    con_nombres: bool = Query(False),
):
    """
    Participación de cada miembro activo de cada grupo en cada desafío: sesiones completadas
    dentro de la ventana del desafío, si participó (mínimo de sesiones) y si cuenta para las
    medallas de desafíos (participó y su grupo completó el desafío).
    """
    repo = AdaptiveRepository(db)
    data = []
    for desafio, gd, grupo, miembros in await _filas_desafios(db, org_id):
        condiciones = repo._condiciones_ventana_desafio(desafio)
        for est, org in miembros:
            sesiones = (await db.execute(
                select(func.count(SesionPractica.id)).where(and_(
                    SesionPractica.estudiante_id == est.id, *condiciones,
                ))
            )).scalar() or 0
            participo = sesiones >= MIN_SESIONES_PARTICIPACION_DESAFIO
            completado = bool(gd.puntos_otorgados)
            data.append({
                "codigo_estudiante": est.codigo_estudiante,
                "nombre_estudiante": _nombre(est, con_nombres),
                "organizacion": org.nombre if org else "",
                "grupo": grupo.nombre,
                "id_desafio": desafio.id,
                "sesiones_en_ventana": sesiones,
                "participo": "Sí" if participo else "No",
                "desafio_completado_por_grupo": "Sí" if completado else "No",
                "cuenta_para_medalla": "Sí" if (participo and completado) else "No",
            })

    return {"columnas": list(data[0].keys()) if data else [], "filas": data}
