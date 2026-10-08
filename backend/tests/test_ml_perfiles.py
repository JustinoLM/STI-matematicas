"""Asignación de perfiles a clústeres de K-means por centroides y evaluación de k."""

from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.cluster import KMeans

from app.models.adaptive import PerfilAprendizaje as P
from app.services.ml_service import MLService

# Cuatro grupos bien separados: (velocidad s/problema, precisión, desviación de velocidad, nivel)
GRUPOS = {
    P.RAPIDO_PRECISO: (6.0, 0.95, 2.0, 3),
    P.CUIDADOSO_METODICO: (26.0, 0.92, 2.0, 3),
    P.IMPULSIVO: (6.0, 0.35, 6.0, 2),
    P.EN_DESARROLLO: (27.0, 0.40, 6.0, 2),
}


def _datos(semilla: int):
    rng = np.random.default_rng(semilla)
    X, y = [], []
    for perfil, (vel, prec, desv, nivel) in GRUPOS.items():
        for _ in range(15):
            X.append([
                vel + rng.normal(0, 0.8),
                prec + rng.normal(0, 0.02),
                desv + rng.normal(0, 0.1),
                np.log1p(10),
                nivel,
            ])
            y.append(perfil)
    return np.array(X), y


@pytest.mark.parametrize("semilla_kmeans", [0, 1, 7, 42, 123])
def test_el_perfil_no_depende_del_numero_de_cluster(semilla_kmeans):
    """Con otra inicialización cambian los números de clúster, pero no los perfiles."""
    X, y = _datos(3)
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(X)
    modelo = KMeans(n_clusters=4, random_state=semilla_kmeans, n_init=1).fit(scaler.transform(X))
    asignacion = MLService()._asignar_perfiles_a_clusters(modelo)

    assert sorted(p.value for p in asignacion.values()) == sorted(p.value for p in GRUPOS)
    for perfil_real, cluster in zip(y, modelo.labels_):
        assert asignacion[int(cluster)] == perfil_real


def _perfil_sintetico(vel, prec, desv=3.0, nivel=2, sesiones=10):
    return SimpleNamespace(
        velocidad_promedio=vel,
        precision_ultimos_15=prec,
        varianza_velocidad=desv,
        total_sesiones=sesiones,
        nivel_actual=nivel,
    )


def test_predecir_perfil_usa_los_centroides():
    ml = MLService()
    X, y = _datos(5)
    perfiles = [_perfil_sintetico(f[0], f[1], f[2], int(f[4])) for f in X]
    ml.entrenar_clustering(perfiles, org_id=1)
    assert ml.has_model_for_org(1)

    for objetivo, (vel, prec, desv, nivel) in GRUPOS.items():
        pred, confianza = ml.predecir_perfil(_perfil_sintetico(vel, prec, desv, nivel), org_id=1)
        assert pred == objetivo
        assert 0.0 <= confianza <= 1.0

    descripcion = ml.describir_clusters(1)
    assert len(descripcion) == 4
    assert {d["perfil"] for d in descripcion} == {p.value for p in GRUPOS}


def test_evaluar_k_devuelve_silueta_e_inercia():
    X, _ = _datos(9)
    perfiles = [_perfil_sintetico(f[0], f[1], f[2], int(f[4])) for f in X]
    res = MLService().evaluar_k(perfiles, 3, 6)
    assert [r["k"] for r in res] == [3, 4, 5, 6]
    assert all(-1.0 <= r["silueta"] <= 1.0 and r["inercia"] > 0 for r in res)
    # con 4 grupos bien separados, k = 4 debe tener la mejor silueta
    assert max(res, key=lambda r: r["silueta"])["k"] == 4


def test_evaluar_k_con_pocos_datos():
    assert MLService().evaluar_k([], 3, 6) == []
