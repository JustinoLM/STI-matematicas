"""
Organización escolar (fase 1): salón fijo, año lectivo, matrícula, grupos, trimestres y cierre.

Cubre:
- unicidad del salón activo del estudiante (en la API y en la base de datos);
- cierre del año lectivo en solo lectura (grupos, configuración, desafíos) sin perder puntos;
- fechas por defecto de los trimestres y su edición por el administrador;
- bloqueo de la práctica para el estudiante sin salón;
- configuración de decimales leída desde el año lectivo del salón.
"""

from datetime import date, datetime, timedelta
from itertools import count

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models.adaptive import PerfilEstudiante
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.gamification import TransaccionPuntos
from app.models.practice_config import ConfiguracionPractica
from app.models.school import AnioLectivo, Matricula
from app.repositories.adaptive_repository import AdaptiveRepository
from app.services.school_service import trimestres_por_defecto
from tests.conftest import TestSessionLocal, admin_headers
from tests.salones_helpers import salon_con_estudiantes
from tests.test_medallas_sesiones_config import _sesion

_n = count(1)
ANIO = date.today().year


# ─── Helpers por la API ──────────────────────────────────────────────────────

async def _org(c: AsyncClient) -> int:
    n = next(_n)
    r = await c.post("/api/admin/organizations", headers=admin_headers(),
                     json={"nombre": f"Escuela Prueba {n}", "codigo": f"ESC{n:03d}"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _profesor(c: AsyncClient, org_id: int) -> tuple[int, dict]:
    codigo = f"PRF{next(_n):03d}"
    r = await c.post("/api/auth/admin/teachers", headers=admin_headers(),
                     json={"codigo_profesor": codigo, "nombre_completo": f"Docente {codigo}",
                           "password": "password123", "organizacion_id": org_id})
    assert r.status_code == 201, r.text
    login = await c.post("/api/auth/login", json={"codigo": codigo, "password": "password123"})
    return r.json()["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _estudiante(c: AsyncClient, org_id: int) -> tuple[int, dict]:
    codigo = f"ALU{next(_n):03d}"
    r = await c.post("/api/auth/admin/students", headers=admin_headers(),
                     json={"codigo_estudiante": codigo, "nombre_completo": f"Estudiante {codigo}",
                           "password": "password123", "organizacion_id": org_id})
    assert r.status_code == 201, r.text
    login = await c.post("/api/auth/login", json={"codigo": codigo, "password": "password123"})
    return r.json()["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _salon(c: AsyncClient, H: dict, nombre: str = "1A", grado: int = 1) -> dict:
    r = await c.post("/api/teachers/salones", headers=H, json={"nombre": nombre, "grado": grado})
    assert r.status_code == 201, r.text
    return r.json()


# ─── Trimestres ──────────────────────────────────────────────────────────────

def test_fechas_por_defecto_de_los_trimestres_2026():
    assert trimestres_por_defecto(2026) == [
        (date(2026, 3, 2), date(2026, 5, 29)),
        (date(2026, 6, 8), date(2026, 9, 4)),
        (date(2026, 9, 14), date(2026, 12, 11)),
    ]


@pytest.mark.parametrize("anio", range(2025, 2036))
def test_los_trimestres_por_defecto_siguen_la_regla(anio):
    t = trimestres_por_defecto(anio)
    inicio = t[0][0]
    assert inicio.month == 3 and inicio.weekday() == 0 and inicio.day <= 7   # primer lunes de marzo
    for (ini, fin) in t:
        assert ini.weekday() == 0 and fin.weekday() == 4                       # de lunes a viernes
        assert (fin - ini).days == 13 * 7 - 3                                  # 13 semanas
    for (_, fin), (ini_sig, _) in zip(t, t[1:]):
        assert (ini_sig - fin).days == 10                                      # una semana de vacaciones
    assert t[2][1].month == 12 and 8 <= t[2][1].day <= 17                      # mediados de diciembre


@pytest.mark.asyncio
async def test_el_administrador_edita_los_trimestres_de_la_organizacion():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        r = await c.get(f"/api/admin/organizations/{org}/trimestres/2026", headers=admin_headers())
        assert r.status_code == 200
        assert [t["fecha_inicio"] for t in r.json()] == ["2026-03-02", "2026-06-08", "2026-09-14"]

        nuevas = {"trimestres": [
            {"fecha_inicio": "2026-03-09", "fecha_fin": "2026-06-05"},
            {"fecha_inicio": "2026-06-15", "fecha_fin": "2026-09-11"},
            {"fecha_inicio": "2026-09-21", "fecha_fin": "2026-12-16"},
        ]}
        r = await c.put(f"/api/admin/organizations/{org}/trimestres/2026", headers=admin_headers(), json=nuevas)
        assert r.status_code == 200, r.text
        r = await c.get(f"/api/admin/organizations/{org}/trimestres/2026", headers=admin_headers())
        assert r.json()[2]["fecha_fin"] == "2026-12-16"

        solapadas = {"trimestres": [
            {"fecha_inicio": "2026-03-09", "fecha_fin": "2026-06-20"},
            {"fecha_inicio": "2026-06-15", "fecha_fin": "2026-09-11"},
            {"fecha_inicio": "2026-09-21", "fecha_fin": "2026-12-16"},
        ]}
        r = await c.put(f"/api/admin/organizations/{org}/trimestres/2026", headers=admin_headers(), json=solapadas)
        assert r.status_code == 400

        # Solo el administrador
        _, H = await _profesor(c, org)
        r = await c.put(f"/api/admin/organizations/{org}/trimestres/2026", headers=H, json=nuevas)
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_el_salon_nuevo_trae_los_trimestres_de_su_organizacion():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        salon = await _salon(c, H)
    esperadas = trimestres_por_defecto(ANIO)
    assert [(t["fecha_inicio"], t["fecha_fin"]) for t in salon["trimestres"]] == [
        (i.isoformat(), f.isoformat()) for i, f in esperadas
    ]
    assert salon["grado"] == 1 and salon["anio"] == ANIO and salon["estado"] == "activo"


# ─── Salón fijo y año lectivo ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_un_salon_tiene_un_solo_anio_activo_y_su_grado_es_fijo():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H1 = await _profesor(c, org)
        _, H2 = await _profesor(c, org)
        await _salon(c, H1, "1a")                       # se normaliza a "1A"
        r = await c.post("/api/teachers/salones", headers=H2, json={"nombre": "1A", "grado": 1})
        assert r.status_code == 409 and "ya está abierto" in r.json()["detail"]
        r = await c.post("/api/teachers/salones", headers=H1, json={"nombre": "1A", "grado": 2})
        assert r.status_code == 409 and "1.º grado" in r.json()["detail"]
        r = await c.post("/api/teachers/salones", headers=H1, json={"nombre": "2B", "grado": 7})
        assert r.status_code == 422
        # Un profesor puede tener varios salones el mismo año
        await _salon(c, H1, "1B")
        r = await c.get("/api/teachers/salones", headers=H1)
        assert sorted(s["nombre"] for s in r.json()) == ["1A", "1B"]


@pytest.mark.asyncio
async def test_el_profesor_no_ve_salones_ajenos():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H1 = await _profesor(c, org)
        _, H2 = await _profesor(c, org)
        salon = await _salon(c, H1)
        r = await c.get(f"/api/teachers/salones/{salon['anio_lectivo_id']}", headers=H2)
        assert r.status_code == 404
        est, _ = await _estudiante(c, org)
        r = await c.post(f"/api/teachers/salones/{salon['anio_lectivo_id']}/estudiantes/{est}", headers=H2)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_solo_se_asignan_estudiantes_de_la_misma_organizacion():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org, otra = await _org(c), await _org(c)
        _, H = await _profesor(c, org)
        salon = await _salon(c, H)
        ajeno, _ = await _estudiante(c, otra)
        r = await c.post(f"/api/teachers/salones/{salon['anio_lectivo_id']}/estudiantes/{ajeno}", headers=H)
        assert r.status_code == 404


# ─── Unicidad del salón activo ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_un_estudiante_esta_en_un_solo_salon_activo():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H1 = await _profesor(c, org)
        _, H2 = await _profesor(c, org)
        s1 = (await _salon(c, H1, "1A"))["anio_lectivo_id"]
        s2 = (await _salon(c, H2, "1B"))["anio_lectivo_id"]
        est, _ = await _estudiante(c, org)

        assert (await c.post(f"/api/teachers/salones/{s1}/estudiantes/{est}", headers=H1)).status_code == 204
        # Asignar dos veces al mismo salón no duplica
        assert (await c.post(f"/api/teachers/salones/{s1}/estudiantes/{est}", headers=H1)).status_code == 204

        r = await c.post(f"/api/teachers/salones/{s2}/estudiantes/{est}", headers=H2)
        assert r.status_code == 409
        assert "1A" in r.json()["detail"] and "debe quitarlo primero" in r.json()["detail"]

        # El candidato aparece con su salón actual
        cand = (await c.get(f"/api/teachers/salones/{s2}/candidatos", headers=H2)).json()
        assert {x["id"]: x["salon_actual"] for x in cand}[est] == "1A"

        # Al quitarlo del primero, ya se puede asignar al segundo
        assert (await c.delete(f"/api/teachers/salones/{s1}/estudiantes/{est}", headers=H1)).status_code == 204
        assert (await c.post(f"/api/teachers/salones/{s2}/estudiantes/{est}", headers=H2)).status_code == 204

    async with TestSessionLocal() as db:
        estados = sorted((await db.execute(
            select(Matricula.estado).where(Matricula.estudiante_id == est)
        )).scalars().all())
    assert estados == ["activa", "retirada"]


@pytest.mark.asyncio
async def test_la_base_impide_dos_matriculas_activas():
    async with TestSessionLocal() as db:
        _, al1 = await salon_con_estudiantes(db, [])
        _, al2 = await salon_con_estudiantes(db, [])
        from app.models.user import Estudiante
        est = Estudiante(codigo_estudiante="DUP1", password_hash="x", tipo_usuario="estudiante",
                         nombre_completo="Duplicado")
        db.add(est)
        await db.flush()
        db.add(Matricula(anio_lectivo_id=al1.id, estudiante_id=est.id, estado="activa"))
        await db.flush()
        db.add(Matricula(anio_lectivo_id=al2.id, estudiante_id=est.id, estado="activa"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


@pytest.mark.asyncio
async def test_la_base_impide_dos_anios_activos_del_mismo_salon():
    async with TestSessionLocal() as db:
        prof, al = await salon_con_estudiantes(db, [])
        db.add(AnioLectivo(salon_id=al.salon_id, anio=al.anio + 1, profesor_id=prof.id, estado="activo"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


@pytest.mark.asyncio
async def test_asignacion_por_codigos_informa_los_conflictos():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H1 = await _profesor(c, org)
        _, H2 = await _profesor(c, org)
        s1 = (await _salon(c, H1, "1A"))["anio_lectivo_id"]
        s2 = (await _salon(c, H2, "1B"))["anio_lectivo_id"]
        e1, _ = await _estudiante(c, org)
        e2, _ = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{s2}/estudiantes/{e2}", headers=H2)
        detalle = (await c.get(f"/api/teachers/salones/{s2}", headers=H2)).json()
        codigo_e2 = detalle["estudiantes"][0]["codigo_estudiante"]
        cand = (await c.get(f"/api/teachers/salones/{s1}/candidatos", headers=H1)).json()
        codigo_e1 = {x["id"]: x["codigo_estudiante"] for x in cand}[e1]

        r = await c.post(f"/api/teachers/salones/{s1}/estudiantes/bulk", headers=H1,
                         json={"codigos": [codigo_e1, codigo_e2, "NOEXISTE", ""]})
        assert r.status_code == 200, r.text
        res = r.json()
        assert res["agregados"] == 1 and len(res["errores"]) == 3
        assert "1B" in res["errores"][0]["mensaje"]


# ─── Grupos dentro del salón ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_los_grupos_son_subconjuntos_del_salon():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        al = (await _salon(c, H))["anio_lectivo_id"]
        dentro, _ = await _estudiante(c, org)
        fuera, _ = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{dentro}", headers=H)

        r = await c.post(f"/api/teachers/salones/{al}/grupos", headers=H, json={"nombre": "Equipo rojo"})
        assert r.status_code == 201, r.text
        grupo = r.json()["id"]
        r = await c.post(f"/api/teachers/salones/{al}/grupos", headers=H, json={"nombre": "Equipo rojo"})
        assert r.status_code == 409

        assert (await c.post(f"/api/teachers/groups/{grupo}/students/{dentro}", headers=H)).status_code == 204
        r = await c.post(f"/api/teachers/groups/{grupo}/students/{fuera}", headers=H)
        assert r.status_code == 400 and "asígnalo al salón" in r.json()["detail"]

        # Quitar al estudiante del salón lo saca también de sus grupos
        await c.delete(f"/api/teachers/salones/{al}/estudiantes/{dentro}", headers=H)
        detalle = (await c.get(f"/api/teachers/groups/{grupo}", headers=H)).json()
        assert detalle["cantidad_estudiantes"] == 0


# ─── Estudiante sin salón ────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("ruta", [
    "/api/adaptive/practice/start",
    "/api/adaptive/diagnostic/start",
    "/api/adaptive/redencion/iniciar",
    "/api/regla-de-tres/practice/start",
])
async def test_un_estudiante_sin_salon_no_puede_practicar(ruta):
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, HE = await _estudiante(c, org)
        r = await c.post(ruta, headers=HE)
    assert r.status_code == 403
    assert r.json()["codigo"] == "SIN_SALON"
    assert "Consulta a tu profesor" in r.json()["detail"]


@pytest.mark.asyncio
async def test_con_salon_el_estudiante_puede_empezar_el_diagnostico():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        al = (await _salon(c, H))["anio_lectivo_id"]
        est, HE = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{est}", headers=H)
        r = await c.post("/api/adaptive/diagnostic/start", headers=HE)
        assert r.status_code == 200, r.text
        perfil = (await c.get("/api/adaptive/profile", headers=HE)).json()
        assert perfil["grupo_nombre"] == "1A"


# ─── Configuración de decimales desde el salón ───────────────────────────────

async def _config(db, al_id, prof_id, ops, minutos_atras=0):
    cfg = ConfiguracionPractica(
        anio_lectivo_id=al_id, aplicada_por_profesor_id=prof_id, operaciones_permitidas=ops,
        niveles_permitidos=[1, 2, 3, 4, 5], rango_min=1, rango_max=50, decimales_maximos=1,
        pistas_habilitadas={"nivel_1": True, "nivel_2": True, "nivel_3": True}, activa=True,
        fecha_aplicacion=datetime.utcnow() - timedelta(minutes=minutos_atras),
    )
    db.add(cfg)
    await db.flush()
    return cfg


@pytest.mark.asyncio
async def test_la_configuracion_de_decimales_se_lee_del_salon_activo():
    from app.models.user import Estudiante
    async with TestSessionLocal() as db:
        est = Estudiante(codigo_estudiante="CFGS1", password_hash="x", tipo_usuario="estudiante",
                         nombre_completo="Config")
        db.add(est)
        await db.flush()
        prof, al = await salon_con_estudiantes(db, [est.id])
        prof2, otro = await salon_con_estudiantes(db, [])
        await _config(db, al.id, prof.id, ["suma"], minutos_atras=10)
        reciente = await _config(db, al.id, prof.id, ["resta"], minutos_atras=1)
        await _config(db, otro.id, prof2.id, ["division"])          # otro salón: no aplica
        await db.commit()

        repo = AdaptiveRepository(db)
        cfg = await repo.get_config_practica_estudiante(est.id)
        assert cfg is not None and cfg.id == reciente.id and cfg.operaciones_permitidas == ["resta"]

        # Sin salón activo no hay configuración
        m = (await db.execute(select(Matricula).where(Matricula.estudiante_id == est.id))).scalar_one()
        m.estado = "retirada"
        await db.commit()
        assert await repo.get_config_practica_estudiante(est.id) is None


@pytest.mark.asyncio
async def test_la_practica_respeta_la_configuracion_del_salon():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        al = (await _salon(c, H))["anio_lectivo_id"]
        est, HE = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{est}", headers=H)
        r = await c.post("/api/teachers/configuration", headers=H, json={
            "anio_lectivo_id": al, "operaciones_permitidas": ["resta"],
            "rango_min": 1, "rango_max": 20, "decimales_maximos": 1,
        })
        assert r.status_code == 201, r.text
        assert (await c.get(f"/api/teachers/salones/{al}/configuration", headers=H)).json()["operaciones_permitidas"] == ["resta"]

        async with TestSessionLocal() as db:
            perfil = (await db.execute(
                select(PerfilEstudiante).where(PerfilEstudiante.estudiante_id == est)
            )).scalar_one()
            perfil.diagnostico_completado = True
            await db.commit()

        r = await c.post("/api/adaptive/practice/start", headers=HE)
        assert r.status_code == 200, r.text
        assert set(r.json()["operaciones_incluidas"]) == {"-"}   # solo resta


# ─── Cierre del año lectivo ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cerrar_el_anio_deja_todo_en_solo_lectura_sin_perder_puntos():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        prof_id, H = await _profesor(c, org)
        al = (await _salon(c, H))["anio_lectivo_id"]
        est, HE = await _estudiante(c, org)
        otro, _ = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{est}", headers=H)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{otro}", headers=H)
        grupo = (await c.post(f"/api/teachers/salones/{al}/grupos", headers=H, json={"nombre": "G1"})).json()["id"]
        await c.post(f"/api/teachers/groups/{grupo}/students/{est}", headers=H)

        # Un desafío del salón completo sin terminar y uno de grupo ya completado (con puntos)
        r = await c.post("/api/teachers/challenges", headers=H, json={
            "nombre": "Cien problemas", "tipo": "problemas_resueltos", "objetivo_cantidad": 100,
            "anio_lectivo_id": al,
        })
        assert r.status_code == 201, r.text
        abierto = r.json()
        assert [g["grupo_id"] for g in abierto["progreso_grupos"]] == [None]
        assert abierto["progreso_grupos"][0]["nombre_grupo"] == "Todo el salón"
        r = await c.post("/api/teachers/challenges", headers=H, json={
            "nombre": "Ya logrado", "tipo": "sesiones_completadas", "objetivo_cantidad": 1,
            "recompensa_puntos": 30, "anio_lectivo_id": al, "grupos_ids": [grupo],
        })
        logrado = r.json()["id"]
        async with TestSessionLocal() as db:
            d = (await db.execute(select(DesafioGrupal).where(DesafioGrupal.id == logrado))).scalar_one()
            d.estado = "completado"
            gd = (await db.execute(select(GrupoDesafio).where(GrupoDesafio.desafio_id == logrado))).scalar_one()
            gd.puntos_otorgados = True
            db.add(TransaccionPuntos(estudiante_id=est, tipo="ganancia", cantidad=30,
                                     concepto="Desafío grupal completado: Ya logrado", saldo_resultante=30))
            await db.commit()

        # El estudiante ve los desafíos de sus equipos
        mis = (await c.get("/api/challenges/mis-desafios", headers=HE)).json()
        assert {d["nombre"] for d in mis} == {"Cien problemas", "Ya logrado"}

        r = await c.post(f"/api/admin/organizations/{org}/anios/{ANIO}/cerrar", headers=admin_headers())
        assert r.status_code == 200, r.text
        assert r.json() == {"anio": ANIO, "anios_cerrados": 1, "matriculas_cerradas": 2,
                            "desafios_no_completados": 1}

        # Todo sigue visible, en solo lectura
        detalle = (await c.get(f"/api/teachers/salones/{al}", headers=H)).json()
        assert detalle["cerrado"] is True and len(detalle["estudiantes"]) == 2
        assert [g["nombre"] for g in detalle["grupos"]] == ["G1"]
        desafios = {d["id"]: d for d in (await c.get("/api/teachers/challenges", headers=H)).json()}
        assert desafios[abierto["id"]]["estado"] == "no_completado"
        assert desafios[logrado]["estado"] == "completado"

        # Cualquier cambio sobre el año cerrado se rechaza
        nuevo, _ = await _estudiante(c, org)
        intentos = [
            c.post(f"/api/teachers/salones/{al}/estudiantes/{nuevo}", headers=H),
            c.delete(f"/api/teachers/salones/{al}/estudiantes/{est}", headers=H),
            c.post(f"/api/teachers/salones/{al}/grupos", headers=H, json={"nombre": "G2"}),
            c.post(f"/api/teachers/groups/{grupo}/students/{otro}", headers=H),
            c.delete(f"/api/teachers/groups/{grupo}/students/{est}", headers=H),
            c.delete(f"/api/teachers/groups/{grupo}", headers=H),
            c.post("/api/teachers/configuration", headers=H, json={"anio_lectivo_id": al, "operaciones_permitidas": ["suma"]}),
            c.post("/api/teachers/challenges", headers=H, json={
                "nombre": "Tarde", "tipo": "sesiones_completadas", "objetivo_cantidad": 1, "anio_lectivo_id": al}),
            c.delete(f"/api/teachers/challenges/{abierto['id']}", headers=H),
        ]
        for intento in intentos:
            r = await intento
            assert r.status_code == 409, r.text
            assert r.json()["codigo"] == "ANIO_CERRADO"

        # El estudiante queda sin salón y no puede practicar
        r = await c.post("/api/adaptive/practice/start", headers=HE)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_SALON"

        # El año siguiente el salón (mismo id) se abre de nuevo; el profesor puede ser otro
        _, H2 = await _profesor(c, org)
        async with TestSessionLocal() as db:
            # El año en curso ya se cerró: simulamos que el cierre fue del año anterior
            al_obj = (await db.execute(select(AnioLectivo).where(AnioLectivo.id == al))).scalar_one()
            al_obj.anio = ANIO - 1
            await db.commit()
            salon_id = al_obj.salon_id
        nuevo_anio = await _salon(c, H2, "1A")
        assert nuevo_anio["salon_id"] == salon_id and nuevo_anio["anio"] == ANIO
        assert nuevo_anio["anio_lectivo_id"] != al and nuevo_anio["cantidad_estudiantes"] == 0

    async with TestSessionLocal() as db:
        puntos = (await db.execute(
            select(TransaccionPuntos.cantidad).where(TransaccionPuntos.estudiante_id == est)
        )).scalars().all()
        gd = (await db.execute(select(GrupoDesafio).where(GrupoDesafio.desafio_id == logrado))).scalar_one()
        estados = set((await db.execute(
            select(Matricula.estado).where(Matricula.anio_lectivo_id == al)
        )).scalars().all())
    assert puntos == [30] and gd.puntos_otorgados is True
    assert estados == {"cerrada"}


@pytest.mark.asyncio
async def test_los_desafios_son_de_un_solo_salon():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        a = (await _salon(c, H, "1A"))["anio_lectivo_id"]
        b = (await _salon(c, H, "1B"))["anio_lectivo_id"]
        grupo_b = (await c.post(f"/api/teachers/salones/{b}/grupos", headers=H, json={"nombre": "GB"})).json()["id"]
        r = await c.post("/api/teachers/challenges", headers=H, json={
            "nombre": "Mezcla", "tipo": "sesiones_completadas", "objetivo_cantidad": 1,
            "anio_lectivo_id": a, "grupos_ids": [grupo_b],
        })
        assert r.status_code == 400 and "mismo salón" in r.json()["detail"]


@pytest.mark.asyncio
async def test_el_progreso_del_salon_completo_suma_a_todos_sus_estudiantes():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        al = (await _salon(c, H))["anio_lectivo_id"]
        e1, _ = await _estudiante(c, org)
        e2, _ = await _estudiante(c, org)
        for e in (e1, e2):
            await c.post(f"/api/teachers/salones/{al}/estudiantes/{e}", headers=H)
        r = await c.post("/api/teachers/challenges", headers=H, json={
            "nombre": "Entre todos", "tipo": "sesiones_completadas", "objetivo_cantidad": 3,
            "anio_lectivo_id": al,
        })
        desafio_id = r.json()["id"]
        async with TestSessionLocal() as db:
            for e in (e1, e2):   # sesiones completadas después de crear el desafío
                db.add(_sesion(e, fecha_fin=datetime.utcnow() + timedelta(minutes=1)))
            await db.commit()
        desafios = {d["id"]: d for d in (await c.get("/api/teachers/challenges", headers=H)).json()}
    assert desafios[desafio_id]["progreso_grupos"][0]["progreso_actual"] == 2


@pytest.mark.asyncio
async def test_el_administrador_ve_los_salones_de_la_organizacion():
    async with AsyncClient(app=app, base_url="http://test") as c:
        org = await _org(c)
        _, H = await _profesor(c, org)
        al = (await _salon(c, H, "2A", grado=2))["anio_lectivo_id"]
        est, _ = await _estudiante(c, org)
        await c.post(f"/api/teachers/salones/{al}/estudiantes/{est}", headers=H)
        r = await c.get(f"/api/admin/organizations/{org}/salones", headers=admin_headers())
        assert r.status_code == 200
        assert r.json()[0]["nombre"] == "2A" and r.json()[0]["grado"] == 2
        assert r.json()[0]["total_estudiantes"] == 1

        usuarios = (await c.get("/api/admin/users", headers=admin_headers())).json()
        fila = next(e for e in usuarios["estudiantes"] if e["id"] == est)
        assert fila["salon_nombre"] == "2A" and fila["grado"] == 2

        # Con salones, la organización no se puede borrar y el estudiante no cambia de organización
        r = await c.delete(f"/api/admin/organizations/{org}", headers=admin_headers())
        assert r.status_code == 409
        otra = await _org(c)
        r = await c.put(f"/api/admin/organizations/{otra}/students/{est}", headers=admin_headers())
        assert r.status_code == 409
