/**
 * Motivación del núcleo (fase 7b): nivel de jugador, caminos y mapa; y las medallas del núcleo.
 * Solo se piden si el estudiante practica en el núcleo. Se invalidan al terminar una sesión.
 */

import { useQuery } from '@tanstack/react-query';
import { CLAVE_MEDALLAS_NUCLEO, CLAVE_PROGRESO_NUCLEO, nucleoService } from '@/services/nucleoService';
import { useEstadoNucleo } from './useEstadoNucleo';

export function useProgresoNucleo() {
  const { data: estado } = useEstadoNucleo();
  const enNucleo = estado?.disponible ?? false;
  const consulta = useQuery({
    queryKey: CLAVE_PROGRESO_NUCLEO,
    queryFn: () => nucleoService.progreso(),
    enabled: enNucleo,
    staleTime: 30_000,
  });
  return { enNucleo, ...consulta };
}

export function useMedallasNucleo(habilitado: boolean) {
  return useQuery({
    queryKey: CLAVE_MEDALLAS_NUCLEO,
    queryFn: () => nucleoService.medallas(),
    enabled: habilitado,
    staleTime: 30_000,
  });
}
