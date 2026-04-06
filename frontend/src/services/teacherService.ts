/**
 * Servicio de profesor (grupos, desafíos, alertas, configuración).
 */

import apiClient, { getErrorMessage } from './api';
import {
  Grupo,
  AlertaEstudianteDetalle,
  DesafioGrupal,
  EstadisticasGrupo,
  ConfiguracionPractica,
  ProgresoEstudiante,
} from '@/types';

export interface BulkAddError {
  fila: number;
  codigo: string;
  mensaje: string;
}

export interface BulkAddResult {
  total: number;
  agregados: number;
  errores: BulkAddError[];
}

/** Estudiante de la organización del profesor (endpoint GET /teachers/students). */
export interface EstudianteOrg {
  id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  grado_academico: string | null;
  activo: boolean;
  nivel_actual: number;
  precision_ultimos_15: number;
}

export interface PerfilProfesor {
  id: number;
  codigo_profesor: string;
  nombre_completo: string;
  institucion: string | null;
  grado_academico: string | null;
  organizacion_nombre: string | null;
}

export const teacherService = {
  // ==================== PERFIL ====================

  async getPerfilProfesor(): Promise<PerfilProfesor> {
    try {
      const response = await apiClient.get<PerfilProfesor>('/teachers/me');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== GRUPOS ====================

  /**
   * Obtener todos los grupos del profesor.
   */
  async getGrupos(): Promise<Grupo[]> {
    try {
      const response = await apiClient.get<Grupo[]>('/teachers/groups');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtener detalle de un grupo específico.
   */
  async getGrupoDetalle(grupoId: number): Promise<Grupo> {
    try {
      const response = await apiClient.get<Grupo>(`/teachers/groups/${grupoId}`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Crear nuevo grupo.
   */
  async crearGrupo(nombre: string, codigoGrupo: string): Promise<Grupo> {
    try {
      const response = await apiClient.post<Grupo>('/teachers/groups', {
        nombre,
        codigo_grupo: codigoGrupo,
      });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async eliminarGrupo(grupoId: number): Promise<void> {
    try {
      await apiClient.delete(`/teachers/groups/${grupoId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Agregar estudiante a un grupo.
   */
  async agregarEstudiante(grupoId: number, estudianteId: number): Promise<void> {
    try {
      await apiClient.post(`/teachers/groups/${grupoId}/students/${estudianteId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Remover estudiante de un grupo.
   */
  async removerEstudiante(grupoId: number, estudianteId: number): Promise<void> {
    try {
      await apiClient.delete(`/teachers/groups/${grupoId}/students/${estudianteId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== ESTADÍSTICAS ====================

  /**
   * Obtener estadísticas detalladas de un grupo.
   */
  async getEstadisticasGrupo(grupoId: number): Promise<EstadisticasGrupo> {
    try {
      const response = await apiClient.get<EstadisticasGrupo>(`/teachers/groups/${grupoId}/statistics`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== ALERTAS ====================

  /**
   * Obtener alertas activas de todos los grupos.
   */
  async getAlertas(): Promise<AlertaEstudianteDetalle[]> {
    try {
      const response = await apiClient.get<AlertaEstudianteDetalle[]>('/teachers/alerts');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== DESAFÍOS ====================

  /**
   * Obtener todos los desafíos del profesor.
   */
  async getDesafios(): Promise<DesafioGrupal[]> {
    try {
      const response = await apiClient.get<DesafioGrupal[]>('/teachers/challenges');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Crear desafío grupal.
   */
  async crearDesafio(data: {
    nombre: string;
    descripcion?: string;
    tipo: string;
    objetivo_cantidad: number;
    parametro_adicional?: number;
    recompensa_texto?: string;
    recompensa_puntos?: number;
    grupos_ids: number[];
    fecha_limite?: string;
  }): Promise<DesafioGrupal> {
    try {
      const response = await apiClient.post<DesafioGrupal>('/teachers/challenges', data);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Eliminar desafío (soft delete).
   */
  async eliminarDesafio(desafioId: number): Promise<void> {
    try {
      await apiClient.delete(`/teachers/challenges/${desafioId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== CONFIGURACIÓN ====================

  /**
   * Crear configuración de práctica para un grupo.
   */
  async crearConfiguracion(data: {
    grupo_id: number;
    operaciones_permitidas: string[];
    niveles_permitidos: number[];
    rango_min: number;
    rango_max: number;
    decimales_maximos: number;
    pistas_habilitadas: Record<string, boolean>;
  }): Promise<ConfiguracionPractica> {
    try {
      const response = await apiClient.post<ConfiguracionPractica>('/teachers/configuration', data);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtener configuración activa de un grupo.
   */
  async getConfiguracionGrupo(grupoId: number): Promise<ConfiguracionPractica> {
    try {
      const response = await apiClient.get<ConfiguracionPractica>(`/teachers/groups/${grupoId}/configuration`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== ESTUDIANTES ====================

  /**
   * Obtener todos los estudiantes de la organización del profesor.
   * Opcionalmente filtra por nombre o código con ?q=...
   */
  async getEstudiantesOrg(q?: string): Promise<EstudianteOrg[]> {
    try {
      const params = q ? { q } : {};
      const response = await apiClient.get<EstudianteOrg[]>('/teachers/students', { params });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Añadir estudiantes a un grupo en bulk, dado una lista de códigos.
   */
  async bulkAddToGroup(grupoId: number, codigos: string[]): Promise<BulkAddResult> {
    try {
      const response = await apiClient.post<BulkAddResult>(`/teachers/groups/${grupoId}/students/bulk`, { codigos });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Buscar estudiantes por nombre o código.
   */
  async buscarEstudiantes(query: string): Promise<any[]> {
    try {
      const response = await apiClient.post('/teachers/students/search', { query });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtener progreso detallado de un estudiante (legacy).
   */
  async getProgresoEstudiante(estudianteId: number): Promise<ProgresoEstudiante> {
    try {
      const response = await apiClient.get<ProgresoEstudiante>(`/students/${estudianteId}/progress`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtener perfil adaptativo de un estudiante (mismo formato que GET /adaptive/profile).
   */
  async getPerfilEstudiante(estudianteId: number): Promise<any> {
    try {
      const response = await apiClient.get(`/teachers/students/${estudianteId}/profile`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /**
   * Obtener estadísticas de práctica de un estudiante (mismo formato que GET /practices/stats).
   */
  async getStatsEstudiante(estudianteId: number): Promise<any> {
    try {
      const response = await apiClient.get(`/teachers/students/${estudianteId}/stats`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },
};
