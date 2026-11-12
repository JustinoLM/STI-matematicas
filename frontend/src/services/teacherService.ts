/**
 * Servicio de profesor (salones, grupos, desafíos, alertas, configuración).
 */

import axios from 'axios';
import apiClient, { getErrorMessage } from './api';
import {
  Grupo,
  CandidatoSalon,
  SalonDetalle,
  SalonResumen,
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

/** Estudiante de los salones activos del profesor (endpoint GET /teachers/students). */
export interface EstudianteOrg {
  id: number;
  codigo_estudiante: string;
  nombre_completo: string;
  salon_nombre: string | null;
  grado: number | null;
  anio_lectivo_id: number | null;
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

  // ==================== SALONES ====================

  /** Salones del profesor: los del año en curso primero y luego el historial. */
  async getSalones(): Promise<SalonResumen[]> {
    try {
      const response = await apiClient.get<SalonResumen[]>('/teachers/salones');
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /** Crea el salón (o abre el existente con ese nombre) para el año actual. */
  async crearSalon(nombre: string, grado: number): Promise<SalonDetalle> {
    try {
      const response = await apiClient.post<SalonDetalle>('/teachers/salones', { nombre, grado });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async getSalonDetalle(anioLectivoId: number): Promise<SalonDetalle> {
    try {
      const response = await apiClient.get<SalonDetalle>(`/teachers/salones/${anioLectivoId}`);
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /** Estudiantes de la organización, indicando si ya están en algún salón. */
  async getCandidatosSalon(anioLectivoId: number, q?: string): Promise<CandidatoSalon[]> {
    try {
      const params = q ? { q } : {};
      const response = await apiClient.get<CandidatoSalon[]>(`/teachers/salones/${anioLectivoId}/candidatos`, { params });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async asignarAlSalon(anioLectivoId: number, estudianteId: number): Promise<void> {
    try {
      await apiClient.post(`/teachers/salones/${anioLectivoId}/estudiantes/${estudianteId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  async quitarDelSalon(anioLectivoId: number, estudianteId: number): Promise<void> {
    try {
      await apiClient.delete(`/teachers/salones/${anioLectivoId}/estudiantes/${estudianteId}`);
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  /** Asigna varios estudiantes al salón por código. */
  async asignarAlSalonPorCodigos(anioLectivoId: number, codigos: string[]): Promise<BulkAddResult> {
    try {
      const response = await apiClient.post<BulkAddResult>(`/teachers/salones/${anioLectivoId}/estudiantes/bulk`, { codigos });
      return response.data;
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== GRUPOS (dentro de un salón) ====================

  /** Grupos de los salones del profesor (opcionalmente de un solo salón). */
  async getGrupos(anioLectivoId?: number): Promise<Grupo[]> {
    try {
      const params = anioLectivoId ? { anio_lectivo_id: anioLectivoId } : {};
      const response = await apiClient.get<Grupo[]>('/teachers/groups', { params });
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

  /** Crea un grupo dentro del salón. */
  async crearGrupo(anioLectivoId: number, nombre: string): Promise<Grupo> {
    try {
      const response = await apiClient.post<Grupo>(`/teachers/salones/${anioLectivoId}/grupos`, { nombre });
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
    anio_lectivo_id: number;
    grupos_ids: number[];  // vacío = todo el salón es un equipo
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
   * Aplicar configuración de práctica (decimales) a un salón.
   */
  async crearConfiguracion(data: {
    anio_lectivo_id: number;
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
   * Obtener configuración activa de un salón.
   */
  async getConfiguracionSalon(anioLectivoId: number): Promise<ConfiguracionPractica | null> {
    try {
      const response = await apiClient.get<ConfiguracionPractica>(`/teachers/salones/${anioLectivoId}/configuration`);
      return response.data;
    } catch (error) {
      // 404 = el salón aún no tiene configuración — es esperado, no es un error
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      throw new Error(getErrorMessage(error));
    }
  },

  // ==================== ESTUDIANTES ====================

  /**
   * Estudiantes de los salones activos del profesor, con su salón y grado.
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
   * Buscar estudiantes por nombre o código.
   */
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
