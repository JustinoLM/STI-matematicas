import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Semirrecta } from '@/components/nucleo/Semirrecta';
import type { PresentacionSemirrecta } from '@/types/nucleo';
import { ANCHO, MARGEN, geometriaSemirrecta, llegadaDe } from '@/utils/nucleo/semirrecta';
import { semirrectaAnotar, semirrectaResolver } from './fixtures';

const hasta20 = semirrectaResolver.presentacion as PresentacionSemirrecta;
const de5en5 = semirrectaAnotar.presentacion as PresentacionSemirrecta;

describe('geometría de la semirrecta', () => {
  it('hasta 20: una marca y un número por unidad, dentro del dibujo', () => {
    const g = geometriaSemirrecta(hasta20);
    expect(g.marcas).toHaveLength(21);
    expect(g.marcas.every(m => m.etiqueta)).toBe(true);
    expect(g.marcas[0].x).toBe(MARGEN);
    expect(g.marcas[20].x).toBe(ANCHO - MARGEN);
  });

  it('los saltos van del inicio a la llegada, con el conteo acumulado', () => {
    const g = geometriaSemirrecta(hasta20);
    expect(g.arcos.map(a => [a.desde, a.hasta])).toEqual([[5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11]]);
    expect(g.arcos.map(a => a.conteo)).toEqual(['1', '2', '3', '4', '5', '6']);
    expect(g.arcos.every(a => a.x2 > a.x1)).toBe(true);
    expect(llegadaDe(hasta20)).toBe(11);
  });

  it('resolver no muestra la llegada; anotar sí', () => {
    expect(geometriaSemirrecta(hasta20).llegada).toBeNull();
    expect(geometriaSemirrecta(hasta20, { mostrarLlegada: true }).llegada?.valor).toBe(11);
    expect(geometriaSemirrecta(de5en5).llegada?.valor).toBe(55);
  });

  it('hasta 99: números de 10 en 10 y saltos de 5 hacia la izquierda', () => {
    const g = geometriaSemirrecta(de5en5);
    expect(g.marcas).toHaveLength(51);
    expect(g.marcas.filter(m => m.etiqueta).map(m => m.valor)).toEqual([50, 60, 70, 80, 90, 100]);
    expect(g.arcos.map(a => a.conteo)).toEqual(['5', '10', '15', '20', '25', '30', '35']);
    expect(g.arcos.every(a => a.x2 < a.x1)).toBe(true);
    expect(g.descripcion).toBe('Semirrecta del 50 al 100. Parte del 90 y da 7 saltos de 5 hacia la izquierda, hasta el 55.');
  });

  it('el número de la llegada baja una fila si choca con el de una decena', () => {
    const g = geometriaSemirrecta({ ...de5en5, desde: 80, hasta: 100, inicio: 92, salto: 1, saltos: 3, llegada: 89 });
    expect(g.numerosExtra).toEqual([
      expect.objectContaining({ valor: 92, tipo: 'inicio', abajo: false }),
      expect.objectContaining({ valor: 89, tipo: 'llegada', abajo: true }),
    ]);
    expect(geometriaSemirrecta(hasta20).numerosExtra).toEqual([]);   // de 1 en 1 ya llevan número
  });

  it('con saltos de 1 en la semirrecta de 0 a 100 no escribe el conteo (no cabe)', () => {
    const g = geometriaSemirrecta({ ...de5en5, desde: 0, hasta: 100, salto: 1, saltos: 8, llegada: undefined });
    expect(g.arcos.every(a => a.conteo === null)).toBe(true);
  });
});

describe('componente Semirrecta', () => {
  it('dibuja las marcas, los saltos, el inicio y quien salta', () => {
    render(<Semirrecta presentacion={hasta20} saltarin="🐰" />);
    expect(screen.getAllByTestId('marca')).toHaveLength(21);
    expect(screen.getAllByTestId('salto')).toHaveLength(6);
    expect(screen.getByTestId('inicio')).toBeInTheDocument();
    expect(screen.queryByTestId('llegada')).toBeNull();
    expect(screen.getByRole('img', { name: /Parte del 5 y da 6 saltos hacia la derecha\.$/ })).toBeInTheDocument();
    expect(screen.getByText('🐰')).toBeInTheDocument();
  });

  it('marca la llegada y escribe el inicio aunque no sea una decena', () => {
    render(<Semirrecta presentacion={de5en5} />);
    expect(screen.getByTestId('llegada')).toBeInTheDocument();
    expect(screen.queryByTestId('numero-inicio')).toBeNull();   // 90 ya lleva número
    render(<Semirrecta presentacion={{ ...de5en5, inicio: 85, saltos: 6 }} />);
    expect(screen.getByTestId('numero-inicio')).toHaveTextContent('85');
  });
});
