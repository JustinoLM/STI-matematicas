/**
 * Servicio del módulo de Regla de Tres — práctica adaptativa independiente.
 */

import apiClient, { getErrorMessage } from './api';

// ─── Tipos ──────────────────────────────────────────────────────────────────

export interface ProblemaReglaTres {
  id: number;
  tipo: 'directa' | 'inversa';
  numero1: string | number;
  numero2: string | number;
  numero3: string | number;
  nivel_dificultad: number;
}

export interface SesionReglaTresStart {
  sesion_id: number;
  nivel_al_iniciar: number;
  cantidad_problemas: number;
  progreso_actual: number;
  problema_actual: ProblemaReglaTres;
}

export interface ResumenSesionR3 {
  correctos: number;
  total: number;
  nota_pct: number;
  nivel_actual: number;
  puntos_ganados: number;
}

export interface SubmitRespuestaR3Response {
  es_correcto: boolean;
  resultado_correcto: string | number;
  sesion_completada: boolean;
  progreso_actual: number;
  cantidad_problemas: number;
  siguiente_problema: ProblemaReglaTres | null;
  resumen: ResumenSesionR3 | null;
}

export interface EstudianteNotaR3 {
  estudiante_id: number;
  codigo: string;
  nombre_completo: string;
  tiene_practica: boolean;
  ultima_fecha: string | null;
  correctos: number | null;
  total: number | null;
  nota_pct: number | null;
  nivel_actual: number | null;
}

export interface NotasReglaTresResponse {
  estudiantes: EstudianteNotaR3[];
}

// ─── Servicio ───────────────────────────────────────────────────────────────

export const reglaDeTresService = {
  async iniciarPractica(): Promise<SesionReglaTresStart> {
    try {
      const response = await apiClient.post<SesionReglaTresStart>('/regla-de-tres/practice/start');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async enviarRespuesta(
    sesionId: number,
    problemaId: number,
    respuesta: string | number,
  ): Promise<SubmitRespuestaR3Response> {
    try {
      const response = await apiClient.post<SubmitRespuestaR3Response>(
        `/regla-de-tres/practice/${sesionId}/submit`,
        { problema_id: problemaId, respuesta },
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async obtenerNotasProfesor(): Promise<NotasReglaTresResponse> {
    try {
      const response = await apiClient.get<NotasReglaTresResponse>('/regla-de-tres/teacher/notas');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async obtenerNotasAdmin(): Promise<NotasReglaTresResponse> {
    try {
      const response = await apiClient.get<NotasReglaTresResponse>('/regla-de-tres/admin/notas');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },
};
