/**
 * Envío de eventos desde la pantalla: arrastre con el sensor de teclado de @dnd-kit (espacio
 * para tomar y soltar; jsdom no mide, así que se simulan los rectángulos), teclado en pantalla,
 * uso de la voz, intento incorrecto y respuesta mal formada.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProblemaNucleo, type EnviarRespuesta } from '@/components/nucleo/ProblemaNucleo';
import type { Problema, ResultadoRespuesta } from '@/types/nucleo';
import { signoOculto, sumaBanco, sumaTeclado } from './fixtures';

const terminado = (correcto: boolean, extra: Partial<ResultadoRespuesta> = {}): ResultadoRespuesta => ({
  correcto, huecos: {}, intentos_restantes: 0, problema_terminado: true, solucion: null,
  experiencia_ganada: correcto ? 3 : 1, evento_dominio: null, sesion_completada: false, ...extra,
});

let ahora = 0;
const reloj = () => ahora;

function montar(problema: Problema, enviar: EnviarRespuesta, onTerminado = vi.fn()) {
  render(
    <ProblemaNucleo sesionId={5} icono="🍎" reloj={reloj} enviar={enviar} onTerminado={onTerminado}
      turno={{ sesion_completada: false, problema_sesion_id: 9, orden: 0, problema, intentos_restantes: 3 }} />,
  );
  return onTerminado;
}

/** Arrastra la ficha al hueco con el teclado: espacio para tomarla y espacio para soltarla */
async function arrastrar(valor: string) {
  const ficha = screen.getByTestId(`ficha-${valor}`);
  ficha.focus();
  await act(async () => { fireEvent.keyDown(ficha, { code: 'Space', key: ' ' }); });
  await act(async () => { fireEvent.keyDown(ficha, { code: 'Space', key: ' ' }); });
}

const rectOriginal = Element.prototype.getBoundingClientRect;

beforeEach(() => {
  ahora = 1000;
  // El hueco ocupa toda la pantalla y las fichas quedan dentro: al soltar, la ficha está sobre él
  Element.prototype.getBoundingClientRect = function (this: Element) {
    const id = this.getAttribute?.('data-testid') ?? '';
    const r = id.startsWith('hueco-') ? { x: 0, y: 0, width: 1000, height: 1000 } : { x: 10, y: 10, width: 50, height: 50 };
    return { ...r, top: r.y, left: r.x, right: r.x + r.width, bottom: r.y + r.height, toJSON() { return r; } } as DOMRect;
  };
});

afterEach(() => {
  Element.prototype.getBoundingClientRect = rectOriginal;
  vi.unstubAllGlobals();
});

describe('envío de eventos', () => {
  it('arrastrar, cambiar de opción y comprobar envía la opción, el cambio y el tiempo', async () => {
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>().mockResolvedValue(terminado(true));
    const onTerminado = montar(sumaBanco, enviar);
    expect(screen.getByTestId('comprobar')).toBeDisabled();

    ahora = 3000;
    await arrastrar('6');
    expect(screen.getByTestId('hueco-resultado')).toHaveTextContent('6');
    ahora = 4500;
    await arrastrar('7');
    expect(screen.getByTestId('hueco-resultado')).toHaveTextContent('7');

    ahora = 6000;
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    expect(enviar).toHaveBeenCalledTimes(1);
    const [sesion, problemaSesion, envio] = enviar.mock.calls[0];
    expect([sesion, problemaSesion]).toEqual([5, 9]);
    expect(envio.respuestas).toEqual({ resultado: '7' });
    expect(envio.tiempo_ms).toBe(5000);
    expect(envio.uso_voz).toBe(false);
    expect(envio.eventos).toEqual([
      { tipo: 'opcion_elegida', valor: { hueco: 'resultado', valor: '6' }, ms: 2000 },
      { tipo: 'opcion_elegida', valor: { hueco: 'resultado', valor: '7' }, ms: 3500 },
      { tipo: 'cambio_opcion', valor: { hueco: 'resultado', de: '6', a: '7' }, ms: 3500 },
    ]);
    expect(onTerminado).toHaveBeenCalledWith(expect.objectContaining({ correcto: true }), sumaBanco);
  });

  it('una ficha de otro hueco no entra; el hueco de opción recibe el id de la opción', async () => {
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>().mockResolvedValue(terminado(true));
    montar(signoOculto, enviar);
    await arrastrar('suma');
    expect(screen.getByTestId('hueco-operador')).toHaveTextContent('+');
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    expect(enviar.mock.calls[0][2].respuestas).toEqual({ operador: 'suma' });
  });

  it('el intento incorrecto marca el hueco, no termina y el siguiente intento lleva sus propios eventos', async () => {
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>()
      .mockResolvedValueOnce({ ...terminado(false), problema_terminado: false, intentos_restantes: 2, huecos: { resultado: false } })
      .mockResolvedValueOnce(terminado(true));
    const onTerminado = montar(sumaBanco, enviar);
    await arrastrar('6');
    ahora = 2000;
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    expect(onTerminado).not.toHaveBeenCalled();
    expect(screen.getByTestId('hueco-resultado')).toHaveAttribute('data-marcado', 'true');
    expect(screen.getByTestId('mensaje')).toHaveTextContent('Te quedan 2 intentos');

    ahora = 2600;
    await arrastrar('7');
    expect(screen.getByTestId('hueco-resultado')).not.toHaveAttribute('data-marcado');
    ahora = 3000;
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    const segundo = enviar.mock.calls[1][2];
    expect(segundo.tiempo_ms).toBe(1000);
    expect(segundo.eventos.map(e => e.tipo)).toEqual(['opcion_elegida', 'cambio_opcion']);
    expect(onTerminado).toHaveBeenCalledTimes(1);
  });

  it('con teclado envía el número escrito; una respuesta mal formada no pierde los eventos', async () => {
    const error = Object.assign(new Error('La respuesta no es válida'), {});
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>()
      .mockRejectedValueOnce(error)
      .mockResolvedValueOnce(terminado(true));
    montar(sumaTeclado, enviar);
    expect(screen.getByTestId('teclado')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '3' }));
    fireEvent.click(screen.getByRole('button', { name: '7' }));
    expect(screen.getByTestId('campo-resultado')).toHaveTextContent('37');
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    expect(screen.getByTestId('mensaje')).toHaveTextContent('La respuesta no es válida');
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    expect(enviar.mock.calls[1][2].respuestas).toEqual({ resultado: '37' });
  });
});

describe('lectura en voz alta', () => {
  function vozEn(lang: string | null) {
    const speak = vi.fn();
    vi.stubGlobal('speechSynthesis', {
      getVoices: () => (lang ? [{ lang, name: lang }] : []),
      speak, cancel: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(),
    });
    vi.stubGlobal('SpeechSynthesisUtterance', class { text: string; voice = null; lang = ''; rate = 1; constructor(t: string) { this.text = t; } });
    return speak;
  }

  it('sin voz en español no hay botón', () => {
    vozEn('en-US');
    montar(sumaBanco, vi.fn());
    expect(screen.queryByTestId('boton-voz')).toBeNull();
  });

  it('con voz en español lee la expresión y el uso se envía con el intento', async () => {
    const speak = vozEn('es-MX');
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>().mockResolvedValue(terminado(true));
    montar(sumaBanco, enviar);
    await waitFor(() => expect(screen.getByTestId('boton-voz')).toBeInTheDocument());
    ahora = 1800;
    fireEvent.click(screen.getByTestId('boton-voz'));
    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0][0].text).toContain('3 más 4 es igual a ¿cuánto?');
    await arrastrar('7');
    await act(async () => { fireEvent.click(screen.getByTestId('comprobar')); });
    const envio = enviar.mock.calls[0][2];
    expect(envio.uso_voz).toBe(true);
    expect(envio.eventos[0]).toEqual({ tipo: 'voz', ms: 800 });
  });
});

describe('columnas', () => {
  it('el problema va en una columna y el banco con "Comprobar" en la otra (dos columnas en horizontal)', () => {
    montar(sumaBanco, vi.fn());
    const problema = screen.getByTestId('columna-problema');
    const respuesta = screen.getByTestId('columna-respuesta');
    expect(within(problema).getByTestId('expresion')).toBeInTheDocument();
    expect(within(problema).getByTestId('iconos')).toBeInTheDocument();
    expect(within(respuesta).getByTestId('banco')).toBeInTheDocument();
    expect(within(respuesta).getByTestId('comprobar')).toBeInTheDocument();
    expect(screen.getByTestId('problema').className).toContain('md:landscape:grid-cols-2');
  });

  it('en modo teclado, el teclado va en la columna de respuesta', () => {
    montar(sumaTeclado, vi.fn());
    expect(within(screen.getByTestId('columna-respuesta')).getByTestId('teclado')).toBeInTheDocument();
  });
});
