"""
Integración con el LLM: resolución de temas, validación de números en los enunciados
(variaciones y caché), lote en paralelo, reintentos y respuestas vacías de DeepSeek,
y privacidad (los nombres reales no salen en los prompts).
"""

from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.adaptive import EstadoSesion, PerfilEstudiante
from app.models.llm import EnunciadoTematico
from app.models.problem import Operacion, Problema
from app.repositories.enunciados_repository import EnunciadoTematicoRepository
from app.services.enunciados_service import EnunciadosService
from app.services.llm_service import LLMPrompts, LLMService
from app.services.stats_service import StatsService
from tests.conftest import TestSessionLocal
from tests.test_medallas_sesiones_config import _estudiante, _sesion

# ─── Temas ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre,esperado", [
    ("Piratas de los Mares", "tema-piratas"),
    ("tema-piratas", "tema-piratas"),
    ("Astronautas Galácticos", "tema-astronautas galácticos"),
    ("tema-astronautas", "tema-astronautas galácticos"),
    ("Princesas Inventoras", "tema-princesas inventoras"),
    ("Clásico", None),
    ("tema-default", None),
    ("", None),
    (None, None),
])
def test_resolver_tema_acepta_nombre_del_catalogo_e_id_de_la_tienda(nombre, esperado):
    assert LLMPrompts.resolver_tema(nombre) == esperado


def test_todos_los_temas_del_catalogo_son_narrativos():
    for nombre in ["Piratas de los Mares", "Astronautas Galácticos", "Magos de la Academia",
                   "Caballeros del Reino", "Vaqueros del Oeste", "Princesas Inventoras"]:
        assert LLMPrompts.resolver_tema(nombre) is not None, nombre


# ─── Validación de números y variaciones ─────────────────────────────────────

@pytest.mark.parametrize("texto,n1,n2,ok", [
    ("Tenía 12.5 monedas y encontró 3 más. ¿Cuántas tiene?", Decimal("12.500"), Decimal("3.000"), True),
    ("Tenía 12,5 monedas y encontró 3 más.", Decimal("12.5"), Decimal("3"), True),
    ("Tenía 12.5 monedas y encontró 4 más.", Decimal("12.5"), Decimal("3"), False),   # número cambiado
    ("Tenía 12.5 monedas.", Decimal("12.5"), Decimal("3"), False),                    # falta uno
    ("Tenía 12.5 monedas y 3 cofres y 7 barcos.", Decimal("12.5"), Decimal("3"), False),  # número extra
    ("Tenía doce monedas y tres cofres.", Decimal("12"), Decimal("3"), False),        # sin cifras
    ("Repartió 8 entre 8 amigos.", Decimal("8"), Decimal("8"), True),
])
def test_contiene_numeros_exactos(texto, n1, n2, ok):
    assert EnunciadosService.contiene_numeros_exactos(texto, n1, n2) is ok


def test_parsear_variaciones_extrae_las_lineas_y_quita_comillas():
    resp = 'VARIACION_1: "Uno 2 y 3."\nbasura\nVARIACION_2: Dos 2 y 3.\nvariacion_3:   Tres 2 y 3.  '
    assert EnunciadosService.parsear_variaciones(resp) == ["Uno 2 y 3.", "Dos 2 y 3.", "Tres 2 y 3."]


# ─── Lote de enunciados ──────────────────────────────────────────────────────

class _LLMFalso:
    """Devuelve respuestas guionizadas y cuenta las llamadas."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0

    async def generate(self, prompt, **kw):
        self.llamadas += 1
        r = self.respuestas.pop(0) if self.respuestas else self.respuestas_por_defecto
        if isinstance(r, Exception):
            raise r
        return r

    respuestas_por_defecto = "VARIACION_1: nada"


async def _problema(db, n1, n2, firma):
    p = Problema(operacion=Operacion.SUMA, numero1=Decimal(n1), numero2=Decimal(n2),
                 resultado=Decimal(n1) + Decimal(n2), nivel_dificultad=2, cantidad_decimales=1, signature=firma)
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_lote_guarda_solo_variaciones_con_los_numeros_correctos_y_usa_la_cache():
    async with TestSessionLocal() as db:
        p = await _problema(db, "2.5", "4", "llm_lote_1")
        await db.commit()
        pid = p.id
        llm = _LLMFalso([
            "VARIACION_1: Un pirata tenía 2.5 cofres y halló 4 más. ¿Cuántos tiene?\n"
            "VARIACION_2: Un pirata tenía 2.5 cofres y halló 5 más. ¿Cuántos tiene?\n"      # inválida
            "VARIACION_3: En el barco había 4 barriles y 2,5 más llegaron. ¿Cuántos hay?"
        ])
        svc = EnunciadosService(EnunciadoTematicoRepository(db), llm)

        r1 = await svc.obtener_enunciados_lote([pid, pid], "Piratas de los Mares")
        assert set(r1) == {pid}
        guardadas = (await db.execute(select(EnunciadoTematico))).scalars().all()
        assert sorted(g.variacion for g in guardadas) == [1, 2]
        assert {g.tema for g in guardadas} == {"tema-piratas"}
        assert all(EnunciadosService.contiene_numeros_exactos(g.texto, "2.5", "4") for g in guardadas)

        r2 = await svc.obtener_enunciados_lote([pid], "tema-piratas")
        assert r2[pid] in {g.texto for g in guardadas}
        assert llm.llamadas == 1   # la segunda vez salió de la caché


@pytest.mark.asyncio
async def test_si_el_modelo_cambia_los_numeros_no_se_guarda_nada():
    async with TestSessionLocal() as db:
        p = await _problema(db, "3", "5", "llm_lote_2")
        await db.commit()
        pid = p.id
        llm = _LLMFalso(["VARIACION_1: Tenía 3 y recibió 6.", "VARIACION_1: Tenía 9 y recibió 5."])
        svc = EnunciadosService(EnunciadoTematicoRepository(db), llm)
        assert await svc.obtener_enunciados_lote([pid], "Vaqueros del Oeste") == {}
        assert llm.llamadas == 2   # un reintento
        assert (await db.execute(select(EnunciadoTematico))).scalars().all() == []


@pytest.mark.asyncio
async def test_un_fallo_del_llm_no_cancela_los_demas_problemas_del_lote():
    async with TestSessionLocal() as db:
        a = await _problema(db, "1", "2", "llm_lote_3a")
        b = await _problema(db, "7", "8", "llm_lote_3b")
        await db.commit()
        llm = _LLMFalso([HTTPException(status_code=503, detail="x"),
                         "VARIACION_1: Sumó 7 y 8. ¿Cuántos?"])
        # El primero falla (503); el segundo responde bien y se guarda
        svc = EnunciadosService(EnunciadoTematicoRepository(db), llm)
        r = await svc.obtener_enunciados_lote([a.id, b.id], "Magos de la Academia")
        assert set(r) == {b.id}


@pytest.mark.asyncio
async def test_tema_no_narrativo_y_lote_vacio_no_llaman_al_llm():
    async with TestSessionLocal() as db:
        llm = _LLMFalso([])
        svc = EnunciadosService(EnunciadoTematicoRepository(db), llm)
        assert await svc.obtener_enunciados_lote([1, 2], "Clásico") == {}
        assert llm.llamadas == 0


@pytest.mark.asyncio
async def test_el_endpoint_solo_atiende_problemas_de_las_sesiones_del_estudiante(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, headers = await _estudiante(c, "LLM001")
        async with TestSessionLocal() as db:
            db.add(PerfilEstudiante(estudiante_id=est))
            propio = await _problema(db, "1", "2", "llm_ep_1")
            ajeno = await _problema(db, "3", "4", "llm_ep_2")
            db.add(_sesion(est, estado=EstadoSesion.EN_PROGRESO, problemas_ids=[propio.id]))
            await db.commit()
            propio_id, ajeno_id = propio.id, ajeno.id

        async def _gen(self, prompt, **kw):
            return "VARIACION_1: Hay 1 y 2. ¿Cuántos son?\nVARIACION_2: Suma 3 y 4. ¿Cuánto da?"

        monkeypatch.setattr(LLMService, "generate", _gen)
        r = await c.post("/api/enunciados/lote", headers=headers,
                         json={"problema_ids": [propio_id, ajeno_id], "tema": "Piratas de los Mares"})
        assert r.status_code == 200, r.text
        assert set(r.json()["enunciados"]) == {str(propio_id)}


# ─── LLMService: reintentos y respuesta vacía ────────────────────────────────

class _ClienteFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0
        self.is_closed = False

    async def post(self, url, json=None, timeout=None):
        self.llamadas += 1
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _resp(status_code, contenido="hola"):
    req = httpx.Request("POST", "https://x/chat/completions")
    return httpx.Response(status_code, request=req,
                          json={"choices": [{"message": {"content": contenido}}], "usage": {"total_tokens": 7}})


def _servicio(cliente):
    s = LLMService()
    s._client = cliente
    s.espera_reintento = 0
    return s


@pytest.mark.asyncio
async def test_generate_reintenta_un_error_transitorio_y_luego_responde():
    cliente = _ClienteFalso([_resp(503), _resp(200, "ok")])
    assert await _servicio(cliente).generate("p") == "ok"
    assert cliente.llamadas == 2


@pytest.mark.asyncio
async def test_generate_no_reintenta_una_clave_invalida():
    cliente = _ClienteFalso([_resp(401), _resp(200)])
    with pytest.raises(HTTPException) as e:
        await _servicio(cliente).generate("p")
    assert e.value.status_code == 503 and cliente.llamadas == 1


@pytest.mark.asyncio
async def test_generate_no_reintenta_un_tiempo_agotado():
    cliente = _ClienteFalso([httpx.ReadTimeout("t"), _resp(200)])
    with pytest.raises(HTTPException) as e:
        await _servicio(cliente).generate("p")
    assert e.value.status_code == 504 and cliente.llamadas == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("contenido", ["", "   \n", None])
async def test_generate_rechaza_una_respuesta_vacia(contenido):
    cliente = _ClienteFalso([_resp(200, contenido)])
    with pytest.raises(HTTPException) as e:
        await _servicio(cliente).generate("p")
    assert e.value.status_code == 502


# ─── Privacidad ──────────────────────────────────────────────────────────────

def test_los_prompts_de_estudiante_no_llevan_nombre_y_el_nombre_se_inserta_despues():
    dash = LLMPrompts.mensaje_motivacional_dashboard("femenino", 3, "tema-piratas")
    prog = LLMPrompts.mensaje_motivacional_progreso("masculino", None)
    ana = LLMPrompts.analisis_post_practica("femenino", "Suma", 2, 5, 4, 0.8, 12.0)
    for prompt in (dash, prog, ana):
        assert LLMPrompts.MARCADOR_NOMBRE in prompt
    assert LLMPrompts.insertar_nombre("¡Hola, [NOMBRE]!", "Valentina Gómez Ruiz") == "¡Hola, Valentina!"
    assert LLMPrompts.insertar_nombre("Sin marcador", "Ana") == "Sin marcador"


def _estadisticas_falsas():
    def est(i, nombre, **kw):
        return SimpleNamespace(
            id=i, nombre=nombre, nivel_suma=2, nivel_resta=2, nivel_multiplicacion=2, nivel_division=2,
            precision=70.0, probabilidad_avance=kw.get("prob", 50.0), dias_sin_practicar=kw.get("dias", 0),
            alertas=kw.get("alertas", []))

    ests = [est(1, "Zoe Pérez", prob=20.0, alertas=["rezagado"]), est(2, "Marcos Díaz", prob=90.0)]
    return SimpleNamespace(
        grupo_nombre="5to B Secreto", total_estudiantes=2, estudiantes=ests,
        distribucion_perfiles=SimpleNamespace(rapido_preciso=1, cuidadoso_metodico=0, impulsivo=0,
                                              en_desarrollo=1, no_clasificado=0),
        resumen_alertas=SimpleNamespace(posible_trampa=0, inactivo=0, rezagado=1,
                                        dificultad_persistente=0, excelencia=0),
    )


def test_el_prompt_del_grupo_usa_etiquetas_y_la_respuesta_recupera_los_nombres():
    stats = _estadisticas_falsas()
    prompt = StatsService._construir_prompt_analisis(stats)
    for secreto in ("Zoe", "Marcos", "Secreto"):
        assert secreto not in prompt
    assert "Estudiante 1" in prompt and "[GRUPO]" in prompt

    etiquetas = StatsService._etiquetas_anonimas(stats)
    texto = StatsService._restaurar_nombres("En [GRUPO], Estudiante 1 necesita apoyo y Estudiante 2 destaca.", etiquetas)
    assert texto == "En 5to B Secreto, Zoe Pérez necesita apoyo y Marcos Díaz destaca."


@pytest.mark.asyncio
async def test_r1_usa_un_timeout_mayor_que_v3():
    usados = []

    class _Cliente(_ClienteFalso):
        async def post(self, url, json=None, timeout=None):
            usados.append(timeout)
            return await super().post(url, json)

    svc = _servicio(_Cliente([_resp(200, "a"), _resp(200, "b")]))
    await svc.generate("p")
    await svc.generate("p", use_reasoning=True)
    assert usados == [svc.timeout, svc.timeout_reasoner] and svc.timeout_reasoner > svc.timeout


def test_el_prompt_del_analisis_no_menciona_pasos_intermedios():
    ana = LLMPrompts.analisis_post_practica("femenino", "Suma", 2, 5, 4, 0.8, 12.0)
    assert "intermedios" not in ana.lower()
