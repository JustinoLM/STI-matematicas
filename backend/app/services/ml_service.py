"""
Service de Machine Learning para sistema adaptativo.

Implementa clustering de perfiles y predicción de preparación.

Persistencia: los modelos entrenados se guardan como bytes (pickle) en la
tabla `modelo_ml` de PostgreSQL para sobrevivir reinicios del servidor
(Railway recrea el filesystem en cada deploy).
"""

import pickle
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import PerfilAprendizaje, PerfilEstudiante
from app.models.ml_model import ModeloML


class MLService:
    """
    Service de Machine Learning para personalización adaptativa.

    Componentes:
    1. Clustering de perfiles (K-means, k=4) — entrenado por organización
    2. Predicción de preparación (Regresión Logística) — global

    Los modelos residen en memoria (_org_models, prediccion_model).
    Se persisten en PostgreSQL y se recargan en el startup del servidor.
    """

    # Perfiles identificados por clustering
    PERFILES = {
        0: PerfilAprendizaje.RAPIDO_PRECISO,
        1: PerfilAprendizaje.CUIDADOSO_METODICO,
        2: PerfilAprendizaje.IMPULSIVO,
        3: PerfilAprendizaje.EN_DESARROLLO,
    }

    # Umbrales personalizados por perfil
    UMBRALES_POR_PERFIL = {
        PerfilAprendizaje.RAPIDO_PRECISO: 7,        # Subir más rápido
        PerfilAprendizaje.CUIDADOSO_METODICO: 12,   # Dar más tiempo
        PerfilAprendizaje.IMPULSIVO: 10,            # Estándar
        PerfilAprendizaje.EN_DESARROLLO: 15,        # Más tiempo en nivel
        PerfilAprendizaje.NO_CLASIFICADO: 10,       # Default
    }

    def __init__(self):
        # Modelos por organización: {org_id: (KMeans, StandardScaler)}
        self._org_models: Dict[int, tuple] = {}
        self.prediccion_model: Optional[LogisticRegression] = None

    # ============================================================
    # Clustering de Perfiles (por organización)
    # ============================================================

    def has_model_for_org(self, org_id: int) -> bool:
        """Indica si existe un modelo de clustering en memoria para esta org."""
        modelo, _ = self._get_org_model(org_id)
        return modelo is not None

    def _get_org_model(self, org_id: int) -> tuple:
        """Retorna (KMeans, StandardScaler) desde la caché en memoria."""
        return self._org_models.get(org_id, (None, None))

    def entrenar_clustering(
        self, estudiantes: List[PerfilEstudiante], org_id: int
    ) -> None:
        """
        Entrena modelo de clustering para una organización específica.
        Requiere mínimo 10 estudiantes con datos suficientes.

        Este método es síncrono (CPU-bound); llamarlo con
        `await asyncio.to_thread(...)` desde el endpoint async.
        Después de retornar, guardar en DB con `await save_org_model_to_db(...)`.
        """
        if len(estudiantes) < 10:
            print(f"⚠️  Org {org_id}: Insuficientes estudiantes: {len(estudiantes)}/10")
            return

        features = [
            self._extraer_features_perfil(p)
            for p in estudiantes
            if self._tiene_datos_suficientes(p)
        ]

        if len(features) < 10:
            print(
                f"⚠️  Org {org_id}: Insuficientes perfiles válidos: {len(features)}/10"
            )
            return

        X = np.array(features)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        modelo = KMeans(n_clusters=4, random_state=42, n_init=10)
        modelo.fit(X_scaled)

        # Guardar en memoria
        self._org_models[org_id] = (modelo, scaler)
        print(f"✅ Org {org_id}: Clustering entrenado con {len(features)} estudiantes")

    def predecir_perfil(
        self,
        perfil: PerfilEstudiante,
        org_id: Optional[int] = None,
    ) -> Tuple[PerfilAprendizaje, float]:
        """
        Predice el perfil de aprendizaje de un estudiante.

        Orden de preferencia:
        1. K-Means de la organización (mayor precisión)
        2. Reglas heurísticas (cuando no existe modelo para la org)
        3. NO_CLASIFICADO (cuando no hay suficientes datos del estudiante)
        """
        if not self._tiene_datos_suficientes(perfil):
            return PerfilAprendizaje.NO_CLASIFICADO, 0.0

        modelo, scaler = self._get_org_model(org_id) if org_id else (None, None)

        if not modelo or not scaler:
            return self._clasificar_por_reglas(perfil)

        features = self._extraer_features_perfil(perfil)
        X = np.array([features])
        X_scaled = scaler.transform(X)

        cluster = modelo.predict(X_scaled)[0]

        distancias = modelo.transform(X_scaled)[0]
        distancia_min = distancias[cluster]
        distancia_max = np.max(distancias)

        confianza = (
            1.0 - (distancia_min / distancia_max) if distancia_max > 0 else 1.0
        )
        perfil_aprendizaje = self.PERFILES.get(cluster, PerfilAprendizaje.NO_CLASIFICADO)

        return perfil_aprendizaje, confianza

    def _extraer_features_perfil(self, perfil: PerfilEstudiante) -> List[float]:
        """
        Extrae features de un perfil para clustering.

        Features:
        1. Velocidad promedio (normalizada)
        2. Precisión últimos 15
        3. Varianza de velocidad
        4. Total de sesiones (log)
        5. Nivel actual
        """
        velocidad = float(perfil.velocidad_promedio or 30.0)
        precision = float(perfil.precision_ultimos_15 or 0.5)
        varianza = float(perfil.varianza_velocidad or 10.0)
        sesiones = perfil.total_sesiones or 1
        nivel = perfil.nivel_actual

        return [
            velocidad,
            precision,
            varianza,
            np.log1p(sesiones),
            float(nivel),
        ]

    def _tiene_datos_suficientes(self, perfil: PerfilEstudiante) -> bool:
        """Verifica si el perfil tiene datos suficientes para clasificar."""
        return (
            perfil.total_sesiones >= 3
            and perfil.velocidad_promedio is not None
            and perfil.precision_ultimos_15 is not None
        )

    def _clasificar_por_reglas(
        self, perfil: PerfilEstudiante
    ) -> Tuple[PerfilAprendizaje, float]:
        """
        Clasificación heurística basada en reglas cuando el modelo K-Means
        no está entrenado (pocos estudiantes en el sistema).

        Confianza fija 0.55 — indica clasificación por reglas, no por ML.
        """
        precision = float(perfil.precision_ultimos_15 or 0.0)
        velocidad = float(perfil.velocidad_promedio or 30.0)

        if precision >= 0.80 and velocidad <= 15.0:
            return PerfilAprendizaje.RAPIDO_PRECISO, 0.55
        elif precision >= 0.75 and velocidad > 15.0:
            return PerfilAprendizaje.CUIDADOSO_METODICO, 0.55
        elif precision < 0.60 and velocidad <= 12.0:
            return PerfilAprendizaje.IMPULSIVO, 0.55
        else:
            return PerfilAprendizaje.EN_DESARROLLO, 0.55

    # ============================================================
    # Predicción de Preparación
    # ============================================================

    def entrenar_prediccion(self, historico: List[Dict]) -> None:
        """
        Entrena modelo de predicción de preparación.

        Args:
            historico: Lista de ejemplos históricos con estructura:
                {
                    'nivel_actual': int,
                    'consecutivas': int,
                    'precision': float,
                    'velocidad': float,
                    'sesiones_en_nivel': int,
                    'dias_desde_promocion': int,
                    'exito': bool  # Target
                }
        """
        if len(historico) < 20:
            print(f"⚠️  Insuficientes datos históricos: {len(historico)}/20")
            return

        X = []
        y = []

        for ejemplo in historico:
            features = [
                ejemplo["nivel_actual"],
                ejemplo["consecutivas"],
                ejemplo["precision"],
                ejemplo["velocidad"],
                ejemplo["sesiones_en_nivel"],
                ejemplo["dias_desde_promocion"],
            ]
            X.append(features)
            y.append(1 if ejemplo["exito"] else 0)

        X = np.array(X)
        y = np.array(y)

        self.prediccion_model = LogisticRegression(random_state=42, max_iter=1000)
        self.prediccion_model.fit(X, y)

        print(f"✅ Predicción entrenada con {len(historico)} ejemplos")

    def predecir_exito_nivel_siguiente(
        self,
        perfil: PerfilEstudiante,
        dias_desde_promocion: int,
    ) -> float:
        """
        Predice probabilidad de éxito en siguiente nivel.

        Returns:
            Probabilidad entre 0.0 y 1.0
        """
        if not self.prediccion_model:
            return self._heuristica_exito(perfil)

        features = [
            perfil.nivel_actual,
            perfil.consecutivas_correctas_suma,
            float(perfil.precision_ultimos_15 or 0.5),
            float(perfil.velocidad_promedio or 30.0),
            perfil.sesiones_en_nivel_actual,
            dias_desde_promocion,
        ]

        X = np.array([features])
        probabilidad = self.prediccion_model.predict_proba(X)[0][1]
        return probabilidad

    def _heuristica_exito(self, perfil: PerfilEstudiante) -> float:
        """Heurística simple cuando no hay modelo entrenado."""
        precision = float(perfil.precision_ultimos_15 or 0.5)
        sesiones = perfil.sesiones_en_nivel_actual

        prob_base = precision
        if sesiones >= 5:
            prob_base += 0.1
        if sesiones >= 10:
            prob_base += 0.1

        return min(prob_base, 1.0)

    # ============================================================
    # Personalización de Umbrales
    # ============================================================

    def ajustar_umbral_segun_perfil(self, perfil: PerfilEstudiante) -> int:
        """Retorna umbral personalizado según perfil ML."""
        return self.UMBRALES_POR_PERFIL.get(perfil.perfil_aprendizaje, 10)

    def calcular_umbral_dinamico(
        self,
        perfil: PerfilEstudiante,
        percentil_velocidad: Optional[int] = None,
    ) -> int:
        """
        Calcula umbral dinámico combinando perfil ML y percentil de grupo.

        Returns:
            Umbral personalizado (3-15)
        """
        umbral_base = self.ajustar_umbral_segun_perfil(perfil)

        if percentil_velocidad is not None:
            if percentil_velocidad >= 90:
                return 3
            elif percentil_velocidad >= 80:
                return 5
            elif percentil_velocidad >= 70:
                return 7

        return umbral_base

    # ============================================================
    # Persistencia en PostgreSQL (métodos async)
    # ============================================================

    async def save_org_model_to_db(
        self, org_id: int, session: AsyncSession, perfiles_entrenados: int = 0
    ) -> None:
        """
        Persiste el modelo de clustering de una org en PostgreSQL.
        Hace upsert: crea la fila si no existe, la actualiza si ya existe.
        """
        modelo, scaler = self._get_org_model(org_id)
        if modelo is None or scaler is None:
            print(f"⚠️  save_org_model_to_db: sin modelo en memoria para org {org_id}")
            return

        modelo_bytes = pickle.dumps(modelo)
        scaler_bytes = pickle.dumps(scaler)

        result = await session.execute(
            select(ModeloML).where(
                ModeloML.nombre == "clustering",
                ModeloML.org_id == org_id,
            )
        )
        fila = result.scalar_one_or_none()

        if fila:
            fila.modelo_bytes = modelo_bytes
            fila.scaler_bytes = scaler_bytes
            fila.entrenado_en = datetime.utcnow()
            fila.perfiles_entrenados = perfiles_entrenados
        else:
            fila = ModeloML(
                nombre="clustering",
                org_id=org_id,
                modelo_bytes=modelo_bytes,
                scaler_bytes=scaler_bytes,
                entrenado_en=datetime.utcnow(),
                perfiles_entrenados=perfiles_entrenados,
            )
            session.add(fila)

        await session.flush()
        print(f"✅ Org {org_id}: Clustering guardado en BD")

    async def load_org_model_from_db(
        self, org_id: int, session: AsyncSession
    ) -> bool:
        """
        Carga el modelo de clustering de una org desde PostgreSQL a memoria.

        Returns:
            True si se cargó correctamente, False si no había fila.
        """
        result = await session.execute(
            select(ModeloML).where(
                ModeloML.nombre == "clustering",
                ModeloML.org_id == org_id,
            )
        )
        fila = result.scalar_one_or_none()

        if not fila:
            return False

        try:
            modelo = pickle.loads(fila.modelo_bytes)
            scaler = pickle.loads(fila.scaler_bytes)
            self._org_models[org_id] = (modelo, scaler)
            print(f"✅ Org {org_id}: Clustering cargado desde BD")
            return True
        except Exception as e:
            print(f"⚠️  Error deserializando clustering org {org_id}: {e}")
            return False

    async def save_prediccion_to_db(self, session: AsyncSession) -> None:
        """Persiste el modelo global de predicción en PostgreSQL."""
        if not self.prediccion_model:
            print("⚠️  save_prediccion_to_db: sin modelo de predicción en memoria")
            return

        modelo_bytes = pickle.dumps(self.prediccion_model)

        result = await session.execute(
            select(ModeloML).where(
                ModeloML.nombre == "prediccion",
                ModeloML.org_id.is_(None),
            )
        )
        fila = result.scalar_one_or_none()

        if fila:
            fila.modelo_bytes = modelo_bytes
            fila.entrenado_en = datetime.utcnow()
        else:
            fila = ModeloML(
                nombre="prediccion",
                org_id=None,
                modelo_bytes=modelo_bytes,
                entrenado_en=datetime.utcnow(),
            )
            session.add(fila)

        await session.flush()
        print("✅ Predicción guardada en BD")

    async def load_prediccion_from_db(self, session: AsyncSession) -> bool:
        """
        Carga el modelo global de predicción desde PostgreSQL a memoria.

        Returns:
            True si se cargó correctamente, False si no había fila.
        """
        result = await session.execute(
            select(ModeloML).where(
                ModeloML.nombre == "prediccion",
                ModeloML.org_id.is_(None),
            )
        )
        fila = result.scalar_one_or_none()

        if not fila:
            return False

        try:
            self.prediccion_model = pickle.loads(fila.modelo_bytes)
            print("✅ Predicción cargada desde BD")
            return True
        except Exception as e:
            print(f"⚠️  Error deserializando modelo de predicción: {e}")
            return False

    async def load_all_from_db(self, session: AsyncSession) -> None:
        """
        Carga todos los modelos almacenados en BD a la caché en memoria.
        Llamar en el startup del servidor para evitar cold-start sin modelos.
        """
        # Cargar todos los registros de clustering
        result = await session.execute(
            select(ModeloML).where(ModeloML.nombre == "clustering")
        )
        filas_clustering = result.scalars().all()

        orgs_cargadas = 0
        for fila in filas_clustering:
            try:
                modelo = pickle.loads(fila.modelo_bytes)
                scaler = pickle.loads(fila.scaler_bytes)
                self._org_models[fila.org_id] = (modelo, scaler)
                orgs_cargadas += 1
            except Exception as e:
                print(f"⚠️  Error cargando clustering org {fila.org_id}: {e}")

        # Cargar modelo de predicción global
        pred_cargado = await self.load_prediccion_from_db(session)

        print(
            f"🤖 ML startup: {orgs_cargadas} modelos de clustering, "
            f"predicción={'OK' if pred_cargado else 'no disponible'}"
        )


# Instancia singleton
ml_service = MLService()
