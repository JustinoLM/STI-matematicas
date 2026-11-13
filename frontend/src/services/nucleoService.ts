/**
 * Servicio del núcleo de práctica (/api/nucleo). Va en paralelo a la práctica de decimales.
 */

import apiClient from './api';
import type {
  EnvioRespuesta,
  EstadoNucleo,
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
