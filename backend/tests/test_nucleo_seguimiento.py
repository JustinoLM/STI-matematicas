"""
Seguimiento del profesor (fase 6b): tabla del salón, alertas (cuándo saltan y cuándo no), cortes
por trimestre, plan por trimestre (sin pisar ajustes manuales), ficha del estudiante, número fijo
de consultas y permisos de las rutas.
"""

from datetime import date, datetime, timedelta
from itertools import count

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select

from app.main import app
from app.models.nucleo import (
    ALERTA_DIFICULTAD,
    ALERTA_EXCELENCIA,
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    PROBLEMA_TERMINADO,
    SESION_COMPLETADA,
    XP_LECCION_DOMINADA,
    ZONA_EXTENSION,
    ZONA_NORMAL,
    ZONA_REFUERZO,
    NucleoDominio,
    NucleoExperiencia,
    NucleoHabilitacion,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.models.school import ANIO_CERRADO, MATRICULA_CERRADA, AnioLectivo, Matricula
from app.models.user import Estudiante
from app.nucleo import seguimiento as calc
from app.nucleo.dominio import EstadoDominio, Resultado
from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.seguimiento import (
    DOMINADO,
    EN_PROGRESO,
    MOTIVO_REFUERZO,
    MOTIVO_SALON,
    MOTIVO_SIN_REFUERZO,
    POR_CONFIRMAR,
    REPASO,
    SIN_EMPEZAR,
    EstudianteFoto,
    FotoSalon,
    LeccionFoto,
    Periodo,
)
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.plan import ServicioPlan
from app.nucleo.servicios.practica import ServicioPractica
from app.nucleo.servicios.seguimiento import ServicioSeguimiento, descripciones_de_errores
from app.services.curriculo_service import cargar_programa, leer_programa
from app.services.school_service import NoEncontrado
from tests.conftest import TestSessionLocal, test_engine
from tests.salones_helpers import crear_organizacion, salon_con_estudiantes
from tests.test_organizacion_escolar import _estudiante, _org, _profesor, _salon

P = ParametrosNucleo()
AHORA = datetime(2026, 11, 13, 15, 0)
L1, L2, L3, EXT = "g1-u03-l01", "g1-u03-l02", "g1-u03-l03", "g1-u05-l01"
_n = count(1)


def res(*aciertos: bool, dias_atras: int = 1) -> list[Resultado]:
    return [Resultado(a, AHORA - timedelta(days=dias_atras, minutes=len(aciertos) - i)) for i, a in enumerate(aciertos)]


def leccion(i: str, orden: int, caminos=("naturales.suma",)) -> LeccionFoto:
    return LeccionFoto(i, f"Lección {i}", 1, int(i[4:6]), f"Unidad {int(i[4:6])}", int(i[-2:]), orden, caminos)


def foto(n_estudiantes: int = 3, **kw) -> FotoSalon:
    base = dict(
        estudiantes=[EstudianteFoto(i, f"Est {i:02d}", f"E{i}") for i in range(1, n_estudiantes + 1)],
        lecciones={L1: leccion(L1, 1), L2: leccion(L2, 2, ("naturales.resta",)), L3: leccion(L3, 3), EXT: leccion(EXT, 4)},
        habilitadas={L2, L3}, prioritarias={L3}, asignadas={}, dominios={}, resultados={}, extension={},
        refuerzo_reciente={}, prerrequisitos={L2: (L1,), L3: (L2,), EXT: (L3,)},
    )
    base.update(kw)
    return FotoSalon(**base)


def con_generador(i: str) -> bool:
    return i in (L1, L2, L3, EXT)


def sin_generador(i: str) -> bool:
    return False


MAL = [False] * 7 + [True] * 3        # 30 %


# ─── Estados y tabla ─────────────────────────────────────────────────────────

def test_estado_visible_incluye_repaso():
    assert calc.estado_visible(None, AHORA, P) == SIN_EMPEZAR
    assert calc.estado_visible(EstadoDominio(DOMINIO_EN_PROGRESO), AHORA, P) == EN_PROGRESO
    reciente = EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA - timedelta(days=3))
    viejo = EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA - timedelta(days=20))
    assert calc.estado_visible(reciente, AHORA, P) == DOMINADO
    assert calc.estado_visible(viejo, AHORA, P) == REPASO


def test_tabla_por_leccion_cuenta_estados_y_porcentaje():
    f = foto(4, asignadas={2: {EXT}}, dominios={
        (1, L2): EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA - timedelta(days=1)),
        (2, L2): EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA - timedelta(days=30)),
        (3, L2): EstadoDominio(DOMINIO_EN_PROGRESO),
    })
    filas = calc.tabla_por_leccion(f, AHORA, P)
    assert [x["leccion_id"] for x in filas] == [L2, L3, EXT]           # asignada solo a uno: al final
    l2 = filas[0]
    assert l2["conteos"] == {DOMINADO: 1, REPASO: 1, POR_CONFIRMAR: 0, EN_PROGRESO: 1, SIN_EMPEZAR: 1}
    assert (l2["dominan"], l2["total"], l2["porcentaje_dominan"]) == (2, 4, 0.5)
    assert l2["estudiantes"][REPASO] == [2]
    ext = filas[2]
    assert (ext["habilitada"], ext["total"], ext["estudiantes"][SIN_EMPEZAR]) == (False, 1, [2])
    assert filas[1]["prioritaria"]


def test_tabla_por_estudiante_pone_primero_a_quien_necesita_atencion():
    f = foto(3, dominios={(1, L2): EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA)})
    alertas = [{"tipo": ALERTA_DIFICULTAD, "estudiante_id": 3}]
    filas = calc.tabla_por_estudiante(f, alertas, AHORA, P)
    assert [x["estudiante_id"] for x in filas] == [3, 2, 1]
    assert filas[2]["conteos"][DOMINADO] == 1 and filas[2]["total"] == 2


# ─── Alertas de dificultad ───────────────────────────────────────────────────

def test_dificultad_cuando_el_refuerzo_no_basta():
    f = foto(dominios={(1, L2): EstadoDominio(DOMINIO_EN_PROGRESO), (1, L1): EstadoDominio(DOMINIO_EN_PROGRESO)},
             resultados={(1, L2): res(*MAL), (1, L1): res(False, False, True, False)},
             refuerzo_reciente={(1, L1): 4})
    [a] = calc.alertas(f, AHORA, P, con_generador)
    assert (a["tipo"], a["motivo"], a["estudiante_id"], a["leccion_id"]) == (ALERTA_DIFICULTAD, MOTIVO_REFUERZO, 1, L2)
    assert (a["prerrequisito_id"], a["precision"], a["precision_prerrequisito"], a["refuerzo_recibido"]) == (L1, 0.3, 0.25, 4)
    assert a["sugerencia"] == {"accion": "asignar", "leccion_id": L1, "titulo": f"Lección {L1}"}
    assert (a["dominan_salon"], a["total_salon"]) == (0, 3)


def test_dificultad_sin_refuerzo_posible():
    f = foto(dominios={(1, L2): EstadoDominio(DOMINIO_EN_PROGRESO)}, resultados={(1, L2): res(*MAL)})
    [a] = calc.alertas(f, AHORA, P, sin_generador)
    assert (a["motivo"], a["sugerencia"]) == (MOTIVO_SIN_REFUERZO, None)


@pytest.mark.parametrize("caso", ["pocos_problemas", "va_bien", "refuerzo_en_curso", "ya_domina", "pre_dominado"])
def test_dificultad_no_salta(caso):
    dominios = {(1, L2): EstadoDominio(DOMINIO_EN_PROGRESO)}
    resultados = {(1, L2): res(*MAL), (1, L1): res(False, False)}
    refuerzo = {(1, L1): 4}
    if caso == "pocos_problemas":
        resultados[(1, L2)] = res(*MAL[:9])
    elif caso == "va_bien":
        resultados[(1, L2)] = res(*([True] * 7 + [False] * 3))
    elif caso == "refuerzo_en_curso":
        refuerzo = {(1, L1): 3}
    elif caso == "ya_domina":
        dominios[(1, L2)] = EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA)
    elif caso == "pre_dominado":       # el prerrequisito ya está dominado y la lección tiene generador
        dominios[(1, L1)] = EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA)
        f = foto(dominios=dominios, resultados=resultados, refuerzo_reciente=refuerzo,
                 prerrequisitos={L2: (L1, L3)}, habilitadas={L2})
        assert calc.alertas(f, AHORA, P, con_generador) == []
        return
    f = foto(dominios=dominios, resultados=resultados, refuerzo_reciente=refuerzo)
    assert calc.alertas(f, AHORA, P, con_generador) == []


def test_va_detras_del_salon_solo_con_suficientes_estudiantes():
    def armar(n):
        dominios = {(i, L2): EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA) for i in range(2, n + 1)}
        dominios[(1, L2)] = EstadoDominio(DOMINIO_EN_PROGRESO)
        # Va bien (70 %) pero lleva 12 problemas sin dominar y casi todos ya la dominan
        return foto(n, dominios=dominios, resultados={(1, L2): res(*([True] * 7 + [False] * 3), True, False)})
    [a] = calc.alertas(armar(6), AHORA, P, con_generador)
    assert (a["motivo"], a["dominan_salon"], a["total_salon"]) == (MOTIVO_SALON, 5, 6)
    assert calc.alertas(armar(4), AHORA, P, con_generador) == []    # menos de 5: no se compara


# ─── Alertas de excelencia ───────────────────────────────────────────────────

def test_excelencia_en_la_extension():
    buena = res(True, True, True, True, False, True)
    f = foto(extension={(2, EXT): buena})
    [a] = calc.alertas(f, AHORA, P, con_generador)
    assert (a["tipo"], a["estudiante_id"], a["leccion_id"], a["problemas"]) == (ALERTA_EXCELENCIA, 2, EXT, 6)
    assert a["sugerencia"]["accion"] == "habilitar"


@pytest.mark.parametrize("caso", ["pocos", "baja", "habilitada", "asignada", "dominada"])
def test_excelencia_no_salta(caso):
    ext = res(True, True, True, True, True, True)
    kw = {}
    if caso == "pocos":
        ext = ext[:4]
    elif caso == "baja":
        ext = res(True, False, True, False, True, True)
    elif caso == "habilitada":
        kw["habilitadas"] = {L2, L3, EXT}
    elif caso == "asignada":
        kw["asignadas"] = {2: {EXT}}
    elif caso == "dominada":
        kw["dominios"] = {(2, EXT): EstadoDominio(DOMINIO_DOMINADO, AHORA, AHORA)}
    assert calc.alertas(foto(extension={(2, EXT): ext}, **kw), AHORA, P, con_generador) == []


def test_alerta_oculta_vuelve_pasados_los_dias():
    ext = {(2, EXT): res(*[True] * 6)}
    oculta = foto(extension=ext, ocultas={(2, EXT, ALERTA_EXCELENCIA): AHORA - timedelta(days=3)})
    assert calc.alertas(oculta, AHORA, P, con_generador) == []
    assert calc.alertas(oculta, AHORA, P, con_generador, incluir_ocultas=True)[0]["oculta"] is True
    vieja = foto(extension=ext, ocultas={(2, EXT, ALERTA_EXCELENCIA): AHORA - timedelta(days=20)})
    assert len(calc.alertas(vieja, AHORA, P, con_generador)) == 1


# ─── Periodo y plan (puros) ──────────────────────────────────────────────────

T = [Periodo(1, date(2026, 3, 2), date(2026, 5, 29)), Periodo(2, date(2026, 6, 8), date(2026, 9, 4)),
     Periodo(3, date(2026, 9, 14), date(2026, 12, 11))]


def test_trimestre_vigente_y_vacaciones():
    assert calc.trimestre_vigente(T, date(2026, 2, 20)) is None
    assert calc.trimestre_vigente(T, date(2026, 4, 1)) == 1
    assert calc.trimestre_vigente(T, date(2026, 6, 3)) == 1          # vacaciones: sigue el T1
    assert calc.trimestre_vigente(T, date(2026, 11, 13)) == 3


def test_cambios_del_plan_respetan_el_ajuste_manual():
    plan = {L1: {1}, L2: {2, 3}, L3: {2}}
    habs = {L1: (True, False), L2: (False, False), L3: (False, True)}   # L3 ajustada a mano
    assert calc.cambios_del_plan(plan, habs, 2) == [(L1, False), (L2, True)]
    assert calc.cambios_del_plan(plan, habs, None) == []
    assert calc.cambios_del_plan(plan, {}, 1) == [(L1, True)]


def test_tabla_del_periodo():
    f = foto(2, resultados={(1, L2): res(True, False, dias_atras=200) + res(True, True, dias_atras=5)})
    t3 = calc.tabla_del_periodo(f, T[2], [(1, L2, AHORA - timedelta(days=4)), (2, L2, AHORA - timedelta(days=300))], P)
    [fila] = t3
    assert (fila["leccion_id"], fila["dominaron"], fila["practicaron"], fila["problemas"], fila["precision"]) == (L2, [1], 1, 2, 1.0)


def test_errores_frecuentes_con_nombre_para_docentes():
    descripciones = descripciones_de_errores()
    menos = descripciones["naturales.suma.conto_uno_menos"]
    assert menos.startswith("Contó uno de menos")
    errores = calc.errores_frecuentes(
        ["naturales.suma.conto_uno_menos"] * 3 + ["no_clasificado", "naturales.suma.resto"], descripciones)
    assert [(e["descripcion"], e["veces"]) for e in errores] == [
        (menos, 3), ("Otro error (sin clasificar)", 1), ("Restó en vez de sumar", 1)]
    assert errores[0]["camino"] == "naturales.suma" and errores[1]["camino"] is None


# ─── Con la base ─────────────────────────────────────────────────────────────

async def _estudiantes(db, org_id, n):
    ests = []
    for _ in range(n):
        e = Estudiante(codigo_estudiante=f"SEG{next(_n)}", password_hash="x", tipo_usuario="estudiante",
                       nombre_completo=f"Estudiante {next(_n)}", organizacion_id=org_id)
        db.add(e)
        ests.append(e)
    await db.flush()
    return ests


async def _practica(db, est_id, anio_id, lec, aciertos, *, zona=ZONA_NORMAL, fecha=AHORA, error=None):
    s = NucleoSesion(estudiante_id=est_id, anio_lectivo_id=anio_id, estado=SESION_COMPLETADA, plan=[],
                     cantidad_problemas=len(aciertos), progreso=len(aciertos), fecha_inicio=fecha, fecha_fin=fecha)
    db.add(s)
    await db.flush()
    for i, a in enumerate(aciertos):
        ps = NucleoProblemaSesion(sesion_id=s.id, estudiante_id=est_id, orden=i, leccion_id=lec, zona=zona, problema={},
                                  estado=PROBLEMA_TERMINADO, intentos=1, correcto=a, acierto=a,
                                  fecha_creacion=fecha, fecha_fin=fecha + timedelta(seconds=i))
        db.add(ps)
        await db.flush()
        if not a and error:
            db.add(NucleoIntento(problema_sesion_id=ps.id, estudiante_id=est_id, numero=1, respuestas={}, correcto=False,
                                 errores={"resultado": error}, tiempo_ms=1000, modo_respuesta="banco", fecha=fecha))
    await db.flush()
    return s


async def _salon_con_practica(db, n):
    await cargar_programa(db, leer_programa())
    org = await crear_organizacion(db)
    ests = await _estudiantes(db, org.id, n)
    prof, al = await salon_con_estudiantes(db, [e.id for e in ests], organizacion_id=org.id)
    hab = ServicioHabilitacion(db)
    for lec in (L1, L2):
        await hab.habilitar(al.id, prof.id, lec)
    for e in ests:
        db.add(NucleoDominio(estudiante_id=e.id, leccion_id=L1, estado=DOMINIO_EN_PROGRESO, fecha_inicio=AHORA,
                             ultima_practica=AHORA))
        await _practica(db, e.id, al.id, L1, [True, False, False])
        await _practica(db, e.id, al.id, EXT, [True], zona=ZONA_EXTENSION)
    return prof, al, ests


async def _contar_consultas(coro_factory) -> int:
    contador = {"n": 0}

    def contar(*_):
        contador["n"] += 1
    event.listen(test_engine.sync_engine, "before_cursor_execute", contar)
    try:
        await coro_factory()
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", contar)
    return contador["n"]


@pytest.mark.db
@pytest.mark.asyncio
async def test_la_tabla_hace_las_mismas_consultas_con_3_o_25_estudiantes():
    cuentas = []
    for n in (3, 25):
        async with TestSessionLocal() as db:
            prof, al, _ = await _salon_con_practica(db, n)
            serv = ServicioSeguimiento(db, P, reloj=lambda: AHORA)
            await serv.seguimiento(al.id, prof.id)        # calienta (trimestres por defecto, etc.)
            cuentas.append(await _contar_consultas(lambda: serv.seguimiento(al.id, prof.id)))
            r = await serv.seguimiento(al.id, prof.id)
            assert r["por_leccion"][0]["conteos"][EN_PROGRESO] == n
            await db.rollback()
    assert cuentas[0] == cuentas[1] and cuentas[0] <= 20, cuentas   # 7b: +3 por "diagnóstico pendiente"


@pytest.mark.db
@pytest.mark.asyncio
async def test_alerta_de_dificultad_y_asignar_desde_ella():
    async with TestSessionLocal() as db:
        prof, al, ests = await _salon_con_practica(db, 3)
        est = ests[0]
        # L2 va mal, y ya tuvo 4 problemas de refuerzo de L1 que también fallan
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=L2, estado=DOMINIO_EN_PROGRESO, fecha_inicio=AHORA))
        await _practica(db, est.id, al.id, L2, MAL)
        await _practica(db, est.id, al.id, L1, [False] * 4, zona=ZONA_REFUERZO, fecha=AHORA - timedelta(days=2))
        await ServicioHabilitacion(db).deshabilitar(al.id, prof.id, L1)   # para poder asignarla
        serv = ServicioSeguimiento(db, P, reloj=lambda: AHORA)
        [a] = [x for x in await serv.alertas(al.id, prof.id) if x["tipo"] == ALERTA_DIFICULTAD]
        assert (a["estudiante_id"], a["leccion_id"], a["motivo"]) == (est.id, L2, MOTIVO_REFUERZO)
        assert a["sugerencia"]["leccion_id"] == L1 and a["prerrequisito_asignado"] is False
        await ServicioHabilitacion(db).asignar(al.id, prof.id, est.id, L1)
        restantes = await serv.alertas(al.id, prof.id)
        [a] = [x for x in restantes if x["tipo"] == ALERTA_DIFICULTAD]
        assert a["sugerencia"] is None and a["prerrequisito_asignado"] is True
        # Ocultar la esconde
        await serv.ocultar(al.id, prof.id, est.id, L2, ALERTA_DIFICULTAD)
        assert not [x for x in await serv.alertas(al.id, prof.id) if x["leccion_id"] == L2]


@pytest.mark.db
@pytest.mark.asyncio
async def test_plan_por_trimestre_no_pisa_el_ajuste_manual():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        prof, al = await salon_con_estudiantes(db, [], anio=2026)
        reloj = {"ahora": datetime(2026, 4, 1, 15)}                     # T1
        plan = ServicioPlan(db, P, reloj=lambda: reloj["ahora"])
        await plan.guardar(al.id, prof.id, {L1: [1], L2: [2, 3], L3: [2]})

        async def habilitadas():
            return {h.leccion_id for h in (await db.execute(select(NucleoHabilitacion).where(
                NucleoHabilitacion.anio_lectivo_id == al.id))).scalars() if h.habilitada}
        assert await habilitadas() == {L1}

        # El profesor deshabilita L3 a mano en el T1 y habilita L1… ya estaba; cambia al T2
        hab = ServicioHabilitacion(db)
        await hab.habilitar(al.id, prof.id, L3)
        await hab.deshabilitar(al.id, prof.id, L3)
        reloj["ahora"] = datetime(2026, 6, 20, 15)                       # T2
        cambios = await plan.aplicar(al.id)
        assert sorted(cambios) == [(L1, False), (L2, True)]
        assert await habilitadas() == {L2}                              # L3 no: tiene ajuste manual
        assert await plan.aplicar(al.id) == []                          # idempotente

        resumen = await plan.devolver_al_plan(al.id, prof.id, L3)
        assert resumen["vigente"] == 2 and await habilitadas() == {L2, L3}

        # El estudiante también lo aplica al entrar (T3: L3 sale, L2 sigue)
        reloj["ahora"] = datetime(2026, 10, 1, 15)
        est = (await _estudiantes(db, prof.organizacion_id, 1))[0]
        db.add(Matricula(anio_lectivo_id=al.id, estudiante_id=est.id, estado="activa"))
        await db.flush()
        await ServicioPractica(db, P, reloj=lambda: reloj["ahora"]).estado(est.id)
        assert await habilitadas() == {L2}

        # Catálogo: muestra el plan y el ajuste manual
        await hab.deshabilitar(al.id, prof.id, L2)
        cat = {x["id"]: x for x in await hab.catalogo(al.id, prof.id)}
        assert cat[L2]["plan_trimestres"] == [2, 3] and cat[L2]["ajuste_manual"] is True


@pytest.mark.db
@pytest.mark.asyncio
async def test_ficha_errores_caminos_y_anios_anteriores():
    async with TestSessionLocal() as db:
        prof, al, ests = await _salon_con_practica(db, 2)
        est = ests[0]
        await _practica(db, est.id, al.id, L2, [False, False, True], error="naturales.resta.sumo")
        # Año anterior cerrado, en otro salón, con una lección dominada
        _, viejo = await salon_con_estudiantes(db, [], profesor=prof, anio=2025, nombre="K-B")
        viejo.estado = ANIO_CERRADO
        db.add(Matricula(anio_lectivo_id=viejo.id, estudiante_id=est.id, estado=MATRICULA_CERRADA))
        s = await _practica(db, est.id, viejo.id, L1, [True, True], fecha=datetime(2025, 8, 1))
        ps = (await db.execute(select(NucleoProblemaSesion).where(NucleoProblemaSesion.sesion_id == s.id))).scalars().first()
        db.add(NucleoExperiencia(estudiante_id=est.id, tipo=XP_LECCION_DOMINADA, cantidad=50, leccion_id=L1,
                                 problema_sesion_id=ps.id, primera_vez=True, fecha=datetime(2025, 8, 1)))
        await db.flush()

        serv = ServicioSeguimiento(db, P, reloj=lambda: AHORA)
        ficha = await serv.ficha(al.id, prof.id, est.id)
        assert ficha["estudiante"]["id"] == est.id and ficha["salon"]["anio_lectivo_id"] == al.id
        assert [e["descripcion"] for e in ficha["errores"]][:1] == [descripciones_de_errores()["naturales.resta.sumo"]]
        assert {c["camino"] for c in ficha["por_camino"]} >= {"naturales.suma", "naturales.resta"}
        lecs = {x["leccion_id"]: x for x in ficha["lecciones"]}
        assert lecs[L1]["estado"] == EN_PROGRESO and lecs[EXT]["extension_problemas"] == 1
        [previo] = ficha["anios_anteriores"]
        assert (previo["salon"], previo["anio"], previo["problemas"], previo["lecciones_dominadas"]) == ("K-B", 2025, 2, 1)
        assert len(ficha["sesiones"]) >= 2

        # Corte por trimestre: en el T1 no hubo práctica
        t1 = await serv.ficha(al.id, prof.id, est.id, trimestre=1)
        assert t1["errores"] == [] and all(x["problemas_periodo"] == 0 for x in t1["lecciones"])
        with pytest.raises(NoEncontrado):
            await serv.ficha(al.id, prof.id, ests[1].id + 999)


@pytest.mark.db
@pytest.mark.asyncio
async def test_permisos_de_las_rutas_de_seguimiento():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        await db.commit()

    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, HP = await _profesor(c, org)
        _, HP2 = await _profesor(c, org)
        est_id, HE = await _estudiante(c, org)
        otro_id, _ = await _estudiante(c, org)
        al = (await _salon(c, HP))["anio_lectivo_id"]
        assert (await c.post(f"/api/teachers/salones/{al}/estudiantes/{est_id}", headers=HP)).status_code == 204
        base = f"/api/nucleo/anios/{al}"

        r = await c.get(f"{base}/seguimiento", headers=HP)
        assert r.status_code == 200 and r.json()["estudiantes"][0]["id"] == est_id
        assert (await c.get(f"{base}/seguimiento?trimestre=2", headers=HP)).json()["periodo"]["numero"] == 2
        assert (await c.get(f"{base}/seguimiento?trimestre=4", headers=HP)).status_code == 422
        for url in (f"{base}/seguimiento", f"{base}/alertas", f"{base}/plan", f"{base}/estudiantes/{est_id}/ficha"):
            assert (await c.get(url, headers=HP2)).status_code == 404, url
            assert (await c.get(url, headers=HE)).status_code == 403, url
        assert (await c.get(f"{base}/estudiantes/{otro_id}/ficha", headers=HP)).status_code == 404
        assert (await c.get("/api/nucleo/alertas", headers=HP)).json() == []

        r = await c.put(f"{base}/plan", headers=HP, json={"plan": {L1: [1, 2, 3]}})
        assert r.status_code == 200 and r.json()["plan"] == {L1: [1, 2, 3]}
        assert (await c.put(f"{base}/plan", headers=HP, json={"plan": {L1: [4]}})).status_code == 409
        assert (await c.put(f"{base}/plan", headers=HP2, json={"plan": {}})).status_code == 404
        r = await c.post(f"{base}/alertas/ocultar", headers=HP, json={"estudiante_id": est_id, "leccion_id": L1, "tipo": "dificultad"})
        assert r.status_code == 204
        assert (await c.post(f"{base}/alertas/ocultar", headers=HP2,
                             json={"estudiante_id": est_id, "leccion_id": L1, "tipo": "dificultad"})).status_code == 404

        async with TestSessionLocal() as db:
            (await db.get(AnioLectivo, al)).estado = ANIO_CERRADO
            await db.commit()
        assert (await c.get(f"{base}/seguimiento", headers=HP)).status_code == 200
        r = await c.put(f"{base}/plan", headers=HP, json={"plan": {}})
        assert (r.status_code, r.json()["codigo"]) == (409, "ANIO_CERRADO")
        assert (await c.delete(f"{base}/plan/manual/{L1}", headers=HP)).status_code == 409
