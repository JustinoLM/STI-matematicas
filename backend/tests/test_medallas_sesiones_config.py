"""
Medallas de exploración y de desafíos, tema activo por sesión, completar sesión
(propiedad, estado y una sola vez), cierre de sesiones inactivas, configuración del
profesor (niveles y pistas) y alerta de promoción rápida.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.adaptive import EstadoSesion, PerfilEstudiante, SesionPractica, TipoAlerta
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.gamification import (
    CategoriaDesbloqueable,
    CategoriaMedalla,
    Desbloqueable,
    EstudianteDesbloqueable,
    Medalla,
    PersonalizacionEstudiante,
)
from app.models.group import EstudianteGrupo, Grupo
from app.models.practice_config import ConfiguracionPractica
from app.models.problem import Intento, Operacion, Problema, TipoSesion
from app.models.user import Profesor
from app.repositories.adaptive_repository import TEMAS_NARRATIVOS, AdaptiveRepository
from app.repositories.gamification_repository import GamificationRepository
from app.services import scheduler_service
from app.services.adaptive_service import AdaptiveService
from app.services.gamification_service import GamificationService
from app.services.teacher_service import TeacherService
from tests.conftest import TestSessionLocal, admin_headers


async def _estudiante(c: AsyncClient, codigo: str):
    r = await c.post("/api/auth/admin/students", headers=admin_headers(),
                     json={"codigo_estudiante": codigo, "nombre_completo": "Estudiante de prueba",
                           "password": "password123"})
    assert r.status_code == 201, r.text
    login = await c.post("/api/auth/login", json={"codigo": codigo, "password": "password123"})
    return r.json()["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def _sesion(est_id, estado=EstadoSesion.COMPLETADA, dias_atras=0, tema=None, cambios=None, **kw):
    fin = datetime.utcnow() - timedelta(days=dias_atras)
    campos = dict(
        estudiante_id=est_id, perfil_id=est_id, cantidad_problemas=1, problemas_ids=[],
        estado=estado, nivel_actual_inicio=2, tema_activo=tema, cambios_nivel=cambios,
        fecha_inicio=fin - timedelta(minutes=10),
        fecha_fin=fin if estado == EstadoSesion.COMPLETADA else None,
    )
    campos.update(kw)
    return SesionPractica(**campos)


def _servicio_gamificacion(db):
    return GamificationService(GamificationRepository(db), AdaptiveRepository(db))


# ─── Medallas ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_medalla_explorador_exige_practicar_con_los_seis_temas():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "MED001")
    async with TestSessionLocal() as db:
        db.add(PerfilEstudiante(estudiante_id=est))
        await db.flush()
        medalla = Medalla(nombre="Explorador", descripcion="x", categoria=CategoriaMedalla.EXPLORACION,
                          criterio={"tipo": "exploracion_temas", "temas_requeridos": 6})
        db.add(medalla)
        for tema in TEMAS_NARRATIVOS[:5]:
            db.add(_sesion(est, tema=tema))
        db.add(_sesion(est, tema="tema-default"))                     # el tema clásico no cuenta
        db.add(_sesion(est, tema=TEMAS_NARRATIVOS[0], estado=EstadoSesion.ABANDONADA))
        await db.commit()
        svc = _servicio_gamificacion(db)
        perfil = await AdaptiveRepository(db).get_perfil(est)
        assert await AdaptiveRepository(db).contar_temas_narrativos_practicados(est) == 5
        assert await svc._cumple_criterio_medalla(est, perfil, medalla) is False
        db.add(_sesion(est, tema=TEMAS_NARRATIVOS[5]))
        await db.commit()
        assert await svc._cumple_criterio_medalla(est, perfil, medalla) is True


async def _desafio_completado(db, est, sesiones_en_ventana):
    prof = Profesor(codigo_profesor=f"PD{est}", password_hash="x", tipo_usuario="profesor",
                    nombre_completo="Profesor de prueba")
    db.add(prof)
    await db.flush()
    grupo = Grupo(nombre="G", profesor_id=prof.id, codigo_grupo=f"GD{est}")
    db.add(grupo)
    await db.flush()
    db.add(EstudianteGrupo(estudiante_id=est, grupo_id=grupo.id, activo=True))
    desafio = DesafioGrupal(profesor_id=prof.id, nombre="Reto", tipo="sesiones_completadas",
                            objetivo_cantidad=5, fecha_creacion=datetime.utcnow() - timedelta(days=10),
                            completado=True)
    db.add(desafio)
    await db.flush()
    db.add(GrupoDesafio(desafio_id=desafio.id, grupo_id=grupo.id, progreso_actual=5, puntos_otorgados=True))
    for i in range(sesiones_en_ventana):
        db.add(_sesion(est, dias_atras=i + 1))
    await db.commit()
    return desafio


@pytest.mark.asyncio
async def test_medalla_de_desafio_grupal_cuenta_solo_los_desafios_en_que_participo():
    async with AsyncClient(app=app, base_url="http://test") as c:
        participa, _ = await _estudiante(c, "MED002")
        espectador, _ = await _estudiante(c, "MED003")
    async with TestSessionLocal() as db:
        db.add_all([PerfilEstudiante(estudiante_id=participa), PerfilEstudiante(estudiante_id=espectador)])
        await db.flush()
        await _desafio_completado(db, participa, sesiones_en_ventana=3)   # ≥ 3 sesiones: participó
        await _desafio_completado(db, espectador, sesiones_en_ventana=2)  # < 3: no participó
        repo = AdaptiveRepository(db)
        assert await repo.contar_desafios_grupales_participados(participa) == 1
        assert await repo.contar_desafios_grupales_participados(espectador) == 0

        medalla = Medalla(nombre="Colaborador", descripcion="x", categoria=CategoriaMedalla.DESAFIOS,
                          criterio={"tipo": "desafio_grupal", "cantidad": 1})
        db.add(medalla)
        await db.commit()
        svc = _servicio_gamificacion(db)
        assert await svc._cumple_criterio_medalla(participa, await repo.get_perfil(participa), medalla) is True
        assert await svc._cumple_criterio_medalla(espectador, await repo.get_perfil(espectador), medalla) is False


@pytest.mark.asyncio
async def test_medalla_de_comprar_todo_se_evalua_contra_el_catalogo_vigente():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "MED004")
    async with TestSessionLocal() as db:
        db.add(PerfilEstudiante(estudiante_id=est))
        items = [Desbloqueable(categoria=CategoriaDesbloqueable.FONDO, nombre=f"F{i}", precio_puntos=75)
                 for i in range(3)]
        db.add_all(items)
        medalla = Medalla(nombre="Todo", descripcion="x", categoria=CategoriaMedalla.EXPLORACION,
                          criterio={"tipo": "coleccionista", "todos": True})
        db.add(medalla)
        await db.flush()
        repo = AdaptiveRepository(db)
        svc = _servicio_gamificacion(db)
        for it in items[:2]:
            db.add(EstudianteDesbloqueable(estudiante_id=est, desbloqueable_id=it.id, puntos_gastados=75))
        await db.commit()
        assert await svc._cumple_criterio_medalla(est, await repo.get_perfil(est), medalla) is False
        db.add(EstudianteDesbloqueable(estudiante_id=est, desbloqueable_id=items[2].id, puntos_gastados=75))
        await db.commit()
        assert await svc._cumple_criterio_medalla(est, await repo.get_perfil(est), medalla) is True


@pytest.mark.asyncio
async def test_medalla_de_comprar_todo_no_se_cumple_con_un_item_inactivo_en_lugar_de_uno_activo():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "MED005")
    async with TestSessionLocal() as db:
        db.add(PerfilEstudiante(estudiante_id=est))
        activos = [Desbloqueable(categoria=CategoriaDesbloqueable.FONDO, nombre=f"A{i}", precio_puntos=75)
                   for i in range(2)]
        retirado = Desbloqueable(categoria=CategoriaDesbloqueable.FONDO, nombre="Retirado",
                                 precio_puntos=75, activo=False)
        db.add_all(activos + [retirado])
        medalla = Medalla(nombre="Todo", descripcion="x", categoria=CategoriaMedalla.EXPLORACION,
                          criterio={"tipo": "coleccionista", "todos": True})
        db.add(medalla)
        await db.flush()
        repo = AdaptiveRepository(db)
        svc = _servicio_gamificacion(db)
        # Tiene tantos items como activos hay (2), pero uno es el retirado y falta un activo
        for it in (activos[0], retirado):
            db.add(EstudianteDesbloqueable(estudiante_id=est, desbloqueable_id=it.id, puntos_gastados=75))
        await db.commit()
        assert await svc._cumple_criterio_medalla(est, await repo.get_perfil(est), medalla) is False
        db.add(EstudianteDesbloqueable(estudiante_id=est, desbloqueable_id=activos[1].id, puntos_gastados=75))
        await db.commit()
        assert await svc._cumple_criterio_medalla(est, await repo.get_perfil(est), medalla) is True


# ─── Tema activo ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tema_activo_del_estudiante():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "TEM001")
    async with TestSessionLocal() as db:
        repo = AdaptiveRepository(db)
        assert await repo.get_tema_activo(est) is None
        tema = Desbloqueable(categoria=CategoriaDesbloqueable.TEMA, nombre="Piratas", precio_puntos=500,
                             archivo_referencia="tema-piratas", orden=2)
        db.add(tema)
        await db.flush()
        db.add(PersonalizacionEstudiante(estudiante_id=est, tema_activo_id=tema.id))
        await db.commit()
        assert await repo.get_tema_activo(est) == "tema-piratas"


# ─── Completar sesión ────────────────────────────────────────────────────────

async def _sesion_con_intentos(db, est, estado=EstadoSesion.COMPLETADA, aciertos=(True,), suma_previa=0):
    perfil = await db.get(PerfilEstudiante, est)
    if perfil is None:
        perfil = PerfilEstudiante(estudiante_id=est, diagnostico_completado=True, nivel_suma=2)
        db.add(perfil)
    perfil.consecutivas_correctas_suma = suma_previa
    await db.flush()
    prob = Problema(operacion=Operacion.SUMA, numero1=Decimal(1), numero2=Decimal(2), resultado=Decimal(3),
                    nivel_dificultad=1, cantidad_decimales=0, signature=f"cs_{est}_{datetime.utcnow().timestamp()}")
    db.add(prob)
    await db.flush()
    s = _sesion(est, estado=estado, problemas_ids=[prob.id], operaciones_incluidas={"+": len(aciertos)},
                cantidad_problemas=len(aciertos))
    s.nivel_suma_inicio = 2
    db.add(s)
    await db.flush()
    for ok in aciertos:
        db.add(Intento(estudiante_id=est, problema_id=prob.id, respuesta_estudiante=Decimal(3 if ok else 4),
                       es_correcto=ok, tiempo_resolucion=12, tipo_sesion=TipoSesion.PRACTICA, sesion_id=s.id))
    await db.commit()
    return s.id


@pytest.mark.asyncio
async def test_completar_sesion_una_sola_vez_y_solo_el_dueno():
    async with AsyncClient(app=app, base_url="http://test") as c:
        dueno, H1 = await _estudiante(c, "COM001")
        otro, H2 = await _estudiante(c, "COM002")
        async with TestSessionLocal() as db:
            sid = await _sesion_con_intentos(db, dueno)
            en_curso = await _sesion_con_intentos(db, dueno, estado=EstadoSesion.EN_PROGRESO)

        # otro estudiante no puede completar la sesión ajena (ni recibir sus puntos)
        r = await c.post("/api/adaptive/practice/complete", headers=H2, json={"sesion_id": sid})
        assert r.status_code == 403
        # una sesión sin terminar no se puede completar
        r = await c.post("/api/adaptive/practice/complete", headers=H1, json={"sesion_id": en_curso})
        assert r.status_code == 400
        # el dueño la completa una vez y recibe los puntos
        r = await c.post("/api/adaptive/practice/complete", headers=H1, json={"sesion_id": sid})
        assert r.status_code == 200, r.text
        saldo = (await c.get("/api/gamification/balance", headers=H1)).json()["puntos_totales"]
        assert saldo > 0
        # repetir la llamada no suma puntos ni vuelve a procesar el perfil
        r = await c.post("/api/adaptive/practice/complete", headers=H1, json={"sesion_id": sid})
        assert r.status_code == 409
        assert (await c.get("/api/gamification/balance", headers=H1)).json()["puntos_totales"] == saldo
        assert (await c.get("/api/gamification/balance", headers=H2)).json()["puntos_totales"] == 0


@pytest.mark.asyncio
async def test_la_racha_acumulada_sube_de_nivel_y_queda_en_el_historial():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, H = await _estudiante(c, "HIS002")
        async with TestSessionLocal() as db:
            # umbral 10 (no clasificado): 9 aciertos acumulados + 1 en esta sesión
            sid = await _sesion_con_intentos(db, est, aciertos=(True,), suma_previa=9)
        r = await c.post("/api/adaptive/practice/complete", headers=H, json={"sesion_id": sid})
        assert r.status_code == 200, r.text
        cambios = {x["operacion"]: x for x in r.json()["cambios_nivel"]}
        assert cambios["+"]["nivel_nuevo"] == 3 and "10 problemas consecutivos" in cambios["+"]["razon"]
    async with TestSessionLocal() as db:
        perfil = await db.get(PerfilEstudiante, est)
        assert perfil.nivel_suma == 3 and perfil.consecutivas_correctas_suma == 0
        assert [h["operacion"] for h in perfil.historial_promociones] == ["+"]
        assert perfil.historial_promociones[0]["nivel_nuevo"] == 3


# ─── Sesiones inactivas ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_el_job_cierra_las_sesiones_iniciadas_y_en_progreso_inactivas(monkeypatch):
    monkeypatch.setattr(scheduler_service, "AsyncSessionLocal", TestSessionLocal)
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, _ = await _estudiante(c, "JOB001")
    viejo = datetime.utcnow() - timedelta(minutes=120)
    async with TestSessionLocal() as db:
        db.add(PerfilEstudiante(estudiante_id=est))
        await db.flush()
        ids = {}
        for nombre, estado, ultima in [("iniciada", EstadoSesion.INICIADA, viejo),
                                       ("en_progreso", EstadoSesion.EN_PROGRESO, viejo),
                                       ("reciente", EstadoSesion.EN_PROGRESO, datetime.utcnow()),
                                       ("pausada", EstadoSesion.PAUSADA, viejo)]:
            s = _sesion(est, estado=estado, fecha_ultima_actividad=ultima)
            db.add(s)
            await db.flush()
            ids[nombre] = s.id
        await db.commit()

    await scheduler_service.job_cerrar_sesiones_huerfanas()

    async with TestSessionLocal() as db:
        estados = {n: (await db.get(SesionPractica, i)).estado for n, i in ids.items()}
    assert estados == {"iniciada": EstadoSesion.ABANDONADA, "en_progreso": EstadoSesion.ABANDONADA,
                       "reciente": EstadoSesion.EN_PROGRESO, "pausada": EstadoSesion.PAUSADA}


# ─── Configuración del profesor ──────────────────────────────────────────────

def test_niveles_permitidos_eligen_el_nivel_mas_cercano():
    f = AdaptiveService._ajustar_a_niveles_permitidos
    assert f(3, []) == 3 and f(3, [2, 3, 4]) == 3
    assert f(5, [1, 2, 3]) == 3 and f(1, [3, 4]) == 3
    assert f(3, [2, 4]) == 2          # empate: el menor


async def _grupo_con_config(db, est, **cfg):
    prof = Profesor(codigo_profesor=f"PC{est}", password_hash="x", tipo_usuario="profesor",
                    nombre_completo="Profesor de prueba")
    db.add(prof)
    await db.flush()
    grupo = Grupo(nombre="G", profesor_id=prof.id, codigo_grupo=f"GC{est}")
    db.add(grupo)
    await db.flush()
    db.add(EstudianteGrupo(estudiante_id=est, grupo_id=grupo.id, activo=True))
    base = dict(grupo_id=grupo.id, aplicada_por_profesor_id=prof.id, operaciones_permitidas=["suma"],
                niveles_permitidos=[1, 2, 3, 4, 5], rango_min=1, rango_max=100, decimales_maximos=2,
                pistas_habilitadas={"nivel_1": True, "nivel_2": True, "nivel_3": True}, activa=True)
    base.update(cfg)
    db.add(ConfiguracionPractica(**base))
    await db.commit()


@pytest.mark.asyncio
async def test_el_profesor_puede_deshabilitar_niveles_de_pista():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, H = await _estudiante(c, "CFG001")
        async with TestSessionLocal() as db:
            db.add(PerfilEstudiante(estudiante_id=est))
            prob = Problema(operacion=Operacion.SUMA, numero1=Decimal(1), numero2=Decimal(2), resultado=Decimal(3),
                            nivel_dificultad=1, cantidad_decimales=0, signature="cfg1")
            db.add(prob)
            await db.flush()
            s = _sesion(est, estado=EstadoSesion.EN_PROGRESO, problemas_ids=[prob.id])
            db.add(s)
            await db.flush()
            await _grupo_con_config(db, est, pistas_habilitadas={"nivel_1": True, "nivel_2": False, "nivel_3": True})
            pid, sid = prob.id, s.id

        r = await c.post("/api/hints/request", headers=H, json={"sesion_id": sid, "problema_id": pid, "nivel_pista": 2})
        assert r.status_code == 403 and "deshabilitó" in r.json()["detail"]
        r = await c.post("/api/hints/request", headers=H, json={"sesion_id": sid, "problema_id": pid, "nivel_pista": 1})
        assert r.status_code == 200
        disp = (await c.get("/api/hints/available", headers=H,
                            params={"sesion_id": sid, "problema_id": pid})).json()
        assert disp["niveles_disponibles"] == [3] and disp["niveles_usados"] == [1]


@pytest.mark.asyncio
async def test_una_pista_de_un_problema_ajeno_a_la_sesion_se_rechaza():
    async with AsyncClient(app=app, base_url="http://test") as c:
        est, H = await _estudiante(c, "CFG002")
        async with TestSessionLocal() as db:
            db.add(PerfilEstudiante(estudiante_id=est))
            s = _sesion(est, estado=EstadoSesion.EN_PROGRESO, problemas_ids=[999])
            db.add(s)
            await db.commit()
            sid = s.id
        r = await c.post("/api/hints/request", headers=H, json={"sesion_id": sid, "problema_id": 1, "nivel_pista": 1})
        assert r.status_code == 400


# ─── Alerta de promoción rápida ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerta_de_promocion_rapida():
    async with AsyncClient(app=app, base_url="http://test") as c:
        rapido, _ = await _estudiante(c, "ALE001")
        normal, _ = await _estudiante(c, "ALE002")
    subida = {"+": {"antes": 2, "despues": 3, "razon": "x"}}
    async with TestSessionLocal() as db:
        prof = Profesor(codigo_profesor="PALE", password_hash="x", tipo_usuario="profesor",
                        nombre_completo="Profesor de prueba")
        db.add(prof)
        await db.flush()
        grupo = Grupo(nombre="G", profesor_id=prof.id, codigo_grupo="GALE")
        db.add(grupo)
        await db.flush()
        for e in (rapido, normal):
            db.add(PerfilEstudiante(estudiante_id=e))
            db.add(EstudianteGrupo(estudiante_id=e, grupo_id=grupo.id, activo=True))
        await db.flush()
        for dias, cambios in [(4, {}), (3, subida), (2, subida), (1, {})]:   # 2 subidas en las últimas 3
            db.add(_sesion(rapido, dias_atras=dias, cambios=cambios))
        for dias, cambios in [(6, subida), (3, {}), (2, {}), (1, {})]:       # la subida quedó fuera de las 3
            db.add(_sesion(normal, dias_atras=dias, cambios=cambios))
        await db.commit()

        alertas = [a for a in await TeacherService(db).get_alertas(prof.id)
                   if a.tipo == TipoAlerta.PROMOCION_RAPIDA]
        assert [a.estudiante_id for a in alertas] == [rapido]
        assert alertas[0].datos_contexto == {"subidas_ultimas_3_sesiones": 2}
