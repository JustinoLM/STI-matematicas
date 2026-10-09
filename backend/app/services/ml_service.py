"""
Service de Machine Learning para sistema adaptativo.

Implementa clustering de perfiles (K-means por organización) y predicción de
preparación para subir de nivel (regresión logística global).

Persistencia: los modelos entrenados se guardan como bytes (pickle) en la
tabla `modelo_ml` de PostgreSQL para sobrevivir reinicios del servidor
(Railway recrea el filesystem en cada deploy).
"""

import asyncio
import bisect
import logging
import pickle
from collections import defaultdict
from datetime import datetime
from itertools import permutations
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import EstadoSesion, PerfilAprendizaje, PerfilEstudiante, SesionPractica
from app.models.ml_model import ModeloML
from app.models.problem import Intento
from app.models.user import Estudiante

logger = logging.getLogger(__name__)


class MLService:
    """
    Service de Machine Learning para personalización adaptativa.

    Componentes:
    1. Clustering de perfiles (K-means, k=4) — entrenado por organización
    2. Predicción de preparación (Regresión Logística) — global, entrenada con el
       histórico de sesiones (ver `construir_historico`)

    Los modelos residen en memoria (_org_models, prediccion_model).
    Se persisten en PostgreSQL y se recargan en el startup del servidor.
    """

    # Perfiles que se asignan a los 4 clústeres. El número de clúster que
    # devuelve K-means es arbitrario (depende de la inicialización), así que la
    # correspondencia clúster → perfil se calcula a partir de los centroides
    # (ver `_asignar_perfiles_a_clusters`), no de un diccionario fijo.
    N_CLUSTERS = 4
    PERFILES_ORDEN = (
        PerfilAprendizaje.RAPIDO_PRECISO,
        PerfilAprendizaje.CUIDADOSO_METODICO,
        PerfilAprendizaje.IMPULSIVO,
        PerfilAprendizaje.EN_DESARROLLO,
    )

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
        self.prediccion_model: Optional[Pipeline] = None

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
            logger.warning(f"Org {org_id}: Insuficientes estudiantes: {len(estudiantes)}/10")
            return

        features = [
            self._extraer_features_perfil(p)
            for p in estudiantes
            if self._tiene_datos_suficientes(p)
        ]

        if len(features) < 10:
            logger.warning(
                f"Org {org_id}: Insuficientes perfiles válidos: {len(features)}/10"
            )
            return

        X = np.array(features)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        modelo = KMeans(n_clusters=self.N_CLUSTERS, random_state=42, n_init=10)
        modelo.fit(X_scaled)

        # Guardar en memoria
        self._org_models[org_id] = (modelo, scaler)
        logger.info(f"Org {org_id}: Clustering entrenado con {len(features)} estudiantes")

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
        perfil_aprendizaje = self._asignar_perfiles_a_clusters(modelo).get(
            int(cluster), PerfilAprendizaje.NO_CLASIFICADO
        )

        return perfil_aprendizaje, confianza

    def _asignar_perfiles_a_clusters(self, modelo: KMeans) -> Dict[int, PerfilAprendizaje]:
        """
        Asigna un perfil de aprendizaje a cada clúster interpretando sus centroides.

        Los centroides están en el espacio estandarizado de las features
        [velocidad, precisión, varianza, log(sesiones), nivel]. Con z_prec (precisión)
        y z_vel (tiempo por problema, mayor = más lento):

        - Rápido y preciso:     precisión alta, tiempo bajo   → z_prec − z_vel
        - Cuidadoso y metódico: precisión alta, tiempo alto   → z_prec + z_vel
        - Impulsivo:            precisión baja, tiempo bajo   → −z_prec − z_vel
        - En desarrollo:        precisión baja, tiempo alto   → −z_prec + z_vel

        Se elige la asignación uno a uno (clúster ↔ perfil) que maximiza la suma
        de puntajes; con 4 clústeres se prueban las 24 permutaciones. El resultado
        depende solo de los centroides, no del número arbitrario de cada clúster.
        """
        centros = np.asarray(modelo.cluster_centers_)
        if centros.shape[0] != len(self.PERFILES_ORDEN):
            return {}
        z_vel = centros[:, 0]
        z_prec = centros[:, 1]
        puntajes = np.column_stack(
            [z_prec - z_vel, z_prec + z_vel, -z_prec - z_vel, -z_prec + z_vel]
        )
        mejor = max(
            permutations(range(len(self.PERFILES_ORDEN))),
            key=lambda perm: sum(puntajes[c, perm[c]] for c in range(len(perm))),
        )
        return {c: self.PERFILES_ORDEN[mejor[c]] for c in range(len(mejor))}

    def describir_clusters(self, org_id: int) -> List[Dict]:
        """Centroides (en unidades originales) y perfil asignado a cada clúster de una org."""
        modelo, scaler = self._get_org_model(org_id)
        if modelo is None or scaler is None:
            return []
        asignacion = self._asignar_perfiles_a_clusters(modelo)
        centros = scaler.inverse_transform(modelo.cluster_centers_)
        return [
            {
                "cluster": c,
                "perfil": asignacion.get(c, PerfilAprendizaje.NO_CLASIFICADO).value,
                "velocidad_promedio": float(fila[0]),
                "precision": float(fila[1]),
                "desviacion_velocidad": float(fila[2]),
                "sesiones": float(np.expm1(fila[3])),
                "nivel_actual": float(fila[4]),
            }
            for c, fila in enumerate(centros)
        ]

    def evaluar_k(
        self,
        estudiantes: List[PerfilEstudiante],
        k_min: int = 3,
        k_max: int = 6,
    ) -> List[Dict]:
        """
        Evalúa distintos valores de k con las mismas features y normalización
        que el entrenamiento. Devuelve, por cada k válido, la inercia (método del
        codo) y el coeficiente de silueta. No modifica ningún modelo.

        Un k solo es válido si hay más muestras que clústeres (la silueta lo exige).
        """
        features = [
            self._extraer_features_perfil(p)
            for p in estudiantes
            if self._tiene_datos_suficientes(p)
        ]
        if len(features) < 2:
            return []
        X_scaled = StandardScaler().fit_transform(np.array(features))
        resultados = []
        for k in range(k_min, k_max + 1):
            if len(features) <= k:
                continue
            km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_scaled)
            resultados.append(
                {
                    "k": k,
                    "muestras": len(features),
                    "inercia": float(km.inertia_),
                    "silueta": float(silhouette_score(X_scaled, km.labels_)),
                }
            )
        return resultados

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
    # Predicción de Preparación (regresión logística)
    # ============================================================

    # Definición de "éxito": el estudiante sube de nivel (nivel general o de
    # alguna operación) en la sesión actual o en alguna de las siguientes
    # VENTANA_EXITO_SESIONES - 1 sesiones completadas.
    VENTANA_EXITO_SESIONES = 3
    MIN_EJEMPLOS_PREDICCION = 20
    MIN_EJEMPLOS_POR_CLASE = 3
    FEATURES_PREDICCION = (
        "nivel_actual",
        "precision",
        "velocidad",
        "sesiones_en_nivel",
        "perfectas_consecutivas",
        "dias_desde_promocion",
    )

    @property
    def prediccion_entrenada(self) -> bool:
        return self.prediccion_model is not None

    @staticmethod
    def _hubo_subida(cambios_nivel) -> bool:
        """True si el registro `cambios_nivel` de una sesión contiene alguna subida."""
        if not cambios_nivel:
            return False
        return any(
            isinstance(c, dict) and c.get("despues", 0) > c.get("antes", 0)
            for c in cambios_nivel.values()
        )

    def _ejemplos_de_estudiante(self, sesiones: List, intentos: List[Tuple]) -> List[Dict]:
        """
        Construye los ejemplos de entrenamiento de un estudiante.

        Args:
            sesiones: sesiones completadas, de la más antigua a la más reciente.
                Cada una con `nivel_actual_inicio`, `fecha_inicio`,
                `es_practica_perfecta` y `cambios_nivel`.
            intentos: tuplas (timestamp, es_correcto, tiempo_resolucion) ordenadas.

        Cada sesión k ≥ 1 es un ejemplo cuyas features describen al estudiante
        ANTES de empezarla. La etiqueta `exito` es 1 si hubo una subida de nivel
        en las sesiones k..k+VENTANA-1; es 0 solo si esa ventana está completa
        (así no se etiqueta como fracaso a quien aún no tuvo tiempo de subir).
        """
        n = len(sesiones)
        subidas = [self._hubo_subida(s.cambios_nivel) for s in sesiones]
        marcas = [i[0] for i in intentos]
        ejemplos: List[Dict] = []

        inicio_racha_nivel = 0   # índice de la primera sesión del nivel_actual vigente
        perfectas = 0            # racha de prácticas perfectas antes de la sesión k
        for k, sesion in enumerate(sesiones):
            if k > 0:
                if sesion.nivel_actual_inicio != sesiones[k - 1].nivel_actual_inicio:
                    inicio_racha_nivel = k
                perfectas = perfectas + 1 if sesiones[k - 1].es_practica_perfecta else 0
            if k == 0:
                continue

            previos = intentos[: bisect.bisect_left(marcas, sesion.fecha_inicio)]
            ult15 = previos[-15:]
            ult20 = previos[-20:]
            precision = (
                sum(1 for _, ok, _ in ult15 if ok) / len(ult15) if ult15 else 0.5
            )
            velocidad = (
                sum(t for _, _, t in ult20) / len(ult20) if ult20 else 30.0
            )
            dias = max((sesion.fecha_inicio - sesiones[inicio_racha_nivel].fecha_inicio).days, 0)

            ventana = subidas[k : k + self.VENTANA_EXITO_SESIONES]
            if any(ventana):
                exito = True
            elif k + self.VENTANA_EXITO_SESIONES <= n:
                exito = False
            else:
                continue  # ventana incompleta y sin subida: no se puede etiquetar

            ejemplos.append(
                {
                    "nivel_actual": int(sesion.nivel_actual_inicio or 1),
                    "precision": float(precision),
                    "velocidad": float(velocidad),
                    "sesiones_en_nivel": k - inicio_racha_nivel,
                    "perfectas_consecutivas": perfectas,
                    "dias_desde_promocion": dias,
                    "exito": exito,
                }
            )
        return ejemplos

    async def construir_historico(self, session: AsyncSession) -> List[Dict]:
        """Reconstruye, desde las sesiones e intentos guardados, el histórico de entrenamiento."""
        sesiones_res = await session.execute(
            select(SesionPractica)
            .where(
                SesionPractica.estado == EstadoSesion.COMPLETADA,
                SesionPractica.fecha_fin.isnot(None),
            )
            .order_by(SesionPractica.estudiante_id, SesionPractica.fecha_inicio)
        )
        intentos_res = await session.execute(
            select(
                Intento.estudiante_id,
                Intento.timestamp,
                Intento.es_correcto,
                Intento.tiempo_resolucion,
            ).order_by(Intento.estudiante_id, Intento.timestamp)
        )

        sesiones_por_est: Dict[int, List] = defaultdict(list)
        for sesion in sesiones_res.scalars().all():
            sesiones_por_est[sesion.estudiante_id].append(sesion)
        intentos_por_est: Dict[int, List[Tuple]] = defaultdict(list)
        for est_id, ts, ok, t in intentos_res.all():
            intentos_por_est[est_id].append((ts, bool(ok), t or 0))

        historico: List[Dict] = []
        for est_id, sesiones in sesiones_por_est.items():
            historico.extend(self._ejemplos_de_estudiante(sesiones, intentos_por_est.get(est_id, [])))
        return historico

    def entrenar_prediccion(self, historico: List[Dict]) -> bool:
        """
        Entrena la regresión logística global de preparación para subir de nivel.

        Requiere al menos MIN_EJEMPLOS_PREDICCION ejemplos y MIN_EJEMPLOS_POR_CLASE
        de cada clase (éxito / no éxito). Las features se estandarizan dentro de un
        Pipeline y las clases se balancean, porque las subidas son menos frecuentes
        que las sesiones sin subida.

        Returns:
            True si se entrenó un modelo nuevo.
        """
        positivos = sum(1 for e in historico if e["exito"])
        negativos = len(historico) - positivos
        if (
            len(historico) < self.MIN_EJEMPLOS_PREDICCION
            or min(positivos, negativos) < self.MIN_EJEMPLOS_POR_CLASE
        ):
            logger.warning(
                f"Predicción: datos insuficientes ({len(historico)} ejemplos, "
                f"{positivos} con éxito y {negativos} sin éxito)."
            )
            return False

        X = np.array([[e[f] for f in self.FEATURES_PREDICCION] for e in historico], dtype=float)
        y = np.array([1 if e["exito"] else 0 for e in historico])

        self.prediccion_model = Pipeline(
            [
                ("escala", StandardScaler()),
                (
                    "logistica",
                    LogisticRegression(random_state=42, max_iter=1000, class_weight="balanced"),
                ),
            ]
        ).fit(X, y)
        logger.info(f"Predicción entrenada con {len(historico)} ejemplos ({positivos} con éxito)")
        return True

    def predecir_exito_nivel_siguiente(
        self,
        perfil: PerfilEstudiante,
        dias_desde_promocion: int,
    ) -> float:
        """
        Probabilidad (0-1) de que el estudiante suba de nivel en las próximas
        VENTANA_EXITO_SESIONES sesiones. Con el modelo entrenado usa la regresión
        logística; si aún no hay modelo, la heurística de respaldo.
        """
        if not self.prediccion_model:
            return self._heuristica_exito(perfil)

        features = {
            "nivel_actual": perfil.nivel_actual,
            "precision": float(perfil.precision_ultimos_15 or 0.5),
            "velocidad": float(perfil.velocidad_promedio or 30.0),
            "sesiones_en_nivel": perfil.sesiones_en_nivel_actual or 0,
            "perfectas_consecutivas": perfil.practicas_perfectas_consecutivas or 0,
            "dias_desde_promocion": dias_desde_promocion,
        }
        X = np.array([[features[f] for f in self.FEATURES_PREDICCION]], dtype=float)
        return float(self.prediccion_model.predict_proba(X)[0][1])

    def _heuristica_exito(self, perfil: PerfilEstudiante) -> float:
        """Heurística simple cuando no hay modelo entrenado."""
        precision = float(perfil.precision_ultimos_15 or 0.5)
        sesiones = perfil.sesiones_en_nivel_actual or 0

        prob_base = precision
        if sesiones >= 5:
            prob_base += 0.1
        if sesiones >= 10:
            prob_base += 0.1

        return min(prob_base, 1.0)

    # ============================================================
    # Entrenamiento completo (job diario y endpoint de administración)
    # ============================================================

    async def entrenar_y_clasificar(self, db: AsyncSession) -> Dict:
        """
        Entrena y guarda en la BD: el K-means de cada organización y la regresión
        logística global; luego reclasifica a todos los estudiantes. Hace commit.
        """
        perfiles = list((await db.execute(select(PerfilEstudiante))).scalars().all())
        org_map: Dict[int, int] = {
            row.id: row.organizacion_id
            for row in await db.execute(
                select(Estudiante.id, Estudiante.organizacion_id).where(
                    Estudiante.organizacion_id.isnot(None)
                )
            )
        }
        perfiles_por_org: Dict[int, List] = defaultdict(list)
        for p in perfiles:
            org_id = org_map.get(p.estudiante_id)
            if org_id:
                perfiles_por_org[org_id].append(p)

        # 1. K-means por organización
        orgs_entrenadas = 0
        for org_id, org_perfiles in perfiles_por_org.items():
            await asyncio.to_thread(self.entrenar_clustering, org_perfiles, org_id)
            if self.has_model_for_org(org_id):
                orgs_entrenadas += 1
                n_validos = sum(1 for p in org_perfiles if self._tiene_datos_suficientes(p))
                await self.save_org_model_to_db(org_id, db, perfiles_entrenados=n_validos)

        # 2. Regresión logística global
        historico = await self.construir_historico(db)
        prediccion_entrenada = await asyncio.to_thread(self.entrenar_prediccion, historico)
        if prediccion_entrenada:
            await self.save_prediccion_to_db(db)

        # 3. Reclasificar a todos con el modelo de su organización
        reclasificados = 0
        if orgs_entrenadas:
            ahora = datetime.utcnow()
            for perfil in perfiles:
                perfil_ml, confianza = self.predecir_perfil(perfil, org_map.get(perfil.estudiante_id))
                perfil.perfil_aprendizaje = perfil_ml
                perfil.confianza_perfil = round(confianza, 2)
                perfil.fecha_ultima_clasificacion = ahora
                perfil.umbral_promocion_personalizado = self.ajustar_umbral_segun_perfil(perfil)
                reclasificados += 1

        await db.commit()
        return {
            "orgs_entrenadas": orgs_entrenadas,
            "total_perfiles": len(perfiles),
            "perfiles_validos": sum(1 for p in perfiles if self._tiene_datos_suficientes(p)),
            "reclasificados": reclasificados,
            "ejemplos_prediccion": len(historico),
            "prediccion_entrenada": prediccion_entrenada,
        }

    # ============================================================
    # Personalización de Umbrales
    # ============================================================

    def ajustar_umbral_segun_perfil(self, perfil: PerfilEstudiante) -> int:
        """Retorna umbral personalizado según perfil ML."""
        return self.UMBRALES_POR_PERFIL.get(perfil.perfil_aprendizaje, 10)

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
            logger.warning(f"save_org_model_to_db: sin modelo en memoria para org {org_id}")
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
        logger.info(f"Org {org_id}: Clustering guardado en BD")

    async def save_prediccion_to_db(self, session: AsyncSession) -> None:
        """Persiste el modelo global de predicción en PostgreSQL."""
        if not self.prediccion_model:
            logger.warning("save_prediccion_to_db: sin modelo de predicción en memoria")
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
        logger.info("Predicción guardada en BD")

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
            logger.info("Predicción cargada desde BD")
            return True
        except Exception as e:
            logger.warning(f"Error deserializando modelo de predicción: {e}")
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
                logger.warning(f"Error cargando clustering org {fila.org_id}: {e}")

        # Cargar modelo de predicción global
        pred_cargado = await self.load_prediccion_from_db(session)

        logger.info(
            f"ML startup: {orgs_cargadas} modelos de clustering, "
            f"predicción={'OK' if pred_cargado else 'no disponible'}"
        )


# Instancia singleton
ml_service = MLService()
