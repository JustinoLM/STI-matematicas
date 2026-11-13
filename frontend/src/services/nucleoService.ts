/**
 * Servicio del núcleo de práctica (/api/nucleo). Va en paralelo a la práctica de decimales.
 */

import axios from 'axios';
import apiClient, { getErrorMessage } from './api';
import type {
  AjusteEstudiante,
  AsignacionNucleo,
  ConfigLeccion,
  EnvioRespuesta,
  EstadoNucleo,
  LeccionSalon,
  ProblemaTurno,
  ResultadoRespuesta,
  SesionNucleo,
} from '@/types/nucleo';

export const CLAVE_ESTADO_NUCLEO = ['nucleo-estado'] as const;

export const nucleoService = {
  /** ¿El estudiante practica en el núcleo? y su sesión a medias, si la tiene */
  async estado(): Promise<EstadoNucleo> {
    return (await apiClient.get<EstadoNucleo>('/nucleo/estado')).data;
  },

  /** Inicia una sesión nueva, o devuelve la activa si ya hay una */
  async iniciar(): Promise<SesionNucleo> {
    return (await apiClient.post<SesionNucleo>('/nucleo/sesiones')).data;
  },

  async siguiente(sesionId: number): Promise<ProblemaTurno> {
    return (await apiClient.get<ProblemaTurno>(`/nucleo/sesiones/${sesionId}/siguiente`)).data;
  },

  async responder(sesionId: number, problemaSesionId: number, envio: EnvioRespuesta): Promise<ResultadoRespuesta> {
    return (await apiClient.post<ResultadoRespuesta>(
      `/nucleo/sesiones/${sesionId}/problemas/${problemaSesionId}/respuesta`,
      envio,
    )).data;
  },

  /** Abandona la sesión activa: lo que quedó pendiente no cuenta */
  async descartar(sesionId: number): Promise<SesionNucleo> {
    return (await apiClient.post<SesionNucleo>(`/nucleo/sesiones/${sesionId}/descartar`)).data;
  },
};

// ─── Profesor: lecciones del salón (fase 6a) ─────────────────────────────────

/** Error de la API con el código de la regla (MAX_PRIORITARIAS, PRERREQUISITO_CICLO, ANIO_CERRADO…) */
export class ErrorNucleo extends Error {
  constructor(mensaje: string, public codigo?: string) {
    super(mensaje);
    this.name = 'ErrorNucleo';
  }
}

async function llamar<T>(peticion: () => Promise<{ data: T }>): Promise<T> {
  try {
    return (await peticion()).data;
  } catch (error) {
    const codigo = axios.isAxiosError(error) ? error.response?.data?.codigo : undefined;
    throw new ErrorNucleo(getErrorMessage(error), codigo);
  }
}

export const clavesProfesor = {
  catalogo: (anioId: number) => ['teacher', 'nucleo', anioId, 'catalogo'] as const,
  asignaciones: (anioId: number) => ['teacher', 'nucleo', anioId, 'asignaciones'] as const,
  ajustes: (anioId: number) => ['teacher', 'nucleo', anioId, 'ajustes'] as const,
};

export const nucleoProfesorService = {
  catalogo(anioId: number): Promise<LeccionSalon[]> {
    return llamar(() => apiClient.get<LeccionSalon[]>(`/nucleo/anios/${anioId}/catalogo`));
  },

  /** Habilita la lección o guarda su configuración */
  configurar(anioId: number, leccionId: string, config: ConfigLeccion): Promise<unknown> {
    return llamar(() => apiClient.put(`/nucleo/anios/${anioId}/lecciones/${leccionId}`, config));
  },

  deshabilitar(anioId: number, leccionId: string): Promise<unknown> {
    return llamar(() => apiClient.delete(`/nucleo/anios/${anioId}/lecciones/${leccionId}`));
  },

  editarPrerrequisitos(anioId: number, leccionId: string, prerrequisitos: string[]): Promise<unknown> {
    return llamar(() => apiClient.put(`/nucleo/anios/${anioId}/lecciones/${leccionId}/prerrequisitos`, { prerrequisitos }));
  },

  restaurarPrerrequisitos(anioId: number, leccionId: string): Promise<unknown> {
    return llamar(() => apiClient.delete(`/nucleo/anios/${anioId}/lecciones/${leccionId}/prerrequisitos`));
  },

  asignaciones(anioId: number): Promise<AsignacionNucleo[]> {
    return llamar(() => apiClient.get<AsignacionNucleo[]>(`/nucleo/anios/${anioId}/asignaciones`));
  },

  asignar(anioId: number, estudianteId: number, leccionId: string): Promise<AsignacionNucleo> {
    return llamar(() => apiClient.post<AsignacionNucleo>(`/nucleo/anios/${anioId}/asignaciones`,
      { estudiante_id: estudianteId, leccion_id: leccionId }));
  },

  cerrarAsignacion(asignacionId: number): Promise<AsignacionNucleo> {
    return llamar(() => apiClient.delete<AsignacionNucleo>(`/nucleo/asignaciones/${asignacionId}`));
  },

  ajustes(anioId: number): Promise<AjusteEstudiante[]> {
    return llamar(() => apiClient.get<AjusteEstudiante[]>(`/nucleo/anios/${anioId}/ajustes`));
  },

  forzarBanco(anioId: number, estudianteId: number, bancoForzado: boolean): Promise<AjusteEstudiante> {
    return llamar(() => apiClient.put<AjusteEstudiante>(`/nucleo/anios/${anioId}/estudiantes/${estudianteId}/ajustes`,
      { banco_forzado: bancoForzado }));
  },
};
