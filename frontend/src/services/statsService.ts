/**
 * Servicio de estadísticas para el panel analítico del profesor: de un salón completo
 * (año lectivo) o de un grupo dentro del salón.
 */

import apiClient, { getErrorMessage, TIMEOUT_LLM_R1_MS } from './api';
import type { GrupoStatsResponse, AnalisisIAResponse } from '@/types';

export type AmbitoStats = 'salon' | 'grupo';

const ruta = (ambito: AmbitoStats, id: number) =>
  ambito === 'salon' ? `/stats/salones/${id}` : `/stats/groups/${id}`;

export const statsService = {
  /**
   * Obtiene estadísticas completas (perfiles ML, alertas, niveles, actividad).
   */
  async getStats(ambito: AmbitoStats, id: number): Promise<GrupoStatsResponse> {
    try {
      const response = await apiClient.get<GrupoStatsResponse>(ruta(ambito, id));
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Genera análisis pedagógico bajo demanda con DeepSeek.
   * Sin caché — cada llamada genera un análisis fresco.
   */
  async analizarConIA(ambito: AmbitoStats, id: number): Promise<AnalisisIAResponse> {
    try {
      const response = await apiClient.post<AnalisisIAResponse>(
        `${ruta(ambito, id)}/ai-analysis`,
        undefined,
        { timeout: TIMEOUT_LLM_R1_MS }
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },
};
