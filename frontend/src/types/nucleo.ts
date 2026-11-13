/**
 * Tipos de la API del núcleo de práctica (/api/nucleo).
 *
 * El problema llega en su vista pública: sin respuestas correctas, sin los datos internos del
 * generador y sin la regla de error de cada opción del banco (backend/app/nucleo/problema.py).
 */

// ─── Problema ────────────────────────────────────────────────────────────────

export type Segmento =
  | { tipo: 'texto'; texto: string }
  | { tipo: 'numero'; valor: string }
  | { tipo: 'fraccion'; numerador: number; denominador: number }
  | { tipo: 'simbolo'; simbolo: string }
  | { tipo: 'hueco'; hueco_id: string };

export interface OpcionHueco {
  id: string;
  texto: string;
}

export type Hueco =
  | { id: string; tipo: 'numero'; banco?: { valor: string }[] }
  | { id: string; tipo: 'opcion'; opciones: OpcionHueco[] }
  | { id: string; tipo: 'fraccion' }
  | { id: string; tipo: 'cantidad'; unidades: string[] };

export type ModoRespuesta = 'banco' | 'teclado';

export interface ModosProblema {
  mostrar_signo: boolean;
  mostrar_iconos: boolean;
  respuesta: ModoRespuesta;
  opciones_banco: number;
}

interface ProblemaBase {
  esquema: number;
  leccion_id: string;
  generador_version: number;
  modos: ModosProblema;
  /** Cuántos íconos lleva cada operando, si se muestran */
  iconos: number[] | null;
}

/**
 * Enunciado con plantilla (1.º y 2.º, sin LLM). El backend elige la situación y la variante; la
 * pantalla arma el texto con el tema narrativo del estudiante (utils/nucleo/plantillas.ts).
 * `cantidades` son los números del problema que se ven, nunca la respuesta; los íconos salen de
 * las mismas cantidades.
 */
export interface EnunciadoPlantilla {
  situacion: string;
  variante: number;
  cantidades: number[];
  /** Con tres números: qué pasa en cada paso ("agregar" o "quitar") */
  acciones?: string[];
}

interface SemirrectaBase {
  tipo: 'semirrecta';
  desde: number;
  hasta: number;
  marcas_cada: number;
  etiquetas_cada: number;
}

/** Semirrecta numérica con el punto de partida y los saltos (fase 5a: resolver y anotar) */
export interface PresentacionSemirrecta extends SemirrectaBase {
  /** Los problemas de la fase 5a no lo traen: vale 'saltos' */
  ejercicio?: 'saltos';
  inicio: number;
  salto: number;
  saltos: number;
  sentido: 'derecha' | 'izquierda';
  /** Solo cuando el ejercicio es anotar la operación que muestran los saltos */
  llegada?: number;
}

/** Flecha que señala un número de la semirrecta; con etiqueta (A, B, C) en "ubicar" */
export interface FlechaSemirrecta {
  valor: number;
  etiqueta: string | null;
}

/** Semirrecta con flechas (fase 5b): leer el número que señala una flecha, o ubicar un número */
export interface PresentacionSemirrectaPuntos extends SemirrectaBase {
  ejercicio: 'leer' | 'ubicar';
  flechas: FlechaSemirrecta[];
  /** Números que no se escriben (U4 L2: los que hay que leer) */
  ocultas: number[];
}

/** Íconos que se cuentan: son el problema mismo, se dibujan siempre (fase 5b) */
export interface PresentacionConteo {
  tipo: 'conteo';
  cantidades: number[];
}

export type Presentacion = PresentacionSemirrecta | PresentacionSemirrectaPuntos | PresentacionConteo;

export interface ProblemaExpresion extends ProblemaBase {
  forma: 'expresion';
  segmentos: Segmento[];
  huecos: Hueco[];
  enunciado?: EnunciadoPlantilla | null;
  presentacion?: Presentacion | null;
}

export interface ProblemaOrdenar extends ProblemaBase {
  forma: 'ordenar';
  numeros: string[];
  ascendente: boolean;
  enunciado?: EnunciadoPlantilla | null;
}

export type Problema = ProblemaExpresion | ProblemaOrdenar;

// ─── Respuestas ──────────────────────────────────────────────────────────────

export interface ValorFraccion {
  numerador: string;
  denominador: string;
}

/** Valor de un hueco en pantalla: número u opción (texto), fracción o cantidad por unidad */
export type ValorHueco = string | ValorFraccion | Record<string, string>;

export type Respuestas = Record<string, ValorHueco | undefined>;

export interface EventoNucleo {
  tipo: string;
  valor?: unknown;
  /** ms desde que se mostró el problema */
  ms?: number;
}

// ─── API ─────────────────────────────────────────────────────────────────────

export interface SesionNucleo {
  sesion_id: number;
  estado: string;
  cantidad_problemas: number;
  progreso: number;
  fecha_inicio?: string | null;
}

export interface SesionActivaNucleo extends SesionNucleo {
  minutos_transcurridos: number;
}

export interface EstadoNucleo {
  disponible: boolean;
  sesion_activa: SesionActivaNucleo | null;
}

export interface ProblemaTurno {
  sesion_completada: boolean;
  problema_sesion_id?: number | null;
  orden?: number | null;
  problema?: Problema | null;
  intentos_restantes?: number | null;
  pistas_habilitadas?: Record<string, boolean> | null;
}

export interface EnvioRespuesta {
  respuestas: Record<string, unknown>;
  tiempo_ms: number;
  uso_voz: boolean;
  eventos: EventoNucleo[];
}

export interface ResultadoRespuesta {
  correcto: boolean;
  huecos: Record<string, boolean>;
  intentos_restantes: number;
  problema_terminado: boolean;
  solucion: Record<string, unknown> | null;
  experiencia_ganada: number;
  evento_dominio: string | null;
  sesion_completada: boolean;
}

// ─── Profesor: lecciones del salón (fase 6a) ─────────────────────────────────

export type ModoLeccion = 'siempre' | 'nunca' | 'azar';
export type PistasLeccion = Record<'1' | '2' | '3', boolean>;

/** Lección del catálogo con su estado en el año lectivo del salón */
export interface LeccionSalon {
  id: string;
  grado: number;
  unidad_numero: number;
  unidad_titulo: string;
  leccion_numero: number;
  leccion_titulo: string;
  orden_programa: number;
  incluida: boolean;
  motivo_exclusion: string | null;
  parcial: boolean;
  nota_parcial: string | null;
  presentacion_especial: string | null;
  cubierta_por: string | null;
  caminos: string[];
  /** Los que se aplican en este año (los del programa si no se editaron) */
  prerrequisitos: string[];
  prerrequisitos_programa: string[];
  prerrequisitos_editados: boolean;
  tiene_generador: boolean;
  habilitada: boolean;
  signo: ModoLeccion;
  iconos: ModoLeccion;
  pistas: PistasLeccion;
  prioritaria: boolean;
}

export interface ConfigLeccion {
  signo: ModoLeccion;
  iconos: ModoLeccion;
  pistas: PistasLeccion;
  prioritaria: boolean;
}

export interface AsignacionNucleo {
  id: number;
  anio_lectivo_id: number;
  estudiante_id: number;
  leccion_id: string;
  estado: 'activa' | 'cerrada_por_dominio' | 'cancelada';
  fecha_asignacion: string;
  fecha_cierre: string | null;
  leccion_titulo: string;
  estudiante_nombre: string;
}

export interface AjusteEstudiante {
  estudiante_id: number;
  banco_forzado: boolean;
}
