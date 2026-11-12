/**
 * Tipos centralizados del sistema.
 */

// ==================== AUTH ====================
export type TipoUsuario = 'estudiante' | 'profesor';

export interface LoginRequest {
  codigo: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: Usuario;
  // Campos extras que evitan un segundo request al /me
  nombre_completo: string;
  codigo: string;
}

export interface Usuario {
  id: number;
  tipo_usuario: TipoUsuario;
  fecha_creacion: string;
  ultimo_acceso?: string;
  activo: boolean;
}

export interface Estudiante extends Usuario {
  tipo_usuario: 'estudiante';
  codigo_estudiante: string;
  nombre_completo: string;
  narrativa_seleccionada_id?: number;
}

export interface Profesor extends Usuario {
  tipo_usuario: 'profesor';
  codigo_profesor: string;
  nombre_completo: string;
  institucion?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: Estudiante | Profesor;
}

// ==================== ADAPTIVE ====================
export interface PerfilEstudiante {
  estudiante_id: number;
  nivel_actual: number;
  nivel_suma: number;
  nivel_resta: number;
  nivel_multiplicacion: number;
  nivel_division: number;
  precision_ultimos_15: number;
  velocidad_promedio: number;
  total_sesiones: number;
  ultima_actividad: string;
  dias_sin_practicar: number;
  // Campos adicionales del PerfilResponse del backend
  operaciones_disponibles: string[];
  operaciones_bloqueadas: string[];
  consecutivas_por_operacion: Record<string, number>;
  umbral_promocion: number;
  practicas_perfectas_consecutivas: number;
  diagnostico_completado?: boolean;
  grupo_nombre?: string;
  profesor_nombre?: string;
}

export type TipoAlerta = 
  | 'posible_trampa'
  | 'rezagado'
  | 'inactivo'
  | 'promocion_rapida'
  | 'dificultad_persistente'
  | 'excelencia';

export interface AlertaEstudiante {
  id: number;
  tipo: TipoAlerta;
  severidad: 'alta' | 'media' | 'baja';
  titulo: string;
  mensaje: string;
  activa: boolean;
  leida: boolean;
  fecha_creacion: string;
}

// ==================== PROBLEMS ====================
export type Operacion = 'SUMA' | 'RESTA' | 'MULTIPLICACION' | 'DIVISION';

export interface Problema {
  id: number;
  operacion: Operacion;
  numero1: number;
  numero2: number;
  resultado: number;
  nivel_dificultad: number;
  cantidad_decimales: number;
  pregunta: string;
}

export interface Intento {
  id: number;
  problema_id: number;
  respuesta_estudiante: number;
  es_correcto: boolean;
  tiempo_resolucion: number;
  timestamp: string;
}

// Validación granular para feedback por pasos
export interface RespuestaValidacion {
  esCorrecta: boolean;
  resultadoCorrecto: boolean;
  pasosIntermediosCorrectos?: boolean;
  detalles?: {
    paso: string;
    esperado: string;
    recibido: string;
    correcto: boolean;
  }[];
}

// ==================== PRACTICE ====================
export interface SesionPractica {
  id: number;
  estudiante_id: number;
  estado: 'iniciada' | 'en_progreso' | 'pausada' | 'completada' | 'abandonada';
  progreso_actual: number;
  cantidad_problemas: number;
  problemas_ids: number[];
  problemas_correctos: number;
  problemas_incorrectos: number;
  fecha_inicio: string;
  puntos_ganados: number;
}

// ==================== GAMIFICATION ====================
export interface Medalla {
  id: number;
  nombre: string;
  descripcion: string;
  categoria: string;
  icono_url: string;
  condicion_cantidad: number;
}

export interface Desbloqueable {
  id: number;
  nombre: string;
  categoria: 'tema' | 'fondo' | 'musica' | 'efectos';
  costo_puntos: number;
  asset_url: string;
  desbloqueado: boolean;
}

export interface EstadisticasEstudiante {
  puntos_totales: number;
  problemas_resueltos: number;
  precision_general: number;
  racha_actual: number;
  medallas_obtenidas: number;
}

// ==================== TEACHER ====================

/** Trimestre de la organización en un año (lo edita el administrador). */
export interface Trimestre {
  numero: number;
  fecha_inicio: string;
  fecha_fin: string;
}

/** Un salón en un año lectivo, visto por su profesor. */
export interface SalonResumen {
  anio_lectivo_id: number;
  salon_id: number;
  nombre: string;
  grado: number;
  anio: number;
  estado: 'activo' | 'cerrado';
  cerrado: boolean;
  cantidad_estudiantes: number;
  cantidad_grupos: number;
}

export interface EstudianteDelSalon {
  estudiante_id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  nivel_actual: number;
  precision_ultimos_15: number;
  fecha_ingreso: string;
}

export interface GrupoDelSalon {
  id: number;
  nombre: string;
  estudiantes_ids: number[];
}

export interface SalonDetalle extends SalonResumen {
  profesor_nombre: string;
  trimestres: Trimestre[];
  estudiantes: EstudianteDelSalon[];
  grupos: GrupoDelSalon[];
  configuracion: ConfiguracionPractica | null;
}

export interface CandidatoSalon {
  id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  salon_actual: string | null;
  en_este_salon: boolean;
}

/** Grupo: subconjunto opcional de estudiantes dentro de un salón (año lectivo). */
export interface Grupo {
  id: number;
  nombre: string;
  activo: boolean;
  anio_lectivo_id: number;
  salon_nombre: string;
  anio: number;
  cerrado: boolean;
  estudiantes_ids?: number[];
  cantidad_estudiantes: number;
  promedio_precision?: number;
  problemas_resueltos_hoy?: number;
  estudiantes?: EstudianteEnGrupo[];
}

export interface EstudianteEnGrupo {
  estudiante_id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  nivel_actual: number;
  precision_ultimos_15: number;
  fecha_ingreso: string;
  activo: boolean;
}

export interface EstadisticasGrupo {
  grupo_id: number;
  nombre_grupo: string;
  total_estudiantes: number;
  estudiantes_activos: number;
  estudiantes_inactivos: number;
  promedio_precision: number;
  promedio_velocidad: number;
  problemas_resueltos_total: number;
  problemas_resueltos_hoy: number;
  distribucion_niveles: Record<number, number>;
  estudiantes_rezagados: number;
  estudiantes_estancados: number;
  estudiantes_sobresalientes: number;
}

/** Tipos de desafío ordenados de más fácil (1) a más difícil (5). */
export type TipoDesafioGrupal =
  | 'problemas_resueltos'    // ⭐     Resolver X problemas en grupo
  | 'sesiones_completadas'   // ⭐⭐   Resolver X prácticas
  | 'practicas_sin_errores'  // ⭐⭐⭐  Resolver X prácticas con ≤ Y errores
  | 'problemas_rapidos'      // ⭐⭐⭐⭐ Resolver X problemas en ≤ Y seg/problema
  | 'practicas_rapidas';     // ⭐⭐⭐⭐⭐ Resolver X prácticas en ≤ Y minutos

export interface ContribuidorInfo {
  nombre: string;
  sesiones: number;
}

// Vista del desafío desde el lado del estudiante (endpoint /challenges/mis-desafios)
export interface DesafioEstudiante {
  id: number;
  nombre: string;
  descripcion?: string;
  tipo: TipoDesafioGrupal;
  objetivo_cantidad: number;
  parametro_adicional?: number;  // Parámetro Y (max errores / seg / min)
  recompensa_texto?: string;
  recompensa_puntos?: number;    // Puntos al completar
  fecha_creacion: string;
  fecha_limite?: string;
  completado: boolean;
  // Progreso del equipo del estudiante (grupo_id null = todo el salón)
  grupo_id: number | null;
  grupo_nombre: string;
  progreso_actual: number;
  porcentaje: number;
  grupo_completado: boolean;
  // Calculados en servidor
  dias_restantes?: number;
  esta_expirado: boolean;
  // Participación individual del estudiante
  mi_sesiones_en_ventana: number;   // Sesiones propias en la ventana
  califica_recompensa: boolean;     // True si cumple el mínimo de sesiones
  sesiones_para_calificar: number;  // Cuántas más necesita
  // Top contribuidores del grupo
  top_contribuidores: ContribuidorInfo[];
}

export interface DesafioGrupal {
  id: number;
  profesor_id: number;
  anio_lectivo_id: number;
  salon_nombre: string;
  anio: number;
  estado: 'activo' | 'completado' | 'no_completado';
  nombre: string;
  descripcion?: string;
  tipo: TipoDesafioGrupal;
  objetivo_cantidad: number;
  parametro_adicional?: number;  // Parámetro Y (max errores / seg / min)
  recompensa_texto?: string;
  recompensa_puntos?: number;    // XP al completar
  fecha_creacion: string;
  fecha_limite?: string;
  completado: boolean;
  vencido: boolean;  // true si fecha_limite pasó sin completarse
  eliminado: boolean;
  progreso_grupos: ProgresoGrupoDesafio[];
}

export interface ProgresoGrupoDesafio {
  grupo_id: number | null;  // null = todo el salón
  nombre_grupo: string;
  progreso_actual: number;
  objetivo_cantidad: number;
  porcentaje: number;
  completado: boolean;
}

export interface ConfiguracionPractica {
  id: number;
  anio_lectivo_id: number;
  operaciones_permitidas: string[];
  niveles_permitidos: number[];
  rango_min: number;
  rango_max: number;
  decimales_maximos: number;
  pistas_habilitadas: Record<string, boolean>;
  fecha_aplicacion: string;
  activa: boolean;
}

export interface AlertaEstudianteDetalle extends AlertaEstudiante {
  estudiante_id: number;
  codigo_estudiante: string;
  nombre_estudiante: string;
  datos_contexto?: Record<string, any>;
}

export interface ProgresoEstudiante {
  estudiante_id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  nivel_actual: number;
  total_problemas_resueltos: number;
  overall_accuracy: number;
  current_streak: number;
  max_streak: number;
  operations?: {
    operation: string;
    current_level: number;
    problems_solved: number;
    accuracy: number;
    progress_to_next_level: number;
  }[];
  recent_attempts?: {
    id: number;
    operation: string;
    level: number;
    is_correct: boolean;
    time_taken: number;
    created_at: string;
  }[];
}

// ==================== PISTAS ====================
export type NivelPista = 1 | 2 | 3;

export interface Pista {
  nivel: NivelPista;
  contenido: string;
  costo_puntos: number;
}

// ==================== SHOP ====================
// Re-exportar tipos de la tienda
export type {
  CategoriaDesbloqueable,
  RarezaItem,
  Desbloqueable as DesbloquableDetallado,
} from './shop';

export {
  TEMAS,
  FONDOS,
  COLORES,
  MUSICAS,
  EFECTOS,
  getTodosLosDesbloqueables,
  getDesbloqueablesPorCategoria,
  getDesbloquablesDisponibles,
  getFondosPorTema,
  getMusicasPorTema,
} from './shop';

// ==================== ESTADÍSTICAS DE GRUPO ====================

export interface ActividadDia {
  fecha: string;    // "YYYY-MM-DD"
  sesiones: number;
}

export interface PrecisionSemana {
  semana: string;      // "2026-W09"
  precision: number;   // 0 – 100
}

export interface DistribucionPerfiles {
  rapido_preciso: number;
  cuidadoso_metodico: number;
  impulsivo: number;
  en_desarrollo: number;
  no_clasificado: number;
}

export interface AlertaResumen {
  posible_trampa: number;
  rezagado: number;
  inactivo: number;
  promocion_rapida: number;
  dificultad_persistente: number;
  excelencia: number;
}

export interface NivelesOperacion {
  suma: number[];           // [count_nivel1, count_nivel2, ..., count_nivel5]
  resta: number[];
  multiplicacion: number[];
  division: number[];
}

export interface EstudianteStatsItem {
  id: number;
  nombre: string;
  codigo: string;
  // Niveles por operación
  nivel_suma: number;
  nivel_resta: number;
  nivel_multiplicacion: number;
  nivel_division: number;
  nivel_actual: number;
  // Métricas
  precision: number;           // 0–100
  velocidad_promedio: number;  // seg/problema
  total_sesiones: number;
  sesiones_esta_semana: number;
  dias_sin_practicar: number;
  // ML
  perfil_aprendizaje: string;
  confianza_perfil: number;    // 0–100
  probabilidad_avance: number; // 0–100
  // Alertas
  alertas: string[];
  // Actividad 14 días
  actividad_14_dias: ActividadDia[];
}

export interface GrupoStatsResponse {
  grupo_id: number;        // id del grupo o, con tipo "salon", del año lectivo
  grupo_nombre: string;
  tipo?: 'grupo' | 'salon';
  total_estudiantes: number;
  distribucion_perfiles: DistribucionPerfiles;
  resumen_alertas: AlertaResumen;
  niveles_por_operacion: NivelesOperacion;
  precision_semanal: PrecisionSemana[];
  actividad_grupal: ActividadDia[];
  estudiantes: EstudianteStatsItem[];
}

export interface AnalisisIAResponse {
  texto: string;
  generado_por_llm: boolean;
}
