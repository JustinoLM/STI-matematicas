import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { DndContext } from '@dnd-kit/core';
import { Expresion } from '@/components/nucleo/Expresion';
import { BancoRespuestas } from '@/components/nucleo/BancoRespuestas';
import { Iconos } from '@/components/nucleo/Iconos';
import { cantidad, comparacion, fraccion, signoOculto, sumaBanco, sumaTeclado } from './fixtures';

const conDnd = (ui: React.ReactNode) => render(<DndContext>{ui}</DndContext>);

describe('render de huecos', () => {
  it('hueco numérico con banco: vacío muestra "?" y lleno muestra el valor', () => {
    const { rerender } = conDnd(<Expresion problema={sumaBanco} respuestas={{}} />);
    const expresion = screen.getByTestId('expresion');
    expect(within(expresion).getByText('3')).toBeInTheDocument();
    expect(within(expresion).getByText('+')).toBeInTheDocument();
    expect(screen.getByTestId('hueco-resultado')).toHaveTextContent('?');
    rerender(<DndContext><Expresion problema={sumaBanco} respuestas={{ resultado: '7' }} /></DndContext>);
    expect(screen.getByTestId('hueco-resultado')).toHaveTextContent('7');
  });

  it('hueco de opción: muestra el texto de la opción elegida, no su id', () => {
    conDnd(<Expresion problema={signoOculto} respuestas={{ operador: 'resta' }} />);
    expect(screen.getByTestId('hueco-operador')).toHaveTextContent('−');
  });

  it('hueco de comparación <, >, =', () => {
    conDnd(<Expresion problema={comparacion} respuestas={{ rel: 'menor' }} />);
    expect(screen.getByTestId('hueco-rel')).toHaveTextContent('<');
  });

  it('tocar un hueco de arrastre solo elige el banco, no coloca nada', () => {
    const elegir = vi.fn();
    conDnd(<Expresion problema={sumaBanco} respuestas={{}} onElegirHuecoBanco={elegir} />);
    fireEvent.click(screen.getByTestId('hueco-resultado'));
    expect(elegir).toHaveBeenCalledWith('resultado');
    expect(screen.getByTestId('hueco-resultado')).toHaveTextContent('?');
  });

  it('hueco numérico con teclado: el campo activo se marca y se elige tocándolo', () => {
    const elegir = vi.fn();
    conDnd(<Expresion problema={sumaTeclado} respuestas={{ resultado: '37' }} campoActivo="resultado" onElegirCampo={elegir} />);
    const campo = screen.getByTestId('campo-resultado');
    expect(campo).toHaveTextContent('37');
    expect(campo).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(campo);
    expect(elegir).toHaveBeenCalledWith({ huecoId: 'resultado' });
  });

  it('hueco de fracción: numerador y denominador', () => {
    conDnd(<Expresion problema={fraccion} respuestas={{ f: { numerador: '3', denominador: '' } }} />);
    expect(screen.getByTestId('campo-f.numerador')).toHaveTextContent('3');
    expect(screen.getByTestId('campo-f.denominador')).toHaveTextContent('?');
  });

  it('hueco de cantidad: un campo por unidad, con su unidad', () => {
    conDnd(<Expresion problema={cantidad} respuestas={{ t: { h: '6', min: '15' } }} />);
    expect(screen.getByTestId('campo-t.h')).toHaveTextContent('6');
    expect(screen.getByTestId('campo-t.min')).toHaveTextContent('15');
    expect(screen.getByText('min')).toBeInTheDocument();
  });

  it('el hueco incorrecto queda marcado; en solo lectura no se puede tocar', () => {
    const { rerender } = conDnd(<Expresion problema={sumaBanco} respuestas={{ resultado: '6' }} marcas={new Set(['resultado'])} />);
    expect(screen.getByTestId('hueco-resultado')).toHaveAttribute('data-marcado', 'true');
    rerender(<DndContext><Expresion problema={sumaBanco} respuestas={{ resultado: '7' }} soloLectura /></DndContext>);
    expect(screen.getByTestId('hueco-resultado')).toBeDisabled();
  });
});

describe('banco de respuestas', () => {
  it('muestra 3 fichas grandes para arrastrar y marca la que está en el hueco', () => {
    conDnd(<BancoRespuestas huecoId="resultado" fichas={[{ valor: '6', texto: '6' }, { valor: '7', texto: '7' }, { valor: '1', texto: '1' }]} valorEnHueco="7" />);
    const banco = screen.getByTestId('banco');
    expect(within(banco).getAllByRole('button')).toHaveLength(3);
    expect(screen.getByTestId('ficha-7').className).toContain('border-dashed');
    expect(screen.getByTestId('ficha-6').className).not.toContain('border-dashed');
    expect(screen.getByTestId('ficha-6').className).toContain('min-h-[6rem]');
    expect(screen.getByTestId('ficha-6')).toHaveStyle({ touchAction: 'none' });
  });
});

describe('íconos', () => {
  it('uno por operando, sueltos hasta 10', () => {
    render(<Iconos cantidades={[3, 4]} icono="🪙" />);
    expect(screen.getAllByTestId('grupo-iconos')).toHaveLength(2);
    expect(screen.getAllByTestId('icono-suelto')).toHaveLength(7);
    expect(screen.queryByTestId('barra-diez')).toBeNull();
  });

  it('desde 11, barras de 10 y unidades sueltas', () => {
    render(<Iconos cantidades={[23]} icono="⭐" />);
    expect(screen.getAllByTestId('barra-diez')).toHaveLength(2);
    expect(screen.getAllByTestId('icono-suelto')).toHaveLength(3);
  });

  it('hasta 99: 10 + 30 son 4 barras compactas', () => {
    render(<Iconos cantidades={[10, 30]} icono="⭐" />);
    expect(screen.getAllByTestId('barra-diez')).toHaveLength(4);
    expect(screen.queryByTestId('icono-suelto')).toBeNull();
    expect(screen.getByTestId('iconos')).toHaveAttribute('data-compacto', 'true');
  });
});
