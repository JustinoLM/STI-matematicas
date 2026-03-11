/**
 * Servicio de estadísticas de grupo para el panel analítico del profesor.
 */

import apiClient, { getErrorMessage } from './api';
import type { GrupoStatsResponse, AnalisisIAResponse } from '@/types';

export const statsService = {
  /**
   * Obtiene estadísticas completas de un grupo (perfiles ML, alertas, niveles, actividad).
   */
  async getGrupoStats(grupoId: number): Promise<GrupoStatsResponse> {
    try {
      const response = await apiClient.get<GrupoStatsResponse>(
        `/stats/groups/${grupoId}`
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Genera análisis pedagógico del grupo bajo demanda con DeepSeek.
   * Sin caché — cada llamada genera un análisis fresco.
   */
  async analizarConIA(grupoId: number): Promise<AnalisisIAResponse> {
    try {
      const response = await apiClient.post<AnalisisIAResponse>(
        `/stats/groups/${grupoId}/ai-analysis`
      );
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },
};
