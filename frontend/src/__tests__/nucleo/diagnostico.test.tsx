/**
 * Diagnóstico inicial en la pantalla del núcleo (fase 7a): mensaje amable antes de empezar, misma
 * pantalla de problema sin conteo ni corrección, entre problemas solo "¡Gracias!", barra de avance
 * sin conteos, final "Ya sé por dónde empezar" y retomar a mitad sin poder descartar.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { NucleoPracticePage } from '@/pages/student/NucleoPracticePage';
import { AvisoSesionAMedias } from '@/components/nucleo/AvisoSesionAMedias';
import { TEXTO_INTRO } from '@/components/nucleo/Diagnostico';
import { nucleoService } from '@/services/nucleoService';
import type { ResultadoRespuesta, SesionActivaNucleo } from '@/types/nucleo';
import { sumaTeclado } from './fixtures';

const RUTA = '/student/nucleo';
const diag: SesionActivaNucleo = {
  sesion_id: 5, estado: 'activa', tipo: 'diagnostico', cantidad_problemas: 16, progreso: 2, minutos_transcurridos: 3,
};
const neutra = (extra: Partial<ResultadoRespuesta> = {}): ResultadoRespuesta => ({
  correcto: null, huecos: {}, intentos_restantes: 0, problema_terminado: true, solucion: null,
  experiencia_ganada: 0, evento_dominio: null, sesion_completada: false,
  diagnostico: { terminado: false, avance: 0.5 }, ...extra,
});

function montar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[RUTA]}>
        <Routes><Route path={RUTA} element={<NucleoPracticePage />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function responder() {
  fireEvent.click(screen.getByRole('button', { name: '3' }));
  await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
}

beforeEach(() => {
  vi.spyOn(nucleoService, 'iniciar').mockResolvedValue({ ...diag, progreso: 0 });
  vi.spyOn(nucleoService, 'siguiente').mockResolvedValue({
    sesion_completada: false, problema_sesion_id: 41, orden: 0, problema: sumaTeclado, intentos_restantes: 1,
    pistas_habilitadas: { 1: false, 2: false, 3: false }, diagnostico: true, avance: 0.25,
  });
});

afterEach(() => { vi.restoreAllMocks(); });

describe('diagnóstico inicial del estudiante', () => {
  it('empieza con un mensaje amable y no arranca hasta que el niño toca "Empezar"', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: null, diagnostico_pendiente: true });
    montar();
    expect(await screen.findByTestId('intro-diagnostico')).toHaveTextContent(TEXTO_INTRO);
    expect(nucleoService.iniciar).not.toHaveBeenCalled();
    await act(async () => { fireEvent.click(screen.getByTestId('empezar-diagnostico')); });
    expect(await screen.findByTestId('problema')).toBeInTheDocument();
    // Sin conteo "x de N": una barra de avance
    expect(screen.queryByTestId('contador')).toBeNull();
    expect(screen.getByTestId('avance-diagnostico')).toHaveAttribute('aria-valuenow', '25');
  });

  it('entre problemas no celebra ni corrige, y al final dice que ya sabe por dónde empezar', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: null, diagnostico_pendiente: true });
    const enviar = vi.spyOn(nucleoService, 'responder')
      .mockResolvedValueOnce(neutra())
      .mockResolvedValueOnce(neutra({ sesion_completada: true, diagnostico: { terminado: true, avance: 1 } }));
    montar();
    const empezar = await screen.findByTestId('empezar-diagnostico');
    await act(async () => { fireEvent.click(empezar); });
    await screen.findByTestId('problema');
    await responder();
    const entre = await screen.findByTestId('entre-diagnostico');
    expect(entre).toHaveTextContent('¡Gracias! Vamos con otro.');
    expect(screen.queryByText('¡Muy bien!')).toBeNull();
    expect(screen.queryByText('Así se resuelve:')).toBeNull();
    expect(screen.queryByTestId('mensaje')).toBeNull();
    expect(screen.getByTestId('avance-diagnostico')).toHaveAttribute('aria-valuenow', '50');

    await act(async () => { fireEvent.click(screen.getByTestId('siguiente')); });
    await screen.findByTestId('problema');
    await responder();
    expect(await screen.findByTestId('fin-diagnostico')).toHaveTextContent('¡Listo! Ya sé por dónde empezar.');
    expect(enviar).toHaveBeenCalledTimes(2);

    // "Practicar" empieza la práctica normal
    vi.mocked(nucleoService.iniciar).mockResolvedValue({ sesion_id: 6, estado: 'activa', tipo: 'practica', cantidad_problemas: 10, progreso: 0 });
    vi.mocked(nucleoService.siguiente).mockResolvedValue({
      sesion_completada: false, problema_sesion_id: 50, orden: 0, problema: sumaTeclado, intentos_restantes: 3,
    });
    await act(async () => { fireEvent.click(screen.getByTestId('practicar')); });
    expect(await screen.findByTestId('contador')).toHaveTextContent('1 de 10');
    expect(screen.queryByTestId('avance-diagnostico')).toBeNull();
  });

  it('si lo dejó a medias, sigue donde quedó sin la opción de descartarlo', async () => {
    vi.spyOn(nucleoService, 'estado').mockResolvedValue({ disponible: true, sesion_activa: diag, diagnostico_pendiente: true });
    montar();
    expect(await screen.findByTestId('intro-diagnostico')).toHaveTextContent('Seguimos donde quedamos');
    expect(screen.queryByTestId('descartar')).toBeNull();
    expect(screen.queryByTestId('aviso-sesion')).toBeNull();
  });

  it('el aviso del inicio no ofrece descartar el diagnóstico ni muestra conteos', () => {
    const onDescartar = vi.fn();
    render(<AvisoSesionAMedias sesion={diag} onContinuar={vi.fn()} onDescartar={onDescartar} />);
    expect(screen.getByTestId('aviso-diagnostico')).toHaveTextContent('Seguimos donde quedamos');
    expect(screen.queryByTestId('descartar')).toBeNull();
    expect(screen.queryByText(/de 16/)).toBeNull();
  });
});
