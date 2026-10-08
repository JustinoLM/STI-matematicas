"""Regresión logística de preparación: definición de éxito, entrenamiento y persistencia."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.adaptive import PerfilEstudiante
from app.services.ml_service import MLService
from tests.conftest import TestSessionLocal

INICIO = datetime(2026, 5, 1, 9, 0)


def _sesion(i, nivel=2, perfecta=False, cambios=None):
    return SimpleNamespace(
        nivel_actual_inicio=nivel,
        fecha_inicio=INICIO + timedelta(days=i),
        es_practica_perfecta=perfecta,
        cambios_nivel=cambios,
    )


SUBIDA = {"+": {"antes": 2, "despues": 3, "razon": "10 consecutivos"}}


def _intentos(n_sesiones, correctos):
    """Un intento por sesión, el día de la sesión a las 09:30."""
    return [
        (INICIO + timedelta(days=i, minutes=30), correctos[i % len(correctos)], 10)
        for i in range(n_sesiones)
    ]


def test_hubo_subida():
    assert MLService._hubo_subida(SUBIDA) is True
    assert MLService._hubo_subida({"+": {"antes": 3, "despues": 2}}) is False   # bajada
    assert MLService._hubo_subida({}) is False and MLService._hubo_subida(None) is False


def test_etiqueta_exito_usa_una_ventana_de_tres_sesiones():
    ml = MLService()
    # subida en la sesión 3 → éxito para las sesiones 1, 2 y 3 (ventanas que la contienen)
    sesiones = [_sesion(0), _sesion(1), _sesion(2), _sesion(3, cambios=SUBIDA),
                _sesion(4), _sesion(5), _sesion(6), _sesion(7)]
    ej = ml._ejemplos_de_estudiante(sesiones, _intentos(8, [True]))
    por_k = {i + 1: e["exito"] for i, e in enumerate(ej)}   # el ejemplo i corresponde a la sesión i+1
    assert [por_k[1], por_k[2], por_k[3]] == [True, True, True]
    # sesión 4 en adelante: ventana completa y sin subida → fracaso confirmado
    assert por_k[4] is False and por_k[5] is False
    # las dos últimas sesiones (6 y 7) no tienen ventana completa y no se etiquetan
    assert len(ej) == 5


def test_no_se_etiqueta_como_fracaso_si_la_ventana_esta_incompleta():
    ml = MLService()
    sesiones = [_sesion(i) for i in range(4)]            # nunca suben
    ej = ml._ejemplos_de_estudiante(sesiones, _intentos(4, [True]))
    assert len(ej) == 1 and ej[0]["exito"] is False       # solo k=1 tiene 3 sesiones por delante


def test_features_describen_al_estudiante_antes_de_la_sesion():
    ml = MLService()
    sesiones = [_sesion(0, nivel=2, perfecta=True), _sesion(1, nivel=2, perfecta=True),
                _sesion(2, nivel=2), _sesion(3, nivel=3), _sesion(4, nivel=3), _sesion(5, nivel=3)]
    intentos = [(INICIO + timedelta(days=i, minutes=30), i % 2 == 0, 10 + i) for i in range(6)]
    ej = ml._ejemplos_de_estudiante(sesiones, intentos)
    e2 = ej[1]   # sesión 2: nivel 2, dos sesiones previas en el nivel, dos perfectas seguidas
    assert (e2["nivel_actual"], e2["sesiones_en_nivel"], e2["perfectas_consecutivas"]) == (2, 2, 2)
    assert e2["dias_desde_promocion"] == 2
    assert e2["precision"] == pytest.approx(0.5)          # intentos previos: True, False
    assert e2["velocidad"] == pytest.approx(10.5)
    e3 = ej[2]   # sesión 3: primera del nivel 3 → contadores reiniciados
    assert (e3["nivel_actual"], e3["sesiones_en_nivel"], e3["dias_desde_promocion"]) == (3, 0, 0)
    assert e3["perfectas_consecutivas"] == 0


def _historico_separable(n=60):
    """Éxito cuando la precisión previa es alta; fracaso cuando es baja."""
    h = []
    for i in range(n):
        alta = i % 2 == 0
        h.append({
            "nivel_actual": 2, "precision": 0.9 if alta else 0.3, "velocidad": 12.0,
            "sesiones_en_nivel": 4, "perfectas_consecutivas": 0,
            "dias_desde_promocion": 6, "exito": alta,
        })
    return h


def _perfil(precision):
    return SimpleNamespace(
        nivel_actual=2, precision_ultimos_15=precision, velocidad_promedio=12.0,
        sesiones_en_nivel_actual=4, practicas_perfectas_consecutivas=0,
    )


def test_entrenamiento_y_prediccion():
    ml = MLService()
    sin_modelo = ml.predecir_exito_nivel_siguiente(_perfil(0.9), 6)   # heurística
    assert ml.prediccion_entrenada is False and 0.0 <= sin_modelo <= 1.0

    assert ml.entrenar_prediccion(_historico_separable()) is True and ml.prediccion_entrenada
    alta = ml.predecir_exito_nivel_siguiente(_perfil(0.9), 6)
    baja = ml.predecir_exito_nivel_siguiente(_perfil(0.3), 6)
    assert alta > 0.7 and baja < 0.3


def test_no_entrena_con_pocos_datos_ni_con_una_sola_clase():
    ml = MLService()
    assert ml.entrenar_prediccion(_historico_separable(10)) is False
    una_clase = [dict(e, exito=True) for e in _historico_separable(40)]
    assert ml.entrenar_prediccion(una_clase) is False
    casi_una_clase = _historico_separable(40)
    for e in casi_una_clase[1:]:
        e["exito"] = True
    assert ml.entrenar_prediccion(casi_una_clase) is False        # solo 1 ejemplo negativo
    assert ml.prediccion_entrenada is False


@pytest.mark.asyncio
async def test_el_modelo_se_guarda_y_se_recarga_de_la_bd():
    ml = MLService()
    ml.entrenar_prediccion(_historico_separable())
    esperado = ml.predecir_exito_nivel_siguiente(_perfil(0.9), 6)
    async with TestSessionLocal() as db:
        await ml.save_prediccion_to_db(db)
        await db.commit()
        await ml.save_prediccion_to_db(db)    # segunda vez: actualiza, no duplica
        await db.commit()

        nuevo = MLService()
        assert nuevo.prediccion_entrenada is False
        assert await nuevo.load_prediccion_from_db(db) is True
        assert nuevo.predecir_exito_nivel_siguiente(_perfil(0.9), 6) == pytest.approx(esperado)


@pytest.mark.asyncio
async def test_construir_historico_desde_la_bd():
    from decimal import Decimal
    from app.models.adaptive import EstadoSesion, SesionPractica
    from app.models.problem import Intento, Operacion, Problema, TipoSesion
    from app.models.user import Estudiante, TipoUsuario

    async with TestSessionLocal() as db:
        est = Estudiante(codigo_estudiante="HIS001", password_hash="x", tipo_usuario=TipoUsuario.ESTUDIANTE,
                         nombre_completo="Estudiante de prueba")
        db.add(est)
        await db.flush()
        db.add(PerfilEstudiante(estudiante_id=est.id))
        prob = Problema(operacion=Operacion.SUMA, numero1=Decimal(1), numero2=Decimal(1), resultado=Decimal(2),
                        nivel_dificultad=1, cantidad_decimales=0, signature="h1")
        db.add(prob)
        await db.flush()
        for i in range(6):
            s = SesionPractica(
                estudiante_id=est.id, perfil_id=est.id, cantidad_problemas=1, problemas_ids=[prob.id],
                estado=EstadoSesion.COMPLETADA, nivel_actual_inicio=2,
                fecha_inicio=INICIO + timedelta(days=i), fecha_fin=INICIO + timedelta(days=i, minutes=20),
                cambios_nivel=SUBIDA if i == 2 else {},
            )
            db.add(s)
            await db.flush()
            db.add(Intento(estudiante_id=est.id, problema_id=prob.id, respuesta_estudiante=Decimal(2),
                           es_correcto=True, tiempo_resolucion=9, tipo_sesion=TipoSesion.PRACTICA,
                           sesion_id=s.id, timestamp=INICIO + timedelta(days=i, minutes=10)))
        await db.commit()

        historico = await MLService().construir_historico(db)
        # sesiones 1..3 tienen ventana completa (k+3 <= 6); la 1 y la 2 contienen la subida de la 2
        assert [e["exito"] for e in historico] == [True, True, False]
        assert set(historico[0]) == set(MLService.FEATURES_PREDICCION) | {"exito"}
