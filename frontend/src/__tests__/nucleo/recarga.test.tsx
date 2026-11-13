/**
 * Recargar la página en plena práctica retoma la sesión sin preguntar (fase 5b). El aviso de
 * práctica a medias queda para cuando se entra con una sesión abierta (por ejemplo desde el menú).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { NucleoPracticePage } from '@/pages/student/NucleoPracticePage';
import { nucleoService } from '@/services/nucleoService';
import type { SesionActivaNucleo } from '@/types/nucleo';
import { sumaBanco } from './fixtures';

const RUTA = '/student/nucleo';
const activa: SesionActivaNucleo = {
  sesion_id: 7, estado: 'en_progreso', cantidad_problemas: 10, progreso: 3, minutos_transcurridos: 2,
};

let estadoHistorial: unknown = null;
function Sonda() {
  estadoHistorial = useLocation().state;
  return null;
}

function montar(entrada: { pathname: string; state?: unknown }) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[entrada]}>
        <Routes>
          <Route path={RUTA} element={<><NucleoPracticePage /><Sonda /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  estadoHistorial = null;
  vi.spyOn(nucleoService, 'iniciar').mockResolvedValue({ ...activa });
  vi.spyOn(nucleoService, 'siguiente').mockResolvedValue({
    sesion_completada: false, problema_sesion_id: 31, orden: 3, problema: sumaBanco, intentos_restantes: 3,
  });
});

afterEach(() => { vi.restoreAllMocks(); });

describe('sesión a medias y recarga', () => {
  it('al entrar con una sesión abierta (sin venir de "Continuar") pregunta', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: activa });
    montar({ pathname: RUTA });
    expect(await screen.findByTestId('aviso-sesion')).toBeInTheDocument();
    expect(nucleoService.iniciar).not.toHaveBeenCalled();
  });

  it('al empezar, marca el historial; al recargar, retoma sin preguntar', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: null });
    const { unmount } = montar({ pathname: RUTA });
    expect(await screen.findByTestId('problema')).toBeInTheDocument();
    expect(estadoHistorial).toEqual({ retomar: true });
    unmount();

    // Recarga: el navegador conserva el estado de la entrada del historial
    vi.mocked(nucleoService.estado).mockResolvedValue({ disponible: true, sesion_activa: activa });
    vi.mocked(nucleoService.iniciar).mockClear();
    montar({ pathname: RUTA, state: estadoHistorial });
    expect(await screen.findByTestId('problema')).toBeInTheDocument();
    expect(screen.queryByTestId('aviso-sesion')).toBeNull();
    await waitFor(() => expect(nucleoService.iniciar).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId('contador')).toHaveTextContent('4 de 10');
  });

  it('"Continuar" en el aviso también marca el historial', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: activa });
    montar({ pathname: RUTA });
    (await screen.findByTestId('continuar')).click();
    expect(await screen.findByTestId('problema')).toBeInTheDocument();
    expect(estadoHistorial).toEqual({ retomar: true });
  });
});
