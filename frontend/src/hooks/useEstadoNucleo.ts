/**
 * Estado del núcleo para el estudiante: si practica en el núcleo ("Practicar" lleva a
 * /student/nucleo) y su sesión a medias. Se invalida al empezar, descartar o terminar.
 */

import { useQuery } from '@tanstack/react-query';
import { CLAVE_ESTADO_NUCLEO, nucleoService } from '@/services/nucleoService';

export const RUTA_PRACTICA_NUCLEO = '/student/nucleo';

export function useEstadoNucleo(habilitado: boolean = true) {
  return useQuery({
    queryKey: CLAVE_ESTADO_NUCLEO,
    queryFn: () => nucleoService.estado(),
    enabled: habilitado,
    staleTime: 0,
    refetchOnMount: 'always',
    retry: false,
  });
}
