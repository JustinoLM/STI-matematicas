/**
 * Panel de configuración de una lección y pestaña "Por estudiante" (fase 6a).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { PanelLeccion } from '@/components/teacher/lecciones/PanelLeccion';
import { PorEstudiante } from '@/components/teacher/lecciones/PorEstudiante';
import type { LeccionSalon } from '@/types/nucleo';
import { catalogoBase, leccion } from './fixtures';

function montarPanel(l: LeccionSalon, catalogo = catalogoBase(), extra: Partial<Parameters<typeof PanelLeccion>[0]> = {}) {
  const props = {
    leccion: l, catalogo, soloLectura: false,
    onGuardar: vi.fn().mockResolvedValue(undefined), onRestaurar: vi.fn().mockResolvedValue(undefined),
    onCerrar: vi.fn(), ...extra,
  };
  render(<PanelLeccion {...props} />);
  return props;
}

describe('PanelLeccion', () => {
  it('envía signo al azar, sin dibujos, sin pista 3 y prioritaria', async () => {
    const cat = catalogoBase();
    const props = montarPanel(cat[0], cat);
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled();
    fireEvent.click(screen.getByLabelText('A veces visible, a veces oculto'));
    fireEvent.click(within(screen.getByRole('group', { name: 'Dibujos para contar' })).getByLabelText('Nunca'));
    fireEvent.click(screen.getByLabelText('Pista 3: casi la respuesta'));
    fireEvent.click(screen.getByTestId('check-prioritaria'));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(props.onCerrar).toHaveBeenCalled());
    expect(props.onGuardar).toHaveBeenCalledWith({
      config: { signo: 'azar', iconos: 'nunca', pistas: { 1: true, 2: true, 3: false }, prioritaria: true },
      prerrequisitos: null,
    });
  });

  it('con 3 prioritarias desactiva la casilla y explica cuáles son', () => {
    const cat = catalogoBase();
    for (const l of [cat[1], cat[5]]) l.prioritaria = true;
    cat.push(leccion('g1-u05-l01', { leccion_titulo: 'Sumemos hasta 19', habilitada: true, prioritaria: true }));
    montarPanel(cat[0], cat);
    expect(screen.getByTestId('check-prioritaria')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Ya tienes 3 lecciones prioritarias (Restemos de forma horizontal, Sumemos llevando, Sumemos hasta 19)',
    );
  });

  it('una de las 3 prioritarias puede quitarse la prioridad', () => {
    const cat = catalogoBase();
    for (const l of [cat[0], cat[1], cat[5]]) l.prioritaria = true;
    montarPanel(cat[0], cat);
    expect(screen.getByTestId('check-prioritaria')).toBeEnabled();
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('edita prerrequisitos: quita, agrega y envía solo la lista', async () => {
    const cat = catalogoBase();
    const props = montarPanel(cat[1], cat);
    fireEvent.click(screen.getByRole('button', { name: 'Quitar Sumemos de forma horizontal' }));
    expect(screen.getByText('Sin prerrequisitos.')).toBeInTheDocument();
    const select = screen.getByLabelText('Agregar prerrequisito');
    expect(within(select).queryByText(/Emparejar objetos/)).toBeNull();          // excluida
    expect(within(select).queryByText(/Restemos de forma horizontal/)).toBeNull(); // ella misma
    fireEvent.change(select, { target: { value: 'g1-u04-l03' } });
    fireEvent.click(screen.getByRole('button', { name: 'Agregar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(props.onGuardar).toHaveBeenCalledWith({ config: null, prerrequisitos: ['g1-u04-l03'] }));
  });

  it('muestra el error de ciclo del servidor y no cierra', async () => {
    const cat = catalogoBase();
    const onGuardar = vi.fn().mockRejectedValue(new Error('No se puede: «Restemos de forma horizontal» ya depende de esta lección.'));
    const props = montarPanel(cat[0], cat, { onGuardar });
    fireEvent.change(screen.getByLabelText('Agregar prerrequisito'), { target: { value: 'g1-u03-l02' } });
    fireEvent.click(screen.getByRole('button', { name: 'Agregar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('ya depende de esta lección');
    expect(props.onCerrar).not.toHaveBeenCalled();
  });

  it('prerrequisitos editados: muestra los del programa y permite restaurarlos', async () => {
    const cat = catalogoBase();
    cat[1] = { ...cat[1], prerrequisitos: [], prerrequisitos_editados: true };
    const props = montarPanel(cat[1], cat);
    expect(screen.getByText(/En el programa: Sumemos de forma horizontal/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Volver a los del programa/ }));
    await waitFor(() => expect(props.onRestaurar).toHaveBeenCalled());
    expect(await screen.findByText('1.º U3 L1 · Sumemos de forma horizontal')).toBeInTheDocument();
  });

  it('una lección sin habilitar no deja configurar, pero sí ver prerrequisitos', () => {
    const cat = catalogoBase();
    montarPanel(cat[2], cat);
    expect(screen.getByText(/no está habilitada/)).toBeInTheDocument();
    expect(screen.getByLabelText('A veces visible, a veces oculto')).toBeDisabled();
    expect(screen.getByLabelText('Agregar prerrequisito')).toBeEnabled();
  });
});

describe('PorEstudiante', () => {
  const estudiantes = [
    { estudiante_id: 1, codigo_estudiante: 'EST001', nombre_completo: 'Ana Pérez', nivel_actual: 1, precision_ultimos_15: 0, fecha_ingreso: '' },
    { estudiante_id: 2, codigo_estudiante: 'EST002', nombre_completo: 'Luis Gómez', nivel_actual: 1, precision_ultimos_15: 0, fecha_ingreso: '' },
  ];
  const asignaciones = [
    { id: 7, anio_lectivo_id: 1, estudiante_id: 1, leccion_id: 'g1-u03-l03', estado: 'activa' as const,
      fecha_asignacion: '2026-11-10T10:00:00', fecha_cierre: null, leccion_titulo: 'Sumemos y restemos 3 números', estudiante_nombre: 'Ana Pérez' },
    { id: 8, anio_lectivo_id: 1, estudiante_id: 2, leccion_id: 'g1-u03-l01', estado: 'cerrada_por_dominio' as const,
      fecha_asignacion: '2026-11-01T10:00:00', fecha_cierre: '2026-11-12T10:00:00', leccion_titulo: 'Sumemos de forma horizontal', estudiante_nombre: 'Luis Gómez' },
  ];

  function montarPor() {
    const props = {
      estudiantes, catalogo: catalogoBase(), asignaciones, ajustes: [{ estudiante_id: 2, banco_forzado: true }],
      soloLectura: false, onAsignar: vi.fn(), onCerrar: vi.fn(), onForzarBanco: vi.fn(),
    };
    render(<PorEstudiante {...props} />);
    return props;
  }

  it('lista las asignaciones abiertas, las cerradas y el banco forzado', () => {
    montarPor();
    expect(within(screen.getByTestId('estudiante-1')).getByText('Sumemos y restemos 3 números')).toBeInTheDocument();
    expect(screen.getByText(/Luis Gómez · Sumemos de forma horizontal · la dominó/)).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Siempre con opciones para Luis Gómez' })).toBeChecked();
    expect(screen.getByRole('switch', { name: 'Siempre con opciones para Ana Pérez' })).not.toBeChecked();
  });

  it('asigna solo lecciones con ejercicios, cierra y fuerza el banco', () => {
    const props = montarPor();
    const select = screen.getByLabelText('Lección para Ana Pérez');
    expect(within(select).queryByText(/Sumemos llevando/)).toBeNull();          // sin generador
    expect(within(select).queryByText(/Sumemos y restemos 3/)).toBeNull();      // ya asignada
    fireEvent.change(select, { target: { value: 'g1-u03-l02' } });
    fireEvent.click(within(screen.getByTestId('estudiante-1')).getByRole('button', { name: 'Asignar' }));
    expect(props.onAsignar).toHaveBeenCalledWith(1, 'g1-u03-l02');
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar Sumemos y restemos 3 números de Ana Pérez' }));
    expect(props.onCerrar).toHaveBeenCalledWith(7);
    fireEvent.click(screen.getByRole('switch', { name: 'Siempre con opciones para Ana Pérez' }));
    expect(props.onForzarBanco).toHaveBeenCalledWith(1, true);
  });
});
