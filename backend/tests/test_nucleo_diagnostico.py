"""
Diagnóstico inicial del núcleo (fase 7a).

- Algoritmo (sin base): el grafo real de 1.º con sus 21 lecciones; acierta todo, falla todo,
  mezcla, desempate, topes, prerrequisitos editados, cierre por lecciones no candidatas, sin
  lecciones y retomar a mitad.
- Servicio (con base): cuándo se hace solo, pantalla sin pistas ni corrección, retomar, resultado
  provisional, provisional confirmado y retirado por la práctica, el reparto desbloquea con el
  provisional, lo que ve el profesor (ficha, avance) y sus acciones (repetir, cerrar, cancelar).
"""

import random
from datetime import datetime
from itertools import count

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.nucleo import (
    DIAGNOSTICO_CANCELADO,
    DIAGNOSTICO_CERRADO,
    DIAGNOSTICO_EN_CURSO,
    DIAGNOSTICO_TERMINADO,
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    SESION_COMPLETADA,
    SESION_DIAGNOSTICO,
    SESION_PRACTICA,
    ZONA_DIAGNOSTICO,
    ZONA_REPASO,
    NucleoDiagnostico,
    NucleoDominio,
    NucleoProblemaSesion,
)
from app.models.user import Estudiante
from app.nucleo import diagnostico as alg
from app.nucleo.diagnostico import Respuesta, calcular
from app.nucleo.dominio import EstadoDominio
from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.reparto import Candidata, Grafo, repartir
from app.nucleo.seguimiento import DOMINADO, EN_PROGRESO, POR_CONFIRMAR, estado_visible
from app.nucleo.servicios import Prohibido
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.practica import ServicioPractica
from app.nucleo.servicios.seguimiento import ServicioSeguimiento
from app.services.curriculo_service import cargar_programa, leer_programa
from app.services.school_service import Conflicto
from tests.conftest import TestSessionLocal
from tests.salones_helpers import crear_organizacion, salon_con_estudiantes
from tests.test_nucleo_practica import Reloj, respuesta_bien, respuesta_mal
from tests.test_organizacion_escolar import _estudiante, _org, _profesor, _salon

P = ParametrosNucleo()

# ─── El grafo de 1.º (21 lecciones con generador) ────────────────────────────

GRAFO_1 = {
    "g1-u02-l01": (), "g1-u02-l02": ("g1-u02-l01",),
    "g1-u03-l01": ("g1-u02-l01",), "g1-u03-l02": ("g1-u03-l01",), "g1-u03-l03": ("g1-u03-l02",),
    "g1-u04-l01": ("g1-u02-l01",), "g1-u04-l02": ("g1-u04-l01",), "g1-u04-l03": ("g1-u04-l01",),
    "g1-u05-l01": ("g1-u03-l01", "g1-u04-l01"), "g1-u05-l02": ("g1-u02-l02", "g1-u05-l01"),
    "g1-u05-l03": ("g1-u03-l02", "g1-u05-l01"), "g1-u05-l04": ("g1-u03-l03", "g1-u05-l02", "g1-u05-l03"),
    "g1-u05-l05": ("g1-u04-l02", "g1-u05-l03"),
    "g1-u06-l01": ("g1-u04-l01",), "g1-u06-l02": ("g1-u06-l01",), "g1-u06-l03": ("g1-u06-l02",),
    "g1-u06-l04": ("g1-u04-l02", "g1-u06-l02"), "g1-u06-l05": ("g1-u06-l03",),
    "g1-u07-l01": ("g1-u05-l01", "g1-u06-l03"), "g1-u07-l02": ("g1-u05-l03", "g1-u07-l01"),
    "g1-u07-l03": ("g1-u06-l04", "g1-u07-l02"),
}
LECCIONES_1 = sorted(GRAFO_1)
G1 = Grafo(GRAFO_1, {lec: i for i, lec in enumerate(LECCIONES_1)})


def c(corto: str) -> str:
    """"U7L3" → "g1-u07-l03"."""
    return f"g1-u0{corto[1]}-l0{corto[3]}"


def recorrer(sabe, *, lecciones=LECCIONES_1, conocidas=frozenset(), grafo=G1, p=P, ms=30_000):
    """Responde como un estudiante que sabe las lecciones de `sabe` hasta que el diagnóstico termina."""
    respuestas: list[Respuesta] = []
    probadas: list[str] = []
    while True:
        estado = calcular(lecciones, set(conocidas), grafo, respuestas, p)
        if estado.terminado:
            return estado, probadas
        if not probadas or probadas[-1] != estado.siguiente:
            probadas.append(estado.siguiente)
        respuestas.append(Respuesta(estado.siguiente, sabe(estado.siguiente), ms))


def sabidas(estado) -> set[str]:
    return set(estado.sabidas)


# ─── Algoritmo ───────────────────────────────────────────────────────────────

def test_acierta_todo_en_10_problemas():
    estado, probadas = recorrer(lambda lec: True)
    assert probadas == [c("U7L3"), c("U6L5"), c("U5L5"), c("U5L4"), c("U4L3")]
    assert (estado.problemas, estado.motivo_fin) == (10, alg.FIN_COMPLETO)
    assert sabidas(estado) == set(LECCIONES_1)
    origen = {f["leccion_id"]: f["origen"] for f in estado.resultado()}
    assert origen[c("U7L3")] == alg.PROBADA and origen[c("U2L1")] == alg.INFERIDA


def test_falla_todo_retrocede_por_la_mitad():
    estado, probadas = recorrer(lambda lec: False)
    assert probadas == [c("U7L3"), c("U6L2"), c("U4L1"), c("U2L1")]
    assert (estado.problemas, estado.motivo_fin) == (8, alg.FIN_COMPLETO)
    assert sabidas(estado) == set()


def test_mezcla_llega_al_tope_y_deja_lecciones_sin_decidir():
    sabe = {c(x) for x in ("U2L1", "U2L2", "U3L1", "U3L2", "U3L3", "U4L1", "U4L2", "U4L3", "U5L1", "U6L1", "U6L2")}
    estado, probadas = recorrer(lambda lec: lec in sabe)
    assert probadas == [c(x) for x in ("U7L3", "U6L2", "U7L1", "U6L3", "U6L4", "U4L2", "U5L5", "U5L1")]
    assert (estado.problemas, estado.motivo_fin) == (16, alg.FIN_TOPE_PROBLEMAS)
    assert sabidas(estado) == {c(x) for x in ("U2L1", "U3L1", "U4L1", "U4L2", "U5L1", "U6L1", "U6L2")}
    assert len(estado.sin_decidir) == 7
    assert sabidas(estado) <= sabe                       # nunca da por sabida una que no sabe


def test_desempate_con_un_tercer_problema():
    respuestas = [Respuesta(c("U7L3"), True), Respuesta(c("U7L3"), False)]
    estado = calcular(LECCIONES_1, set(), G1, respuestas, P)
    assert not estado.terminado and estado.siguiente == c("U7L3")       # falta el desempate
    sabida = calcular(LECCIONES_1, set(), G1, respuestas + [Respuesta(c("U7L3"), True)], P)
    assert sabida.decisiones[c("U7L3")] == alg.Decision(alg.SABIDA, alg.PROBADA, 2, 3)
    no_sabida = calcular(LECCIONES_1, set(), G1, respuestas + [Respuesta(c("U7L3"), False)], P)
    assert no_sabida.decisiones[c("U7L3")].decision == alg.NO_SABIDA
    # Sin desempate configurado, una mezcla cuenta como no sabida
    p = ParametrosNucleo(diagnostico_problemas_desempate=0)
    assert calcular(LECCIONES_1, set(), G1, respuestas, p).decisiones[c("U7L3")].decision == alg.NO_SABIDA


def test_tope_de_tiempo_activo():
    estado, probadas = recorrer(lambda lec: lec != c("U7L3"), ms=4 * 60_000)    # 4 min por problema
    assert estado.motivo_fin == alg.FIN_TOPE_TIEMPO and estado.problemas == 3
    assert len(probadas) == 2


def test_los_valores_son_parametros():
    p = ParametrosNucleo(diagnostico_problemas_por_leccion=1, diagnostico_max_problemas=3)
    estado, probadas = recorrer(lambda lec: False, p=p)
    assert estado.problemas == 3 and estado.motivo_fin == alg.FIN_TOPE_PROBLEMAS


def test_prerrequisitos_editados_por_el_profesor():
    # Si U7L3 ya no depende de nada, saberla no dice nada de las demás
    editado = Grafo({**GRAFO_1, c("U7L3"): ()}, G1.orden)
    estado, probadas = recorrer(lambda lec: True, grafo=editado)
    assert probadas[:2] == [c("U7L3"), c("U7L2")]
    assert estado.decisiones[c("U7L2")].origen == alg.PROBADA


def test_el_cierre_pasa_por_lecciones_no_candidatas():
    # Solo U2L1 y U5L1 habilitadas: saber U5L1 implica U2L1 (por U3L1 y U4L1, que no están)
    estado, probadas = recorrer(lambda lec: True, lecciones=[c("U2L1"), c("U5L1")])
    assert probadas == [c("U5L1")] and sabidas(estado) == {c("U2L1"), c("U5L1")}


def test_lo_ya_dominado_no_se_prueba():
    conocidas = set(LECCIONES_1) - {c("U7L3")}
    estado, probadas = recorrer(lambda lec: False, conocidas=conocidas)
    assert probadas == [c("U7L3")] and estado.problemas == 2
    assert estado.decisiones[c("U2L1")].origen == alg.PREVIA


def test_sin_lecciones_no_hay_diagnostico():
    estado = calcular([], set(), G1, [], P)
    assert estado.terminado and estado.motivo_fin == alg.FIN_SIN_LECCIONES


def test_retomar_a_mitad_da_el_mismo_recorrido():
    """El estado sale de repetir las respuestas: cortar y seguir otro día no cambia nada."""
    sabe = {c("U2L1"), c("U4L1"), c("U6L1")}
    completo, _ = recorrer(lambda lec: lec in sabe)
    respuestas = []
    for _ in range(5):
        e = calcular(LECCIONES_1, set(), G1, respuestas, P)
        respuestas.append(Respuesta(e.siguiente, e.siguiente in sabe, 30_000))
    retomado = calcular(LECCIONES_1, set(), G1, list(respuestas), P)
    while not retomado.terminado:
        respuestas.append(Respuesta(retomado.siguiente, retomado.siguiente in sabe, 30_000))
        retomado = calcular(LECCIONES_1, set(), G1, respuestas, P)
    assert retomado.resultado() == completo.resultado()


def test_el_avance_no_retrocede():
    respuestas, anterior = [], 0.0
    while not (e := calcular(LECCIONES_1, set(), G1, respuestas, P)).terminado:
        assert e.avance(P) >= anterior
        anterior = e.avance(P)
        respuestas.append(Respuesta(e.siguiente, False))
    assert e.avance(P) == 1.0


# ─── Reparto y seguimiento con el provisional ────────────────────────────────

def test_el_provisional_desbloquea_lecciones_nuevas_y_va_al_repaso():
    grafo = Grafo({"a": (), "b": ("a",)}, {"a": 1, "b": 2})
    cands = [Candidata("a", 1, DOMINIO_PROVISIONAL, repaso_pendiente=True), Candidata("b", 2)]
    plan = repartir(cands, [], [], grafo, P, random.Random(1))
    assert {(it.leccion_id, it.zona) for it in plan} == {("b", "normal"), ("a", ZONA_REPASO)}


def test_la_prioritaria_provisional_cede_su_espacio():
    grafo = Grafo({"a": (), "b": ()}, {"a": 1, "b": 2})
    cands = [Candidata("a", 1, DOMINIO_PROVISIONAL, prioritaria=True, repaso_pendiente=True),
             Candidata("b", 2, DOMINIO_EN_PROGRESO)]
    plan = repartir(cands, [], [], grafo, P, random.Random(1))
    assert all(it.zona != "prioridad" for it in plan)


def test_el_profesor_ve_el_provisional_como_por_confirmar():
    ahora = datetime(2026, 11, 14, 15)
    assert estado_visible(EstadoDominio(DOMINIO_PROVISIONAL), ahora, P) == POR_CONFIRMAR
    assert estado_visible(EstadoDominio(DOMINIO_DOMINADO, ahora, ahora), ahora, P) == DOMINADO


# ─── Con la base ─────────────────────────────────────────────────────────────

U3 = [c("U3L1"), c("U3L2"), c("U3L3")]       # sumar y restar: respuestas con número
_n = count(1)


async def preparar(db, habilitar=U3, n=1):
    await cargar_programa(db, leer_programa())
    org = await crear_organizacion(db)
    ests = []
    for _ in range(n):
        e = Estudiante(codigo_estudiante=f"DIAG{next(_n)}", password_hash="x", tipo_usuario="estudiante",
                       nombre_completo=f"Estudiante Diagnóstico {next(_n)}", organizacion_id=org.id)
        db.add(e)
        ests.append(e)
    await db.flush()
    prof, al = await salon_con_estudiantes(db, [e.id for e in ests], organizacion_id=org.id, grado=1)
    for lec in habilitar:
        await ServicioHabilitacion(db).habilitar(al.id, prof.id, lec)
    return ests, prof, al


async def hacer_diagnostico(serv, est_id, sabe, *, hasta=None):
    """Responde el diagnóstico (o `hasta` problemas) como quien sabe las lecciones de `sabe`."""
    sesion = await serv.iniciar_sesion(est_id)
    assert sesion.tipo == SESION_DIAGNOSTICO
    n, ultima = 0, None
    while (hasta is None or n < hasta) and (ps := await serv.siguiente(est_id, sesion.id)) is not None:
        serv.reloj.avanzar(seconds=40)
        r = respuesta_bien(ps) if ps.leccion_id in sabe else respuesta_mal(ps)
        ultima = await serv.responder(est_id, sesion.id, ps.id, r, 30_000)
        n += 1
    return sesion, ultima


async def estados(db, est_id) -> dict[str, str]:
    return {d.leccion_id: d.estado for d in (await db.execute(
        select(NucleoDominio).where(NucleoDominio.estudiante_id == est_id))).scalars()}


@pytest.mark.db
@pytest.mark.asyncio
async def test_diagnostico_completo_y_luego_la_practica():
    async with TestSessionLocal() as db:
        [est], prof, al = await preparar(db)
        serv = ServicioPractica(db, P, random.Random(1), Reloj())
        assert (await serv.estado(est.id))["diagnostico_pendiente"] is True

        sesion = await serv.iniciar_sesion(est.id)
        ps = await serv.siguiente(est.id, sesion.id)
        assert ps.zona == ZONA_DIAGNOSTICO and ps.leccion_id == c("U3L3")
        # Sin pistas, sin descartar y sin decir si acertó
        with pytest.raises(Prohibido):
            await serv.pista(est.id, sesion.id, ps.id, 1)
        with pytest.raises(Conflicto):
            await serv.descartar(est.id, sesion.id)
        r = await serv.responder(est.id, sesion.id, ps.id, respuesta_mal(ps), 30_000)
        assert (r["correcto"], r["huecos"], r["solucion"], r["experiencia_ganada"]) == (None, {}, None, 0)
        assert r["problema_terminado"] and r["diagnostico"]["avance"] > 0

        # Sabe U3L1 y U3L2, no U3L3
        await hacer_diagnostico(serv, est.id, {c("U3L1"), c("U3L2")})
        assert await estados(db, est.id) == {c("U3L1"): DOMINIO_PROVISIONAL, c("U3L2"): DOMINIO_PROVISIONAL}
        diag = (await db.execute(select(NucleoDiagnostico))).scalar_one()
        assert diag.estado == DIAGNOSTICO_TERMINADO and diag.motivo_fin == alg.FIN_COMPLETO
        assert (await db.get(type(sesion), sesion.id)).estado == SESION_COMPLETADA
        # Los problemas del diagnóstico no cuentan para el dominio
        assert await serv.resultados(est.id) == {}

        # Después, la práctica normal: U3L3 nueva (la desbloquea el provisional) y repaso de los provisionales
        assert (await serv.estado(est.id))["diagnostico_pendiente"] is False
        practica = await serv.iniciar_sesion(est.id)
        assert practica.tipo == SESION_PRACTICA
        zonas = {(it["leccion_id"], it["zona"]) for it in practica.plan}
        assert (c("U3L3"), "normal") in zonas and (c("U3L1"), ZONA_REPASO) in zonas


@pytest.mark.db
@pytest.mark.asyncio
async def test_salir_a_mitad_y_retomar():
    async with TestSessionLocal() as db:
        [est], _, _ = await preparar(db)
        reloj = Reloj()
        serv = ServicioPractica(db, P, random.Random(2), reloj)
        sesion, _ = await hacer_diagnostico(serv, est.id, set(U3), hasta=1)
        pendiente = await serv.siguiente(est.id, sesion.id)          # quedó un problema a la vista

        # Vuelve otro día con otro servicio (otra petición): la misma sesión y el mismo problema
        reloj.avanzar(days=1)
        otra = ServicioPractica(db, P, random.Random(9), reloj)
        estado = await otra.estado(est.id)
        assert estado["diagnostico_pendiente"] and estado["sesion_activa"]["tipo"] == SESION_DIAGNOSTICO
        assert (await otra.iniciar_sesion(est.id)).id == sesion.id
        assert (await otra.siguiente(est.id, sesion.id)).id == pendiente.id
        await hacer_diagnostico(otra, est.id, set(U3))
        assert set((await estados(db, est.id)).values()) == {DOMINIO_PROVISIONAL}


@pytest.mark.db
@pytest.mark.asyncio
async def test_no_se_hace_solo_si_ya_practico_o_sin_lecciones():
    async with TestSessionLocal() as db:
        [sin_lecciones], _, _ = await preparar(db, habilitar=())
        serv = ServicioPractica(db, P, random.Random(3), Reloj())
        assert (await serv.estado(sin_lecciones.id))["diagnostico_pendiente"] is False
        assert (await db.execute(select(NucleoDiagnostico))).first() is None

        # Con el diagnóstico desactivado, va directo a practicar; después ya practicó y no se le pide
        [est], _, _ = await preparar(db)
        sin_diag = ServicioPractica(db, ParametrosNucleo(diagnostico_activo=False), random.Random(3), Reloj())
        sesion = await sin_diag.iniciar_sesion(est.id)
        assert sesion.tipo == SESION_PRACTICA
        ps = await sin_diag.siguiente(est.id, sesion.id)
        await sin_diag.responder(est.id, sesion.id, ps.id, respuesta_bien(ps), 1000)
        await sin_diag.descartar(est.id, sesion.id)
        assert (await serv.estado(est.id))["diagnostico_pendiente"] is False
        assert (await serv.iniciar_sesion(est.id)).tipo == SESION_PRACTICA


@pytest.mark.db
@pytest.mark.asyncio
async def test_provisional_confirmado_y_retirado_por_la_practica():
    async with TestSessionLocal() as db:
        [est], prof, al = await preparar(db, habilitar=[c("U3L1"), c("U3L2")])
        reloj = Reloj()
        serv = ServicioPractica(db, P, random.Random(4), reloj)
        await hacer_diagnostico(serv, est.id, {c("U3L1"), c("U3L2")})
        assert set((await estados(db, est.id)).values()) == {DOMINIO_PROVISIONAL}

        # Practica: U3L1 siempre bien (se confirma en dos días); U3L2 siempre mal (se retira a los 5)
        for _ in range(4):
            sesion = await serv.iniciar_sesion(est.id)
            while (ps := await serv.siguiente(est.id, sesion.id)) is not None:
                reloj.avanzar(minutes=1)
                bien = ps.leccion_id == c("U3L1")
                r = await serv.responder(est.id, sesion.id, ps.id, respuesta_bien(ps) if bien else respuesta_mal(ps), 1000)
                while not r["problema_terminado"]:
                    r = await serv.responder(est.id, sesion.id, ps.id, respuesta_mal(ps), 1000)
            reloj.avanzar(days=1)
        assert await estados(db, est.id) == {c("U3L1"): DOMINIO_DOMINADO, c("U3L2"): DOMINIO_EN_PROGRESO}

        ficha = await ServicioSeguimiento(db, P, reloj).ficha(al.id, prof.id, est.id)
        seguimiento = {f["leccion_id"]: f["seguimiento"] for f in ficha["diagnostico"]["lecciones"]}
        assert seguimiento == {c("U3L1"): "confirmado", c("U3L2"): "retirado"}
        # Retirado no tiene marca propia: en el avance sale como "en progreso"
        tabla = await ServicioSeguimiento(db, P, reloj).seguimiento(al.id, prof.id)
        u3l2 = next(f for f in tabla["por_leccion"] if f["leccion_id"] == c("U3L2"))
        assert u3l2["estudiantes"][EN_PROGRESO] == [est.id]


@pytest.mark.db
@pytest.mark.asyncio
async def test_el_profesor_ve_el_resultado_y_puede_repetir_cerrar_o_cancelar():
    async with TestSessionLocal() as db:
        [est, otro], prof, al = await preparar(db, n=2)
        reloj = Reloj()
        serv = ServicioPractica(db, P, random.Random(5), reloj)
        seg = ServicioSeguimiento(db, P, reloj)
        await hacer_diagnostico(serv, est.id, {c("U3L1")})

        # Avance: "por confirmar" aparte de "dominan"; el otro, con el diagnóstico pendiente
        await serv.iniciar_sesion(otro.id)
        tabla = await seg.seguimiento(al.id, prof.id)
        u3l1 = next(f for f in tabla["por_leccion"] if f["leccion_id"] == c("U3L1"))
        assert u3l1["conteos"][POR_CONFIRMAR] == 1 and u3l1["dominan"] == 0
        assert tabla["diagnosticos"] == {str(otro.id): DIAGNOSTICO_EN_CURSO}

        # Ficha: probadas e inferidas
        ficha = await seg.ficha(al.id, prof.id, est.id)
        d = {f["leccion_id"]: f for f in ficha["diagnostico"]["lecciones"]}
        assert d[c("U3L1")]["decision"] == alg.SABIDA and d[c("U3L1")]["seguimiento"] == "por_confirmar"
        assert d[c("U3L2")]["decision"] == alg.NO_SABIDA
        assert ficha["diagnostico"]["problemas"] > 0 and ficha["sesiones"][0]["tipo"] == SESION_DIAGNOSTICO
        assert ficha["errores"] == []          # los errores del diagnóstico no van a "errores frecuentes"

        # Cerrar con lo obtenido al que lo dejó a mitad: queda lo decidido, el resto sin decidir
        sesion_otro = (await serv.sesion_activa(otro.id)).id
        for bien in (False, False, True, False):          # U3L3 mal, mal; U3L2 bien, mal (falta el desempate)
            ps = await serv.siguiente(otro.id, sesion_otro)
            await serv.responder(otro.id, sesion_otro, ps.id, respuesta_bien(ps) if bien else respuesta_mal(ps), 30_000)
        cerrado = await seg.diagnostico(al.id, prof.id, otro.id, "cerrar")
        decision = {f["leccion_id"]: f["decision"] for f in cerrado["lecciones"]}
        assert cerrado["estado"] == DIAGNOSTICO_CERRADO and cerrado["problemas"] == 4
        assert decision == {c("U3L1"): alg.SIN_DECIDIR, c("U3L2"): alg.SIN_DECIDIR, c("U3L3"): alg.NO_SABIDA}
        assert await estados(db, otro.id) == {}
        assert await serv.sesion_activa(otro.id) is None
        with pytest.raises(Conflicto):
            await seg.diagnostico(al.id, prof.id, otro.id, "cerrar")

        # Repetir: se hace al volver a entrar; lo confirmado no se prueba
        await seg.diagnostico(al.id, prof.id, est.id, "pedir")
        with pytest.raises(Conflicto):
            await seg.diagnostico(al.id, prof.id, est.id, "pedir")
        assert (await serv.estado(est.id))["diagnostico_pendiente"] is True
        cancelado = await seg.diagnostico(al.id, prof.id, est.id, "cancelar")
        assert cancelado["estado"] == DIAGNOSTICO_CANCELADO
        assert (await serv.iniciar_sesion(est.id)).tipo == SESION_PRACTICA


@pytest.mark.db
@pytest.mark.asyncio
async def test_repetir_no_prueba_lo_confirmado_y_retira_provisionales_no_sabidos():
    async with TestSessionLocal() as db:
        [est], prof, al = await preparar(db)
        reloj = Reloj()
        serv = ServicioPractica(db, P, random.Random(6), reloj)
        await hacer_diagnostico(serv, est.id, set(U3))
        # U3L1 confirmada a mano; U3L2 y U3L3 siguen provisionales
        (await db.get(NucleoDominio, (est.id, c("U3L1")))).estado = DOMINIO_DOMINADO
        await ServicioSeguimiento(db, P, reloj).diagnostico(al.id, prof.id, est.id, "pedir")
        await hacer_diagnostico(serv, est.id, set())          # ahora falla todo
        probadas = set((await db.execute(
            select(NucleoProblemaSesion.leccion_id).where(NucleoProblemaSesion.zona == ZONA_DIAGNOSTICO)
            .where(NucleoProblemaSesion.sesion_id == (await db.execute(
                select(NucleoDiagnostico.sesion_id).where(NucleoDiagnostico.origen == "profesor"))).scalar_one())
        )).scalars())
        assert c("U3L1") not in probadas
        assert await estados(db, est.id) == {c("U3L1"): DOMINIO_DOMINADO}     # sin práctica: vuelven a sin empezar


@pytest.mark.db
@pytest.mark.asyncio
async def test_api_del_diagnostico_y_permisos():
    async with TestSessionLocal() as db:
        await cargar_programa(db, leer_programa())
        await db.commit()
    async with AsyncClient(app=app, base_url="http://test") as cl:
        org = await _org(cl)
        _, HP = await _profesor(cl, org)
        _, HP2 = await _profesor(cl, org)
        est_id, HE = await _estudiante(cl, org)
        al = (await _salon(cl, HP))["anio_lectivo_id"]
        assert (await cl.post(f"/api/teachers/salones/{al}/estudiantes/{est_id}", headers=HP)).status_code == 204
        for lec in U3:
            assert (await cl.put(f"/api/nucleo/anios/{al}/lecciones/{lec}", headers=HP, json={})).status_code == 200

        assert (await cl.get("/api/nucleo/estado", headers=HE)).json()["diagnostico_pendiente"] is True
        s = (await cl.post("/api/nucleo/sesiones", headers=HE)).json()
        assert s["tipo"] == SESION_DIAGNOSTICO
        p = (await cl.get(f"/api/nucleo/sesiones/{s['sesion_id']}/siguiente", headers=HE)).json()
        assert p["diagnostico"] and p["intentos_restantes"] == 1 and not any(p["pistas_habilitadas"].values())
        assert "respuestas" not in str(p["problema"])
        r = await cl.post(f"/api/nucleo/sesiones/{s['sesion_id']}/problemas/{p['problema_sesion_id']}/pista",
                          headers=HE, json={"nivel": 1})
        assert r.status_code == 403
        r = await cl.post(f"/api/nucleo/sesiones/{s['sesion_id']}/problemas/{p['problema_sesion_id']}/respuesta",
                          headers=HE, json={"respuestas": {}, "tiempo_ms": 1000})
        assert r.status_code in (200, 422)

        base = f"/api/nucleo/anios/{al}/estudiantes/{est_id}/diagnostico"
        assert (await cl.post(f"{base}/cerrar", headers=HE)).status_code == 403
        assert (await cl.post(f"{base}/cerrar", headers=HP2)).status_code == 404
        r = await cl.post(f"{base}/cancelar", headers=HP)
        assert r.status_code == 200 and r.json()["estado"] == DIAGNOSTICO_CANCELADO
        r = await cl.post(base, headers=HP)
        assert r.status_code == 200 and r.json()["estado"] == "pendiente" and r.json()["origen"] == "profesor"
        ficha = (await cl.get(f"/api/nucleo/anios/{al}/estudiantes/{est_id}/ficha", headers=HP)).json()
        assert ficha["diagnostico"]["estado"] == "pendiente"
        assert ficha["diagnostico"]["fecha_creacion"].endswith("Z")
