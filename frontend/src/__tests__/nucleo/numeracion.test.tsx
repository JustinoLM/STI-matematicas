/**
 * Fase 5b (numeración de 1.º): ordenar tarjetas, semirrecta de leer y ubicar, íconos para contar,
 * secuencias y las plantillas de enunciado nuevas.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProblemaNucleo, type EnviarRespuesta } from '@/components/nucleo/ProblemaNucleo';
import { EntreProblemas } from '@/components/nucleo/EntreProblemas';
import { Semirrecta } from '@/components/nucleo/Semirrecta';
import type { Problema, PresentacionSemirrectaPuntos, ProblemaExpresion, ResultadoRespuesta } from '@/types/nucleo';
import { instruccion, textoParaLeer } from '@/utils/nucleo/lectura';
import { textoEnunciado, VOCABULARIO_POR_TEMA } from '@/utils/nucleo/plantillas';
import { ANCHO, MARGEN, esSemirrectaDePuntos, geometriaPuntos } from '@/utils/nucleo/semirrecta';
import {
  comparacion,
  contarOcho,
  ordenar,
  ordenarConEnunciado,
  secuenciaDe2,
  semirrectaAnotar,
  semirrectaLeer,
  semirrectaLeerOcultas,
  semirrectaResolver,
  semirrectaUbicar,
  sumaBanco,
} from './fixtures';

const leer = semirrectaLeer.presentacion as PresentacionSemirrectaPuntos;
const leerOcultas = semirrectaLeerOcultas.presentacion as PresentacionSemirrectaPuntos;
const ubicar = semirrectaUbicar.presentacion as PresentacionSemirrectaPuntos;

const resultado = (extra: Partial<ResultadoRespuesta> = {}): ResultadoRespuesta => ({
  correcto: false, huecos: {}, intentos_restantes: 0, problema_terminado: true, solucion: null,
  experiencia_ganada: 1, evento_dominio: null, sesion_completada: false, ...extra,
});

function montar(problema: Problema, enviar: EnviarRespuesta = vi.fn(), tema = 'tema-piratas') {
  render(
    <ProblemaNucleo sesionId={5} icono="🪙" tema={tema} enviar={enviar} onTerminado={vi.fn()}
      turno={{ sesion_completada: false, problema_sesion_id: 9, orden: 0, problema, intentos_restantes: 3 }} />,
  );
}

// ─── Semirrecta de flechas ───────────────────────────────────────────────────

describe('semirrecta: leer y ubicar', () => {
  it('distingue los ejercicios de flechas de los de saltos de la fase 5a', () => {
    expect(esSemirrectaDePuntos(leer)).toBe(true);
    expect(esSemirrectaDePuntos(ubicar)).toBe(true);
    for (const p of [semirrectaResolver, semirrectaAnotar]) {
      expect(esSemirrectaDePuntos(p.presentacion as PresentacionSemirrectaPuntos)).toBe(false);
    }
  });

  it('leer: marcas de 1 en 1, números de 10 en 10 y una flecha sobre la marca del 57', () => {
    const g = geometriaPuntos(leer);
    expect(g.marcas).toHaveLength(31);
    expect(g.marcas.filter(m => m.etiqueta).map(m => m.valor)).toEqual([40, 50, 60, 70]);
    expect(g.marcas[0].x).toBe(MARGEN);
    expect(g.marcas[30].x).toBe(ANCHO - MARGEN);
    expect(g.flechas).toEqual([{ valor: 57, x: g.marcas[17].x, etiqueta: null }]);
    expect(g.casillas).toEqual([]);
  });

  it('leer con números sin escribir: recuadros, y el señalado lleva "?"', () => {
    const g = geometriaPuntos(leerOcultas);
    expect(g.marcas.filter(m => m.etiqueta)).toHaveLength(19);
    expect(g.casillas.map(c => [c.valor, c.senalada])).toEqual([[12, true], [13, false]]);
    render(<Semirrecta presentacion={leerOcultas} saltarin="🦜" />);
    const casillas = screen.getAllByTestId('casilla-oculta');
    expect(casillas).toHaveLength(2);
    expect(casillas[0]).toHaveTextContent('?');
    expect(casillas[1]).toHaveTextContent('');
    expect(screen.getByText('🦜')).toBeInTheDocument();
    expect(screen.getByTestId('semirrecta')).toHaveAttribute('data-ejercicio', 'leer');
  });

  it('ubicar: tres flechas con A, B y C, sin decir qué número señalan', () => {
    render(<Semirrecta presentacion={ubicar} saltarin="🦜" />);
    const flechas = screen.getAllByTestId('flecha');
    expect(flechas.map(f => f.getAttribute('data-etiqueta'))).toEqual(['A', 'B', 'C']);
    expect(screen.queryByText('66')).toBeNull();
    expect(screen.queryByText('🦜')).toBeNull();     // el personaje solo va en "leer"
    expect(screen.getByRole('img')).toHaveAccessibleName('Semirrecta del 50 al 80 con las flechas A, B, C.');
  });

  it('la solución escribe el número señalado (leer) y resalta la flecha correcta (ubicar)', () => {
    const { unmount } = render(<Semirrecta presentacion={leer} respuesta={{ valor: 57 }} />);
    expect(screen.getByTestId('numero-senalado')).toHaveTextContent('57');
    unmount();
    render(<Semirrecta presentacion={leerOcultas} respuesta={{ valor: 12 }} />);
    expect(screen.getAllByTestId('casilla-oculta')[0]).toHaveTextContent('12');
  });

  it('entre problemas, la solución de ubicar marca la flecha C con su número', () => {
    render(<EntreProblemas problema={semirrectaUbicar} onSiguiente={vi.fn()}
      resultado={resultado({ solucion: { flecha: 'C' } })} />);
    expect(screen.getByTestId('numero-senalado')).toHaveTextContent('66');
    expect(within(screen.getByTestId('expresion')).getByText('C')).toBeInTheDocument();
  });

  it('en el problema, la semirrecta de leer va con su instrucción y el hueco', () => {
    montar(semirrectaLeer);
    expect(screen.getByTestId('semirrecta')).toHaveAttribute('data-ejercicio', 'leer');
    expect(screen.getByText('Arrastra el número que señala la flecha.')).toBeInTheDocument();
    expect(screen.getByText('La capitana Coral se paró en la semirrecta. ¿En qué número está?')).toBeInTheDocument();
  });
});

// ─── Contar y secuencias ─────────────────────────────────────────────────────

describe('contar y secuencias', () => {
  it('los íconos para contar se dibujan aunque la configuración no muestre íconos de apoyo', () => {
    expect(contarOcho.modos.mostrar_iconos).toBe(false);
    montar(contarOcho);
    expect(screen.getAllByTestId('icono-suelto')).toHaveLength(8);
    expect(screen.getByText('Cuenta. Arrastra el número.')).toBeInTheDocument();
  });

  it('el 0: un recuadro vacío', () => {
    montar({ ...contarOcho, presentacion: { tipo: 'conteo', cantidades: [0] } });
    expect(screen.getByTestId('grupo-iconos')).toHaveAccessibleName('0');
    expect(screen.queryAllByTestId('icono-suelto')).toHaveLength(0);
  });

  it('la secuencia: números separados por comas y su instrucción', () => {
    montar(secuenciaDe2);
    expect(screen.getByTestId('expresion')).toHaveTextContent('6,8,?,12,14');
    expect(instruccion(secuenciaDe2)).toBe('Completa la secuencia. Arrastra el número que falta.');
    expect(textoParaLeer(secuenciaDe2, 'tema-piratas')).toBe(
      'La capitana Coral cuenta de 2 en 2 hacia adelante. ¿Qué número falta? '
      + 'Completa la secuencia. Arrastra el número que falta. 6 , 8 , ¿cuánto? , 12 , 14');
  });
});

// ─── Ordenar ─────────────────────────────────────────────────────────────────

describe('ordenar tarjetas', () => {
  const rectOriginal = Element.prototype.getBoundingClientRect;

  beforeEach(() => {
    // Las tarjetas en fila, de 100 en 100 px, según su lugar en la fila (jsdom no mide)
    Element.prototype.getBoundingClientRect = function (this: Element) {
      const id = this.getAttribute?.('data-testid') ?? '';
      const i = id.startsWith('tarjeta-') ? Array.from(this.parentElement?.children ?? []).indexOf(this) : 0;
      const r = { x: i * 100, y: 0, width: 80, height: 80 };
      return { ...r, top: r.y, left: r.x, right: r.x + r.width, bottom: r.y + r.height, toJSON() { return r; } } as DOMRect;
    };
  });

  afterEach(() => {
    Element.prototype.getBoundingClientRect = rectOriginal;
  });

  const valores = () => within(screen.getByTestId('tarjetas')).getAllByRole('button').map(b => b.textContent);

  it('muestra las tarjetas en el orden recibido, el sentido y el enunciado con el tema', () => {
    montar(ordenarConEnunciado);
    expect(valores()).toEqual(['37', '73', '45', '48']);
    expect(screen.getByText('Mayor')).toBeInTheDocument();
    expect(screen.getByText('La capitana Coral tiene estas tarjetas de números. ¿Cómo quedan de mayor a menor?'))
      .toBeInTheDocument();
    expect(screen.getByText('Ordena los números de mayor a menor.')).toBeInTheDocument();
  });

  it('mover una tarjeta con el teclado cambia el orden y se envía el orden nuevo', async () => {
    const enviar = vi.fn<Parameters<EnviarRespuesta>, ReturnType<EnviarRespuesta>>()
      .mockResolvedValue(resultado({ correcto: true }));
    montar(ordenar, enviar);                                   // 15, 12, 18 de menor a mayor
    const tarjeta = screen.getByTestId('tarjeta-15');
    tarjeta.focus();
    const pausa = () => new Promise(r => setTimeout(r, 20));
    await act(async () => { fireEvent.keyDown(tarjeta, { code: 'Space', key: ' ' }); await pausa(); });
    await act(async () => { fireEvent.keyDown(tarjeta, { code: 'ArrowRight', key: 'ArrowRight' }); await pausa(); });
    await act(async () => { fireEvent.keyDown(tarjeta, { code: 'Space', key: ' ' }); await pausa(); });
    expect(valores()).toEqual(['12', '15', '18']);
    fireEvent.click(screen.getByTestId('comprobar'));
    await waitFor(() => expect(enviar).toHaveBeenCalled());
    const envio = enviar.mock.calls[0][2];
    expect(envio.respuestas).toEqual({ orden: ['12', '15', '18'] });
    expect(envio.eventos.some(e => e.tipo === 'orden_cambiado')).toBe(true);
  });

  it('la solución muestra los números en orden', () => {
    render(<EntreProblemas problema={ordenar} onSiguiente={vi.fn()}
      resultado={resultado({ solucion: { orden: ['12', '15', '18'] } })} />);
    expect(screen.getByTestId('entre-problemas')).toHaveTextContent('12 15 18');
  });
});

// ─── Plantillas de la fase 5b ────────────────────────────────────────────────

describe('plantillas de numeración', () => {
  const con = (situacion: string, cantidades: number[], extra: Partial<ProblemaExpresion> = {}, variante = 0) =>
    ({ ...sumaBanco, ...extra, enunciado: { situacion, variante, cantidades } }) as ProblemaExpresion;

  it.each([
    ['contar', [], 'La capitana Coral buscó monedas de oro en el cofre. ¿Cuántas encontró?'],
    ['nombre', [], 'La capitana Coral escribió un número con letras. ¿Qué número es?'],
    ['formar', [3, 4], 'La capitana Coral tiene 3 monedas de oro en una mano y 4 en la otra. ¿Cuántas forman?'],
    ['formar', [40, 3], 'La capitana Coral tiene 4 bolsas de 10 monedas de oro y 3 sueltas. ¿Cuántas tiene?'],
    ['formar', [10, 6], 'La capitana Coral tiene 1 bolsa de 10 monedas de oro y 6 sueltas. ¿Cuántas tiene?'],
    ['formar_faltante', [2, 7], 'La capitana Coral tiene 2 monedas de oro y quiere tener 7. ¿Cuántas le faltan?'],
    ['grupos_total', [7], 'Hay 7 bolsas con 10 monedas de oro cada una. ¿Cuántas monedas de oro hay?'],
    ['grupos_cuantos', [70], 'La capitana Coral guarda 70 monedas de oro en bolsas de 10. ¿Cuántas bolsas llena?'],
    ['decenas_unidades', [53],
      'La capitana Coral guarda 53 monedas de oro en bolsas de 10. ¿Cuántas bolsas llena y cuántas le sobran?'],
    ['componer_decenas', [4, 0], 'La capitana Coral tiene 4 bolsas de 10 monedas de oro y ninguna suelta. ¿Cuántas tiene?'],
    ['descomponer', [77],
      'La capitana Coral quiere separar 77 monedas de oro en decenas completas y sueltas. ¿Cómo las separa?'],
    ['comparar_cantidades', [25, 34],
      'La capitana Coral tiene 25 monedas de oro y el pirata Tomás tiene 34. Compara los números: ¿quién tiene más?'],
    ['semirrecta_ubicar', [66], 'La capitana Coral busca el 66 en la semirrecta. ¿Qué flecha lo señala?'],
  ])('%s %j con el tema de piratas', (situacion, cantidades, texto) => {
    expect(textoEnunciado(con(situacion, cantidades), 'tema-piratas')).toBe(texto);
  });

  it('concuerda con objetos y recipientes masculinos (vaqueros)', () => {
    expect(textoEnunciado(con('grupos_total', [3]), 'tema-vaqueros'))
      .toBe('Hay 3 corrales con 10 caballos cada uno. ¿Cuántos caballos hay?');
    expect(textoEnunciado(con('grupos_cuantos', [30]), 'tema-vaqueros'))
      .toBe('La vaquera Rosa guarda 30 caballos en corrales de 10. ¿Cuántos corrales llena?');
    expect(textoEnunciado(con('formar', [2, 3], {}, 1), 'tema-vaqueros'))
      .toBe('En el rancho hay 2 caballos de un lado y 3 del otro. ¿Cuántos forman juntos?');
    expect(textoEnunciado(con('componer_decenas', [2, 0]), 'tema-vaqueros')).toMatch(/y ninguno suelto\./);
  });

  it('secuencias: el salto, el sentido y cuántos números faltan', () => {
    const dos = { ...secuenciaDe2, huecos: [...secuenciaDe2.huecos, { id: 'termino4', tipo: 'numero' as const }] };
    expect(textoEnunciado({ ...dos, enunciado: { situacion: 'secuencia_regresiva', variante: 0, cantidades: [10] } },
      'tema-default')).toBe('Ana cuenta de 10 en 10 hacia atrás. ¿Qué números faltan?');
  });

  it('todos los temas tienen recipiente para las decenas', () => {
    for (const v of Object.values(VOCABULARIO_POR_TEMA)) expect(v.grupo.plural).toBeTruthy();
  });

  it('comparar y ubicar no cambian la pregunta por el resultado (no es el signo oculto)', () => {
    const p = { ...comparacion, modos: { ...comparacion.modos, mostrar_signo: true },
      enunciado: { situacion: 'comparar_cantidades', variante: 0, cantidades: [45, 54] } };
    expect(textoEnunciado(p, 'tema-default')).toMatch(/¿quién tiene más\?$/);
    expect(textoEnunciado(semirrectaUbicar, 'tema-default')).toMatch(/¿Qué flecha lo señala\?$/);
  });

  it('lectura en voz alta de comparar y ubicar', () => {
    expect(textoParaLeer(semirrectaUbicar, 'tema-default')).toBe(
      'Ana busca el 66 en la semirrecta. ¿Qué flecha lo señala? '
      + 'Arrastra la letra de la flecha que señala el número. 66 está en la flecha ¿cuál?');
    expect(textoParaLeer(comparacion)).toContain('45 ¿mayor, menor o igual? 54');
  });
});
