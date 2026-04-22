/**
 * Servicio del estudiante — práctica, gamificación, pistas.
 */

import apiClient, { getErrorMessage } from './api';
import type { PerfilEstudiante, DesafioEstudiante } from '@/types';

// ─── Tipos de práctica ────────────────────────────────────────────────────────

export interface ProblemaBE {
  id: number;
  operacion: string;
  numero1: string | number;
  numero2: string | number;
  resultado?: string | number; // El backend NO lo envía al iniciar, pero lo tipamos por si acaso
  nivel_dificultad: number;
  cantidad_decimales: number;
  pregunta?: string;
}

export interface SesionStartResponse {
  sesion_id: number;
  cantidad_problemas: number;
  operaciones_incluidas: Record<string, number>;
  nivel_actual: number;
  problemas: ProblemaBE[];
  mensaje_intro: string;
}

export interface SesionActivaResponse {
  sesion_id: number;
  problemas_completados: number;
  cantidad_problemas: number;
  operaciones_incluidas: Record<string, number>;
  nivel_actual: number;
  minutos_transcurridos: number;
  fecha_inicio: string;
}

export interface SubmitProblemResponse {
  es_correcto: boolean;
  respuesta_correcta: string | null;
  intentos_restantes: number;
  mensaje: string;
  siguiente_problema: {
    sesion_id: number;
    problema_numero: number;
    total_problemas: number;
    problema: ProblemaBE;
    intentos_restantes: number;
    es_ultimo: boolean;
  } | null;
  sesion_completada: boolean;
}

// ─── Tipos de respuesta ──────────────────────────────────────────────────────

export interface SaldoPuntosResponse {
  estudiante_id: number;
  puntos_totales: number;
}

export interface ItemPoseido {
  id: number;
  categoria: string;
  nombre: string;
  descripcion: string | null;
  precio_puntos: number;
  nivel_minimo_requerido: number;
  archivo_referencia: string | null;
  poseido: boolean;
  es_tema_inicial: boolean;
  orden: number;
}

export interface PersonalizacionRequest {
  tema_activo_id?: number | null;
  fondo_activo_id?: number | null;
  musica_activa_id?: number | null;
  color_fondo?: string | null;
  color_texto?: string | null;
  color_botones?: string | null;
}

export interface PersonalizacionResponse {
  estudiante_id: number;
  tema_activo_id: number | null;
  fondo_activo_id: number | null;
  musica_activa_id: number | null;
  tema_activo_nombre: string | null;
  fondo_activo_nombre: string | null;
  musica_activa_nombre: string | null;
  color_fondo: string;
  color_texto: string;
  color_botones: string;
  efectos_activos: number[];
}

export interface ComprarItemResponse {
  exito: boolean;
  mensaje: string;
  item_comprado: ItemPoseido | null;
  puntos_gastados: number;
  saldo_nuevo: number;
}

export interface MedallaItem {
  id: number;
  nombre: string;
  descripcion: string;
  categoria: string;
  imagen_url: string | null;  // Ahora contiene el emoji directamente
  es_secreta: boolean;
  obtenida: boolean;
  fecha_obtencion: string | null;
  orden: number;
}

export interface MedallasResponse {
  total_medallas: number;
  medallas_obtenidas: number;
  medallas: MedallaItem[];
  medalla_destacada_id: number | null;
}

export interface RecompensasSesionResponse {
  sesion_id: number;
  puntos_ganados: number;
  desglose_puntos: Record<string, number>;
  saldo_total: number;
  medallas_nuevas: Array<{ id: number; nombre: string; descripcion: string; imagen_url: string | null }>;
  mensaje_motivacional: string;
}

// ─── Tipos de animaciones ─────────────────────────────────────────────────────

export interface AnimacionGuardadaResponse {
  id: number;
  problema_id: number;
  operacion: string;
  numero1: string;
  numero2: string;
  nivel_dificultad: number;
  guardado_en: string;
}

export interface GuardarAnimacionResponse {
  animacion: AnimacionGuardadaResponse;
  guardadas_total: number;
  maximo: number;
  ya_existia: boolean;
}

export interface ColeccionAnimacionesResponse {
  animaciones: AnimacionGuardadaResponse[];
  total: number;
  maximo: number;
}

// ─── Tipos de videos ──────────────────────────────────────────────────────────

export interface VideoEducativoResponse {
  id: number;
  titulo: string;
  descripcion: string | null;
  duracion_segundos: number;
  url: string;
  thumbnail_url: string | null;
  fuente: string;           // "youtube" | "generado"
  tipo_error: string;
  operacion: string;
  nivel_dificultad: number;
  guardado: boolean;
  fecha_guardado: string | null;
  visto: boolean;
  progreso_segundos: number;
}

export interface GaleriaVideosResponse {
  total: number;
  maximo: number;           // 10
  videos: VideoEducativoResponse[];
}

export interface GuardarVideoResponse {
  exito: boolean;
  mensaje: string;
  videos_guardados_total: number;
  video_eliminado: VideoEducativoResponse | null;
}

// ─── Servicio ────────────────────────────────────────────────────────────────

export const studentService = {
  // ── Perfil adaptativo ──────────────────────────────────────────────────────

  async getPerfil(): Promise<PerfilEstudiante> {
    try {
      const response = await apiClient.get<PerfilEstudiante>('/adaptive/profile');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Diagnóstico ────────────────────────────────────────────────────────────

  /**
   * Inicia la prueba diagnóstica (8 problemas, 2 por operación).
   * Ruta: POST /adaptive/diagnostic/start
   */
  async iniciarDiagnostico(): Promise<{ diagnostico_id: number; problemas: ProblemaBE[]; mensaje: string }> {
    try {
      const response = await apiClient.post('/adaptive/diagnostic/start');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Envía todas las respuestas del diagnóstico y obtiene los niveles asignados.
   * Ruta: POST /adaptive/diagnostic/submit
   */
  async enviarDiagnostico(
    diagnosticoId: number,
    respuestas: Record<number, number>,
    tiemposPorProblema?: Record<number, number>,
  ): Promise<{
    estudiante_id: number;
    perfecto: boolean;
    nivel_suma: number;
    nivel_resta: number;
    nivel_multiplicacion: number;
    nivel_division: number;
    nivel_actual: number;
    correctos_por_operacion: Record<string, number>;
    mensaje: string;
  }> {
    try {
      const response = await apiClient.post('/adaptive/diagnostic/submit', {
        diagnostico_id: diagnosticoId,
        respuestas,
        tiempos_por_problema: tiemposPorProblema,
      });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Práctica ───────────────────────────────────────────────────────────────

  /**
   * Iniciar sesión de práctica adaptativa.
   * Ruta: POST /adaptive/practice/start
   * El sistema decide automáticamente cantidad y operaciones.
   */
  async iniciarPractica(): Promise<SesionStartResponse> {
    try {
      const response = await apiClient.post<SesionStartResponse>('/adaptive/practice/start');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Enviar respuesta a un problema dentro de una sesión.
   * Ruta: POST /practices/{sesion_id}/submit-problem
   * El backend valida, registra el intento, y devuelve el siguiente problema.
   */
  async enviarRespuesta(
    sesionId: number,
    problemaId: number,
    respuesta: number,
    tiempoResolucion: number
  ): Promise<SubmitProblemResponse> {
    try {
      const response = await apiClient.post<SubmitProblemResponse>(
        `/practices/${sesionId}/submit-problem`,
        {
          problema_id: problemaId,
          respuesta,
          tiempo_resolucion: tiempoResolucion,
        }
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Completar sesión de práctica (sólo si el backend no lo hizo automáticamente).
   * Ruta: POST /adaptive/practice/complete
   */
  async finalizarPractica(sesionId: number): Promise<void> {
    try {
      await apiClient.post('/adaptive/practice/complete', { sesion_id: sesionId });
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Verifica si el estudiante tiene problemas disponibles para redención.
   * Ruta: GET /adaptive/redencion/disponible
   */
  async getRedenciónDisponible(): Promise<{ disponible: boolean; total_problemas_fallados: number }> {
    try {
      const response = await apiClient.get<{ disponible: boolean; total_problemas_fallados: number }>(
        '/adaptive/redencion/disponible'
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Inicia una sesión de redención con los 5 problemas fallados.
   * Ruta: POST /adaptive/redencion/iniciar
   */
  async iniciarRedencion(): Promise<SesionStartResponse> {
    try {
      const response = await apiClient.post<SesionStartResponse>('/adaptive/redencion/iniciar');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Devuelve la sesión EN_PROGRESO activa del estudiante (<90 min) o null.
   * Ruta: GET /adaptive/practice/sesion-activa
   */
  async getSesionActiva(): Promise<SesionActivaResponse | null> {
    try {
      const response = await apiClient.get<SesionActivaResponse | null>(
        '/adaptive/practice/sesion-activa'
      );
      return response.data;
    } catch {
      return null; // Silencioso — no bloquea la UI
    }
  },

  /**
   * Retoma una sesión EN_PROGRESO devolviendo los problemas restantes.
   * Ruta: POST /adaptive/practice/retomar/{sesion_id}
   */
  async retomarPractica(sesionId: number): Promise<SesionStartResponse> {
    try {
      const response = await apiClient.post<SesionStartResponse>(
        `/adaptive/practice/retomar/${sesionId}`
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Descarta (abandona) una sesión EN_PROGRESO para poder iniciar una nueva.
   * Ruta: POST /adaptive/practice/descartar/{sesion_id}
   */
  async descartarSesion(sesionId: number): Promise<void> {
    try {
      await apiClient.post(`/adaptive/practice/descartar/${sesionId}`);
    } catch {
      // Silencioso — si falla, la sesión la cierra el scheduler
    }
  },

  // ── Gamificación ───────────────────────────────────────────────────────────

  async getSaldo(): Promise<SaldoPuntosResponse> {
    try {
      const response = await apiClient.get<SaldoPuntosResponse>('/gamification/balance');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Catálogo completo (BD) con IDs numéricos y flag poseido.
   * Se usa para mapear el archivo_referencia → id de BD al comprar.
   */
  async getCatalogo(): Promise<{
    temas: ItemPoseido[];
    fondos: ItemPoseido[];
    colores: ItemPoseido[];
    musicas: ItemPoseido[];
    efectos: ItemPoseido[];
    total_items: number;
  }> {
    try {
      const response = await apiClient.get('/gamification/store');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getItemsPoseidos(): Promise<ItemPoseido[]> {
    try {
      const response = await apiClient.get<ItemPoseido[]>('/gamification/store/owned');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async comprarItem(desbloqueableId: number): Promise<ComprarItemResponse> {
    try {
      const response = await apiClient.post<ComprarItemResponse>(
        `/gamification/store/buy/${desbloqueableId}`
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getPersonalizacion(): Promise<PersonalizacionResponse> {
    try {
      const response = await apiClient.get<PersonalizacionResponse>('/gamification/customization');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtiene enunciados narrativos temáticos para múltiples problemas (batch).
   * Ruta: POST /enunciados/lote
   * Llamar al inicio de la sesión con todos los problema_ids y el tema activo.
   * Retorna {} si el tema es vacío o no hay problema_ids.
   */
  async obtenerEnunciadosLote(
    problema_ids: number[],
    tema: string
  ): Promise<Record<number, string>> {
    try {
      const response = await apiClient.post<{ enunciados: Record<string, string> }>(
        '/enunciados/lote',
        { problema_ids, tema }
      );
      // Convertir claves string → number
      const result: Record<number, string> = {};
      for (const [k, v] of Object.entries(response.data.enunciados)) {
        result[parseInt(k, 10)] = v;
      }
      return result;
    } catch {
      return {};  // Silencioso — fallback a preguntas genéricas
    }
  },

  /**
   * Obtiene mensaje motivacional personalizado (LLM con caché diaria).
   * tipo: "dashboard" | "progreso"
   * UX: llamar en background; mostrar placeholder genérico mientras llega.
   */
  /**
   * Obtiene el análisis pedagógico post-práctica generado con R1.
   * Retorna string vacío si falla (el componente usa fallback genérico).
   */
  async getAnalisisSesion(sesionId: number): Promise<string> {
    try {
      const response = await apiClient.get<{ sesion_id: number; texto: string; generada_llm: boolean }>(
        `/analisis/${sesionId}`
      );
      return response.data.texto;
    } catch {
      return '';
    }
  },

  async getMensajeMotivacional(tipo: 'dashboard' | 'progreso'): Promise<string> {
    try {
      const response = await apiClient.get<{ tipo: string; texto: string; generada_llm: boolean }>(
        `/mensajes/${tipo}`
      );
      return response.data.texto;
    } catch {
      return '';  // Silencioso — el componente mantiene el texto genérico
    }
  },

  /**
   * Obtiene el enunciado narrativo de UN solo problema.
   * Wrapper sobre obtenerEnunciadosLote con un único ID.
   * Retorna null si el LLM no generó texto o si la llamada falla.
   */
  async obtenerEnunciado(
    problema_id: number,
    tema: string
  ): Promise<string | null> {
    const result = await this.obtenerEnunciadosLote([problema_id], tema);
    return result[problema_id] ?? null;
  },

  async savePersonalizacion(data: PersonalizacionRequest): Promise<PersonalizacionResponse> {
    try {
      const response = await apiClient.put<PersonalizacionResponse>(
        '/gamification/customization',
        data
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getMedallas(): Promise<MedallasResponse> {
    try {
      const response = await apiClient.get<MedallasResponse>('/gamification/medals');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async setMedallaDestacada(medalId: number): Promise<void> {
    try {
      await apiClient.put(`/gamification/medals/highlight/${medalId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async quitarMedallaDestacada(): Promise<void> {
    try {
      await apiClient.delete('/gamification/medals/highlight');
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getRecompensasSesion(sesionId: number): Promise<RecompensasSesionResponse> {
    try {
      const response = await apiClient.get<RecompensasSesionResponse>(
        `/gamification/session/${sesionId}/rewards`
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Pistas ─────────────────────────────────────────────────────────────────

  async solicitarPista(
    sesionId: number,
    problemaId: number,
    nivel: number
  ): Promise<{ contenido: string; puntos_gastados: number; saldo_nuevo: number; generada_llm: boolean }> {
    try {
      const response = await apiClient.post('/hints/request', {
        sesion_id: sesionId,
        problema_id: problemaId,
        nivel_pista: nivel,
      });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Animaciones guardadas ──────────────────────────────────────────────────

  async guardarAnimacion(
    problemaId: number,
    operacion: string,
    numero1: string,
    numero2: string,
    nivelDificultad: number,
  ): Promise<GuardarAnimacionResponse> {
    try {
      const response = await apiClient.post<GuardarAnimacionResponse>('/animaciones/guardar', {
        problema_id: problemaId,
        operacion,
        numero1,
        numero2,
        nivel_dificultad: nivelDificultad,
      });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getColeccionAnimaciones(): Promise<ColeccionAnimacionesResponse> {
    try {
      const response = await apiClient.get<ColeccionAnimacionesResponse>('/animaciones/coleccion');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async eliminarAnimacion(id: number): Promise<void> {
    try {
      await apiClient.delete(`/animaciones/${id}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Videos educativos ───────────────────────────────────────────────────────

  async getGaleriaVideos(): Promise<GaleriaVideosResponse> {
    try {
      const response = await apiClient.get<GaleriaVideosResponse>('/videos/gallery');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async guardarVideo(videoId: number): Promise<GuardarVideoResponse> {
    try {
      const response = await apiClient.post<GuardarVideoResponse>(`/videos/${videoId}/save`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async actualizarProgresoVideo(
    videoId: number,
    progresoSegundos: number,
    completo: boolean = false
  ): Promise<void> {
    try {
      await apiClient.put(`/videos/${videoId}/progress`, {
        video_id: videoId,
        progreso_segundos: progresoSegundos,
        completo,
      });
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Desafíos grupales ──────────────────────────────────────────────────────

  /**
   * Obtiene los desafíos grupales asignados al grupo del estudiante.
   * Ruta: GET /challenges/mis-desafios
   * El progreso se calcula en tiempo real en el servidor.
   */
  async getDesafios(): Promise<DesafioEstudiante[]> {
    try {
      const response = await apiClient.get<DesafioEstudiante[]>('/challenges/mis-desafios');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ── Post-Test Final ────────────────────────────────────────────────────────

  /** Verifica si el post-test está activo para la org del estudiante y si ya lo completó. */
  async getPostTestEstado(): Promise<{ activo: boolean; completado: boolean; org_id: number | null }> {
    try {
      const response = await apiClient.get('/adaptive/post-test/estado');
      return response.data;
    } catch {
      return { activo: false, completado: false, org_id: null };
    }
  },

  /** Genera los 8 problemas del post-test. */
  async iniciarPostTest(): Promise<{ post_test_id: number; problemas: ProblemaBE[]; mensaje: string }> {
    try {
      const response = await apiClient.post('/adaptive/post-test/start');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /** Envía las respuestas del post-test. Acepta tiempos opcionales por problema. */
  async enviarPostTest(
    postTestId: number,
    respuestas: Record<number, number>,
    tiemposPorProblema?: Record<number, number>,
  ): Promise<{
    estudiante_id: number;
    perfecto: boolean;
    total_correctos: number;
    correctos_por_operacion: Record<string, number>;
    tiempos_por_operacion: Record<string, number>;
    pre_correctos_por_operacion: Record<string, number> | null;
    pre_nivel_actual: number | null;
    mensaje: string;
  }> {
    try {
      const response = await apiClient.post('/adaptive/post-test/submit', {
        post_test_id: postTestId,
        respuestas,
        tiempos_por_problema: tiemposPorProblema,
      });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },
};
