"""
Modelos para sistema adaptativo y machine learning.

Incluye perfiles de estudiante, sesiones de práctica, diagnósticos y alertas.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, JSON, ForeignKey, Enum, Text, Date
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class PerfilAprendizaje(str, enum.Enum):
    """Perfiles identificados por clustering ML."""
    RAPIDO_PRECISO = "rapido_preciso"
    CUIDADOSO_METODICO = "cuidadoso_metodico"
    IMPULSIVO = "impulsivo"
    EN_DESARROLLO = "en_desarrollo"
    NO_CLASIFICADO = "no_clasificado"


class TipoAlerta(str, enum.Enum):
    """Tipos de alertas del sistema."""
    POSIBLE_TRAMPA = "posible_trampa"
    REZAGADO = "rezagado"
    INACTIVO = "inactivo"
    PROMOCION_RAPIDA = "promocion_rapida"
    DIFICULTAD_PERSISTENTE = "dificultad_persistente"
    EXCELENCIA = "excelencia"


class EstadoDiagnostico(str, enum.Enum):
    """Estado de la prueba diagnóstica."""
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"


class PerfilEstudiante(Base):
    """
    Perfil adaptativo del estudiante.
    
    Trackea niveles por operación, métricas de rendimiento y alertas.
    """
    __tablename__ = "perfil_estudiante"
    
    # Relación con estudiante (1-1)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), primary_key=True)
    
    # ============================================
    # Niveles por Operación (independientes)
    # ============================================
    nivel_suma = Column(Integer, default=1, nullable=False)
    nivel_resta = Column(Integer, default=1, nullable=False)
    nivel_multiplicacion = Column(Integer, default=1, nullable=False)
    nivel_division = Column(Integer, default=1, nullable=False)
    
    # Nivel general (piso que no baja)
    nivel_actual = Column(Integer, default=1, nullable=False)
    
    # ============================================
    # Contadores por Operación
    # ============================================
    consecutivas_correctas_suma = Column(Integer, default=0)
    consecutivas_correctas_resta = Column(Integer, default=0)
    consecutivas_correctas_mult = Column(Integer, default=0)
    consecutivas_correctas_div = Column(Integer, default=0)
    
    # ============================================
    # Métricas Generales
    # ============================================
    precision_ultimos_15 = Column(Numeric(5, 2), default=0.0)  # 0.00 - 1.00
    velocidad_promedio = Column(Numeric(6, 2), default=0.0)  # segundos/problema
    varianza_velocidad = Column(Numeric(6, 2), default=0.0)  # desviación estándar
    
    # ============================================
    # Diagnóstico Inicial
    # ============================================
    diagnostico_completado = Column(Boolean, default=False)
    fecha_diagnostico = Column(DateTime, nullable=True)
    
    # ============================================
    # Machine Learning
    # ============================================
    perfil_aprendizaje = Column(
        Enum(PerfilAprendizaje), 
        default=PerfilAprendizaje.NO_CLASIFICADO
    )
    confianza_perfil = Column(Numeric(3, 2), default=0.0)  # 0.00 - 1.00
    fecha_ultima_clasificacion = Column(DateTime, nullable=True)
    
    # Umbral personalizado por ML (override de default 10)
    umbral_promocion_personalizado = Column(Integer, nullable=True)
    
    # ============================================
    # Contadores de Sesiones
    # ============================================
    total_sesiones = Column(Integer, default=0)
    sesiones_en_nivel_actual = Column(Integer, default=0)
    practicas_perfectas_consecutivas = Column(Integer, default=0)
    
    # ============================================
    # Tracking de Promociones
    # ============================================
    fecha_ultima_promocion = Column(DateTime, nullable=True)
    historial_promociones = Column(JSON, default=list)  # Lista de cambios de nivel
    # Ejemplo: [{"fecha": "2024-01-20", "operacion": "suma", "de": 2, "a": 3}]
    
    # ============================================
    # Sistema de Alertas (para futuras features)
    # ============================================
    alertas_activas = Column(JSON, default=list)  # Flags de alertas
    # Ejemplo: ["posible_trampa", "rezagado"]
    
    ultima_actividad = Column(DateTime, default=datetime.utcnow)
    dias_sin_practicar = Column(Integer, default=0)
    
    # ============================================
    # Metadatos
    # ============================================
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="perfil")
    sesiones = relationship("SesionPractica", back_populates="perfil")
    alertas = relationship("AlertaEstudiante", back_populates="perfil")
    
    def __repr__(self):
        return f"<PerfilEstudiante(estudiante_id={self.estudiante_id}, nivel_actual={self.nivel_actual})>"


class PruebaDiagnostica(Base):
    """
    Prueba diagnóstica inicial para asignar niveles.
    
    8 problemas: 2 por operación (nivel 1 y nivel 2).
    Todos los estudiantes hacen la misma prueba para comparabilidad.
    """
    __tablename__ = "prueba_diagnostica"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    
    # Estado
    estado = Column(Enum(EstadoDiagnostico, values_callable=lambda x: [e.value for e in x]), default=EstadoDiagnostico.PENDIENTE)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    
    # IDs de los 8 problemas generados
    problemas_ids = Column(JSON, nullable=True)  # [1, 2, 3, 4, 5, 6, 7, 8]
    
    # Resultados por operación (2 problemas cada una)
    suma_nivel1_correcto = Column(Boolean, nullable=True)
    suma_nivel2_correcto = Column(Boolean, nullable=True)
    suma_tiempo_total = Column(Integer, nullable=True)  # segundos
    
    resta_nivel1_correcto = Column(Boolean, nullable=True)
    resta_nivel2_correcto = Column(Boolean, nullable=True)
    resta_tiempo_total = Column(Integer, nullable=True)
    
    mult_nivel1_correcto = Column(Boolean, nullable=True)
    mult_nivel2_correcto = Column(Boolean, nullable=True)
    mult_tiempo_total = Column(Integer, nullable=True)
    
    div_nivel1_correcto = Column(Boolean, nullable=True)
    div_nivel2_correcto = Column(Boolean, nullable=True)
    div_tiempo_total = Column(Integer, nullable=True)
    
    # Niveles asignados
    nivel_suma_asignado = Column(Integer, nullable=True)
    nivel_resta_asignado = Column(Integer, nullable=True)
    nivel_mult_asignado = Column(Integer, nullable=True)
    nivel_div_asignado = Column(Integer, nullable=True)
    nivel_actual_asignado = Column(Integer, nullable=True)
    
    # Caso especial: 8/8 correctos
    perfecto = Column(Boolean, default=False)
    
    # Relación
    estudiante = relationship("Estudiante", back_populates="diagnostico")
    
    def __repr__(self):
        return f"<PruebaDiagnostica(estudiante_id={self.estudiante_id}, estado={self.estado})>"


class EstadoSesion(str, enum.Enum):
    """Estados posibles de una sesión de práctica."""
    INICIADA = "iniciada"
    EN_PROGRESO = "en_progreso"
    PAUSADA = "pausada"
    COMPLETADA = "completada"
    ABANDONADA = "abandonada"


class SesionPractica(Base):
    """
    Sesión completa de práctica (10, 15 o 20 problemas).
    
    Trackea configuración, resultados y cambios de nivel.
    Soporta pausar/reanudar con timeout de 4 horas.
    """
    __tablename__ = "sesion_practica"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    perfil_id = Column(Integer, ForeignKey("perfil_estudiante.estudiante_id"), nullable=False)
    
    # Estado de la sesión
    estado = Column(Enum(EstadoSesion, values_callable=lambda x: [e.value for e in x]), default=EstadoSesion.INICIADA, nullable=False)
    progreso_actual = Column(Integer, default=0)  # Índice del problema actual (0-based)
    
    # Timestamps
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    fecha_ultima_actividad = Column(DateTime, default=datetime.utcnow)
    
    # Estado al inicio (snapshot)
    nivel_actual_inicio = Column(Integer)
    nivel_suma_inicio = Column(Integer)
    nivel_resta_inicio = Column(Integer)
    nivel_multiplicacion_inicio = Column(Integer)
    nivel_division_inicio = Column(Integer)
    
    # Configuración de la sesión
    cantidad_problemas = Column(Integer)  # 10, 15 o 20
    problemas_ids = Column(JSON)  # Lista de IDs de problemas
    operaciones_incluidas = Column(JSON)  # {"suma": 5, "mult": 5, ...}
    ratio_dificultad = Column(JSON)  # {"faciles": 0.5, "desafiantes": 0.5}
    
    # Resultados
    problemas_correctos = Column(Integer, default=0)
    problemas_incorrectos = Column(Integer, default=0)
    tiempo_total_segundos = Column(Integer, nullable=True)
    velocidad_promedio = Column(Numeric(6, 2), nullable=True)  # seg/problema
    
    # Flags
    es_practica_perfecta = Column(Boolean, default=False)
    
    # Cambios de nivel post-sesión
    cambios_nivel = Column(JSON, nullable=True)
    
    # Gamificación
    puntos_ganados = Column(Integer, default=0)
    desglose_puntos = Column(JSON, nullable=True)  # Detalle de cómo se calcularon los puntos
    # Ejemplo: {"suma": {"antes": 2, "despues": 3, "razon": "10 consecutivos"}}
    
    # ML predictions (para futuro análisis)
    perfil_al_momento = Column(String(50), nullable=True)
    probabilidad_exito_predicha = Column(Numeric(3, 2), nullable=True)
    
    # ============================================
    # Detección de Anomalías (para alertas futuras)
    # ============================================
    velocidad_sospechosa = Column(Boolean, default=False)  # Muy rápido
    patron_sospechoso = Column(Boolean, default=False)  # Patrón inusual
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="sesiones")
    perfil = relationship("PerfilEstudiante", back_populates="sesiones")
    intentos = relationship("Intento", back_populates="sesion")
    
    def __repr__(self):
        return f"<SesionPractica(id={self.id}, estudiante_id={self.estudiante_id}, perfecta={self.es_practica_perfecta})>"


class AlertaEstudiante(Base):
    """
    Alertas generadas por el sistema para profesores.
    
    Tipos: trampa, rezagado, inactivo, promoción rápida, etc.
    """
    __tablename__ = "alerta_estudiante"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False)
    perfil_id = Column(Integer, ForeignKey("perfil_estudiante.estudiante_id"), nullable=False)
    
    # Tipo y severidad
    tipo = Column(Enum(TipoAlerta), nullable=False)
    severidad = Column(String(20), default="info")  # info, warning, critical
    
    # Contenido
    titulo = Column(String(200), nullable=False)
    mensaje = Column(Text, nullable=False)
    datos_contexto = Column(JSON, nullable=True)  # Datos adicionales
    
    # Estado
    activa = Column(Boolean, default=True)
    leida = Column(Boolean, default=False)
    fecha_lectura = Column(DateTime, nullable=True)
    
    # Timestamps
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_resolucion = Column(DateTime, nullable=True)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="alertas")
    perfil = relationship("PerfilEstudiante", back_populates="alertas")
    
    def __repr__(self):
        return f"<AlertaEstudiante(id={self.id}, tipo={self.tipo}, activa={self.activa})>"


class ResultadoPostTest(Base):
    """
    Resultado del post-test final (activado por el admin).

    Misma estructura de 8 problemas que PruebaDiagnostica (niveles 2 y 3),
    pero los resultados NO modifican el perfil adaptativo del estudiante.
    Solo se registra para comparación pre-test → post-test.
    Único por estudiante (UniqueConstraint en estudiante_id).
    """
    __tablename__ = "resultado_post_test"

    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, unique=True)
    org_id = Column(Integer, ForeignKey("organizacion.id"), nullable=True)

    # Ciclo de vida
    completado = Column(Boolean, default=False, nullable=False)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)

    # IDs de los 8 problemas generados
    problemas_ids = Column(JSON, nullable=True)

    # Resultados por operación (nivel 1 = nivel 2 real, nivel 2 = nivel 3 real)
    suma_nivel1_correcto = Column(Boolean, nullable=True)
    suma_nivel2_correcto = Column(Boolean, nullable=True)
    suma_tiempo_total = Column(Integer, nullable=True)   # segundos

    resta_nivel1_correcto = Column(Boolean, nullable=True)
    resta_nivel2_correcto = Column(Boolean, nullable=True)
    resta_tiempo_total = Column(Integer, nullable=True)

    mult_nivel1_correcto = Column(Boolean, nullable=True)
    mult_nivel2_correcto = Column(Boolean, nullable=True)
    mult_tiempo_total = Column(Integer, nullable=True)

    div_nivel1_correcto = Column(Boolean, nullable=True)
    div_nivel2_correcto = Column(Boolean, nullable=True)
    div_tiempo_total = Column(Integer, nullable=True)

    # Niveles evaluados (solo para referencia, no se aplican)
    nivel_suma_evaluado = Column(Integer, nullable=True)
    nivel_resta_evaluado = Column(Integer, nullable=True)
    nivel_mult_evaluado = Column(Integer, nullable=True)
    nivel_div_evaluado = Column(Integer, nullable=True)

    # Snapshot de niveles del pre-test (tomado del perfil en el momento del post-test)
    pre_nivel_suma = Column(Integer, nullable=True)
    pre_nivel_resta = Column(Integer, nullable=True)
    pre_nivel_mult = Column(Integer, nullable=True)
    pre_nivel_div = Column(Integer, nullable=True)
    pre_nivel_actual = Column(Integer, nullable=True)

    # Totales
    total_correctos = Column(Integer, nullable=True)
    perfecto = Column(Boolean, default=False)

    # Relación
    estudiante = relationship("Estudiante", back_populates="post_test")

    def __repr__(self):
        return f"<ResultadoPostTest(estudiante_id={self.estudiante_id}, completado={self.completado})>"


class EstadisticaEstudiante(Base):
    """
    Estadísticas agregadas del estudiante por fecha.
    
    Permite tracking histórico del rendimiento y generar gráficos.
    """
    __tablename__ = "estadistica_estudiante"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiante.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    
    # Métricas diarias
    practicas_completadas = Column(Integer, nullable=False, default=0)
    problemas_resueltos = Column(Integer, nullable=False, default=0)
    problemas_correctos = Column(Integer, nullable=False, default=0)
    tiempo_total_minutos = Column(Integer, nullable=False, default=0)
    pistas_utilizadas = Column(Integer, nullable=False, default=0)
    
    # Relación
    estudiante = relationship("Estudiante", back_populates="estadisticas")
    
    def __repr__(self):
        return f"<EstadisticaEstudiante(id={self.id}, estudiante_id={self.estudiante_id}, fecha={self.fecha})>"
