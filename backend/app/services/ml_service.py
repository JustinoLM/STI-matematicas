"""
Service de Machine Learning para sistema adaptativo.

Implementa clustering de perfiles y predicción de preparación.
"""

import numpy as np
import joblib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.models.adaptive import PerfilEstudiante, PerfilAprendizaje


class MLService:
    """
    Service de Machine Learning para personalización adaptativa.

    Componentes:
    1. Clustering de perfiles (K-means, k=4) — entrenado por organización
    2. Predicción de preparación (Regresión Logística) — global
    """

    # Directorio para guardar modelos entrenados
    MODELS_DIR = Path("ml_models")

    # Perfiles identificados por clustering
    PERFILES = {
        0: PerfilAprendizaje.RAPIDO_PRECISO,
        1: PerfilAprendizaje.CUIDADOSO_METODICO,
        2: PerfilAprendizaje.IMPULSIVO,
        3: PerfilAprendizaje.EN_DESARROLLO
    }

    # Umbrales personalizados por perfil
    UMBRALES_POR_PERFIL = {
        PerfilAprendizaje.RAPIDO_PRECISO: 7,       # Subir más rápido
        PerfilAprendizaje.CUIDADOSO_METODICO: 12,  # Dar más tiempo
        PerfilAprendizaje.IMPULSIVO: 10,           # Estándar
        PerfilAprendizaje.EN_DESARROLLO: 15,       # Más tiempo en nivel
        PerfilAprendizaje.NO_CLASIFICADO: 10       # Default
    }

    def __init__(self):
        # Modelos por organización: {org_id: (KMeans, StandardScaler)}
        self._org_models: Dict[int, tuple] = {}
        self.prediccion_model: Optional[LogisticRegression] = None

        # Crear directorio de modelos si no existe
        self.MODELS_DIR.mkdir(exist_ok=True)

        # Cargar modelo de predicción global si existe
        self._load_prediccion_model()
    
    # ============================================
    # Clustering de Perfiles (por organización)
    # ============================================

    def _org_dir(self, org_id: int) -> Path:
        """Retorna (y crea si no existe) el directorio de modelos de una org."""
        d = self.MODELS_DIR / f"org_{org_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def has_model_for_org(self, org_id: int) -> bool:
        """Indica si existe un modelo de clustering entrenado para esta org."""
        modelo, _ = self._get_org_model(org_id)
        return modelo is not None

    def _get_org_model(self, org_id: int) -> tuple:
        """Retorna (KMeans, StandardScaler) para la org; carga desde disco si hace falta."""
        if org_id in self._org_models:
            return self._org_models[org_id]
        org_dir = self.MODELS_DIR / f"org_{org_id}"
        cp = org_dir / "clustering_model.pkl"
        sp = org_dir / "scaler.pkl"
        if cp.exists() and sp.exists():
            try:
                modelo = joblib.load(cp)
                scaler = joblib.load(sp)
                self._org_models[org_id] = (modelo, scaler)
                return modelo, scaler
            except Exception as e:
                print(f"⚠️  Error cargando modelos org {org_id}: {e}")
        return None, None

    def entrenar_clustering(self, estudiantes: List[PerfilEstudiante], org_id: int) -> None:
        """
        Entrena modelo de clustering para una organización específica.

        Requiere mínimo 10 estudiantes con datos suficientes.
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
            print(f"⚠️  Org {org_id}: Insuficientes perfiles válidos: {len(features)}/10")
            return

        X = np.array(features)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        modelo = KMeans(n_clusters=4, random_state=42, n_init=10)
        modelo.fit(X_scaled)

        # Guardar en memoria y en disco
        self._org_models[org_id] = (modelo, scaler)
        d = self._org_dir(org_id)
        joblib.dump(modelo, d / "clustering_model.pkl")
        joblib.dump(scaler, d / "scaler.pkl")

        import json
        with open(d / "metadata.json", "w") as f:
            json.dump({
                "fecha_entrenamiento": datetime.utcnow().isoformat(),
                "org_id": org_id,
                "perfiles_entrenados": len(features),
            }, f, indent=2)

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

        Args:
            perfil: Perfil del estudiante.
            org_id: ID de la organización. Si es None, se usan heurísticas.
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

        confianza = 1.0 - (distancia_min / distancia_max) if distancia_max > 0 else 1.0
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
            np.log1p(sesiones),  # Log para evitar outliers
            float(nivel)
        ]
    
    def _tiene_datos_suficientes(self, perfil: PerfilEstudiante) -> bool:
        """Verifica si el perfil tiene datos suficientes para clasificar."""
        return (
            perfil.total_sesiones >= 3 and
            perfil.velocidad_promedio is not None and
            perfil.precision_ultimos_15 is not None
        )

    def _clasificar_por_reglas(
        self, perfil: PerfilEstudiante
    ) -> Tuple[PerfilAprendizaje, float]:
        """
        Clasificación heurística basada en reglas cuando el modelo K-Means
        no está entrenado (pocos estudiantes en el sistema).

        Lógica:
          - RAPIDO_PRECISO:       precisión ≥ 80% Y velocidad ≤ 15 seg/problema
          - CUIDADOSO_METODICO:   precisión ≥ 75% Y velocidad > 15 seg/problema
          - IMPULSIVO:            precisión < 60% Y velocidad ≤ 12 seg/problema
          - EN_DESARROLLO:        resto (precisión baja o velocidad intermedia-alta)

        Confianza fija 0.55 — indica clasificación por reglas, no por ML.
        Cuando el modelo K-Means se entrene tomará el control con mayor precisión.
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

    # ============================================
    # Predicción de Preparación
    # ============================================
    
    def entrenar_prediccion(
        self,
        historico: List[Dict]
    ) -> None:
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
        
        # Separar features y target
        X = []
        y = []
        
        for ejemplo in historico:
            features = [
                ejemplo['nivel_actual'],
                ejemplo['consecutivas'],
                ejemplo['precision'],
                ejemplo['velocidad'],
                ejemplo['sesiones_en_nivel'],
                ejemplo['dias_desde_promocion']
            ]
            X.append(features)
            y.append(1 if ejemplo['exito'] else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Entrenar modelo
        self.prediccion_model = LogisticRegression(random_state=42, max_iter=1000)
        self.prediccion_model.fit(X, y)
        
        # Guardar modelo de predicción
        joblib.dump(self.prediccion_model, self.MODELS_DIR / "prediccion_model.pkl")

        print(f"✅ Predicción entrenada con {len(historico)} ejemplos")
    
    def predecir_exito_nivel_siguiente(
        self,
        perfil: PerfilEstudiante,
        dias_desde_promocion: int
    ) -> float:
        """
        Predice probabilidad de éxito en siguiente nivel.
        
        Returns:
            Probabilidad entre 0.0 y 1.0
        """
        if not self.prediccion_model:
            # Sin modelo entrenado, usar heurística
            return self._heuristica_exito(perfil)
        
        # Preparar features
        features = [
            perfil.nivel_actual,
            perfil.consecutivas_correctas_suma,  # Usar suma como proxy
            float(perfil.precision_ultimos_15 or 0.5),
            float(perfil.velocidad_promedio or 30.0),
            perfil.sesiones_en_nivel_actual,
            dias_desde_promocion
        ]
        
        X = np.array([features])
        
        # Predecir probabilidad
        probabilidad = self.prediccion_model.predict_proba(X)[0][1]
        
        return probabilidad
    
    def _heuristica_exito(self, perfil: PerfilEstudiante) -> float:
        """
        Heurística simple cuando no hay modelo entrenado.
        
        Basada en precisión y sesiones en nivel.
        """
        precision = float(perfil.precision_ultimos_15 or 0.5)
        sesiones = perfil.sesiones_en_nivel_actual
        
        # Más precisión y más sesiones = mayor probabilidad
        prob_base = precision
        
        if sesiones >= 5:
            prob_base += 0.1
        if sesiones >= 10:
            prob_base += 0.1
        
        return min(prob_base, 1.0)
    
    # ============================================
    # Personalización de Umbrales
    # ============================================
    
    def ajustar_umbral_segun_perfil(self, perfil: PerfilEstudiante) -> int:
        """
        Retorna umbral personalizado según perfil ML.
        
        Si no está clasificado, retorna umbral default (10).
        """
        perfil_aprendizaje = perfil.perfil_aprendizaje
        return self.UMBRALES_POR_PERFIL.get(
            perfil_aprendizaje,
            10  # Default
        )
    
    def calcular_umbral_dinamico(
        self,
        perfil: PerfilEstudiante,
        percentil_velocidad: Optional[int] = None
    ) -> int:
        """
        Calcula umbral dinámico combinando perfil ML y percentil de grupo.
        
        Args:
            perfil: Perfil del estudiante
            percentil_velocidad: Percentil de velocidad en el grupo (0-100)
        
        Returns:
            Umbral personalizado (3-15)
        """
        # Umbral base según perfil ML
        umbral_base = self.ajustar_umbral_segun_perfil(perfil)
        
        # Ajustar según percentil de grupo
        if percentil_velocidad is not None:
            if percentil_velocidad >= 90:
                umbral = 3  # Top 10%
            elif percentil_velocidad >= 80:
                umbral = 5  # Top 20%
            elif percentil_velocidad >= 70:
                umbral = 7  # Top 30%
            else:
                umbral = umbral_base
        else:
            umbral = umbral_base
        
        return umbral
    
    # ============================================
    # Persistencia de Modelos
    # ============================================

    def _load_prediccion_model(self) -> None:
        """Carga el modelo de predicción global desde disco si existe."""
        try:
            path = self.MODELS_DIR / "prediccion_model.pkl"
            if path.exists():
                self.prediccion_model = joblib.load(path)
                print("✅ Predicción model cargado")
        except Exception as e:
            print(f"⚠️  Error cargando modelo de predicción: {e}")


# Instancia singleton
ml_service = MLService()
