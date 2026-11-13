/**
 * Catálogo de lecciones del salón (fase 6a): grado por defecto, agrupado por unidad, otros grados,
 * solo habilitadas, insignias e interruptor; y la lógica pura que lo alimenta.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { CatalogoLecciones } from '@/components/teacher/lecciones/CatalogoLecciones';
import { agruparPorUnidad, insignias, puedeSerPrioritaria, resumenConfig } from '@/lib/leccionesSalon';
import { catalogoBase, leccion } from './fixtures';

function montar(extra: Partial<Parameters<typeof CatalogoLecciones>[0]> = {}) {
  const props = {
    catalogo: catalogoBase(), gradoSalon: 1, soloLectura: false,
    onCambiarHabilitada: vi.fn(), onAbrir: vi.fn(), ...extra,
  };
  render(<CatalogoLecciones {...props} />);
  return props;
}

describe('lógica del catálogo', () => {
  it('agrupa por unidad en el orden del programa y filtra por grado', () => {
    const unidades = agruparPorUnidad(catalogoBase(), { grado: 1, soloHabilitadas: false });
    expect(unidades.map((u) => u.numero)).toEqual([1, 3, 4]);
    expect(unidades[1].lecciones.map((l) => l.leccion_numero)).toEqual([1, 2, 3]);
  });

  it('solo habilitadas reúne todos los grados', () => {
    const unidades = agruparPorUnidad(catalogoBase(), { grado: 1, soloHabilitadas: true });
    expect(unidades.flatMap((u) => u.lecciones.map((l) => l.id))).toEqual(['g1-u03-l01', 'g1-u03-l02', 'g2-u03-l01']);
  });

  it('permite como máximo 3 prioritarias, contando la propia', () => {
    const cat = ['g1-u03-l01', 'g1-u03-l02', 'g1-u03-l03'].map((id) => leccion(id, { habilitada: true, prioritaria: true }));
    cat.push(leccion('g1-u04-l01', { habilitada: true }));
    expect(puedeSerPrioritaria(cat, 'g1-u04-l01')).toBe(false);
    expect(puedeSerPrioritaria(cat, 'g1-u03-l01')).toBe(true);
    cat[0].habilitada = false;
    expect(puedeSerPrioritaria(cat, 'g1-u04-l01')).toBe(true);
  });

  it('resume la configuración y describe las insignias en lenguaje de docente', () => {
    expect(resumenConfig(leccion('g1-u03-l01', { signo: 'azar', iconos: 'nunca', pistas: { 1: true, 2: true, 3: false } })))
      .toBe('Signo a veces oculto · Sin dibujos · Sin pista 3');
    expect(resumenConfig(leccion('g1-u03-l01'))).toBe('');
    const [, , , , parcial, sinGen, decimales] = catalogoBase();
    expect(insignias(parcial).map((i) => i.texto)).toEqual(['Parcial']);
    expect(insignias(sinGen).map((i) => i.texto)).toEqual(['Sin ejercicios todavía']);
    expect(insignias(decimales).map((i) => i.texto)).toEqual(['Se practica en decimales']);
  });
});

describe('CatalogoLecciones', () => {
  it('muestra por defecto el grado del salón, agrupado por unidad', () => {
    montar();
    const unidades = screen.getAllByRole('region');
    expect(unidades.map((u) => within(u).getByRole('heading').textContent)).toEqual([
      'Unidad 1 · Unidad 1 de 1.º', 'Unidad 3 · Unidad 3 de 1.º', 'Unidad 4 · Unidad 4 de 1.º',
    ]);
    expect(screen.queryByText('Sumemos llevando')).toBeNull();
    expect(screen.getByText(/1 de 2\.º/)).toBeInTheDocument();   // aviso de habilitadas en otros grados
  });

  it('la excluida no tiene interruptor y muestra el motivo', () => {
    montar();
    const fila = screen.getByTestId('leccion-g1-u01-l01');
    expect(within(fila).queryByRole('switch')).toBeNull();
    expect(within(fila).getByText(/prenumérica/)).toBeInTheDocument();
  });

  it('se pueden ver y habilitar lecciones de otro grado', () => {
    const props = montar();
    fireEvent.click(screen.getByRole('button', { name: /^2\.º/ }));
    expect(screen.getByText(/Estás viendo lecciones de 2\.º/)).toBeInTheDocument();
    expect(within(screen.getByTestId('leccion-g2-u03-l01')).getByText('Sin ejercicios todavía')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('switch', { name: 'Habilitar Decimales de 2.º' }));
    expect(props.onCambiarHabilitada).toHaveBeenCalledWith(expect.objectContaining({ id: 'g2-u05-l01' }), true);
  });

  it('el interruptor deshabilita y el botón abre la configuración', () => {
    const props = montar();
    fireEvent.click(screen.getByRole('switch', { name: 'Habilitar Sumemos de forma horizontal' }));
    expect(props.onCambiarHabilitada).toHaveBeenCalledWith(expect.objectContaining({ id: 'g1-u03-l01' }), false);
    fireEvent.click(within(screen.getByTestId('leccion-g1-u03-l02')).getByRole('button', { name: 'Configurar' }));
    expect(props.onAbrir).toHaveBeenCalledWith(expect.objectContaining({ id: 'g1-u03-l02' }));
  });

  it('solo habilitadas muestra las de todos los grados', () => {
    montar();
    fireEvent.click(screen.getByLabelText(/Ver solo las habilitadas/));
    expect(screen.getByText('Sumemos llevando')).toBeInTheDocument();
    expect(screen.queryByText('Sumemos y restemos 3 números')).toBeNull();
  });

  it('en solo lectura los interruptores están desactivados', () => {
    montar({ soloLectura: true });
    for (const s of screen.getAllByRole('switch')) expect(s).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Configurar' })).toBeNull();
  });
});
