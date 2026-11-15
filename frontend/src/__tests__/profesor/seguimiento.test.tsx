/**
 * Seguimiento del salón (fase 6b): tabla de avance, alertas, ficha del estudiante y plan por
 * trimestre, más los textos de las alertas.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { TablaAvance } from '@/components/teacher/seguimiento/TablaAvance';
import { ListaAlertas } from '@/components/teacher/seguimiento/ListaAlertas';
import { FichaEstudiante } from '@/components/teacher/seguimiento/FichaEstudiante';
import { PlanTrimestre } from '@/components/teacher/seguimiento/PlanTrimestre';
import { agruparAvance, textoAlerta, fechaDelServidor } from '@/lib/seguimiento';
import type { AlertaNucleo, FichaEstudiante as Ficha, FilaAvanceLeccion, Seguimiento } from '@/types/nucleo';
import { catalogoBase } from './fixtures';

function fila(id: string, extra: Partial<FilaAvanceLeccion> = {}): FilaAvanceLeccion {
  const [, u, l] = /u(\d+)-l(\d+)/.exec(id)!;
  return {
    leccion_id: id, titulo: `Lección ${id}`, grado: 1, unidad_numero: Number(u), unidad_titulo: `Unidad ${Number(u)}`,
    leccion_numero: Number(l), caminos: ['naturales.suma'], habilitada: true, prioritaria: false, total: 4, dominan: 2,
    porcentaje_dominan: 0.5, conteos: { dominado: 1, repaso: 1, en_progreso: 1, no_iniciado: 1 },
    estudiantes: { dominado: [1], repaso: [2], en_progreso: [3], no_iniciado: [4] }, ...extra,
  };
}

const ESTUDIANTES = [
  { id: 1, nombre: 'Ana Pérez', codigo: 'E1' }, { id: 2, nombre: 'Luis Gómez', codigo: 'E2' },
  { id: 3, nombre: 'Marta Ruiz', codigo: 'E3' }, { id: 4, nombre: 'Sofía Ríos', codigo: 'E4' },
];

function datos(extra: Partial<Seguimiento> = {}): Seguimiento {
  return {
    trimestre: null, estudiantes: ESTUDIANTES,
    por_leccion: [
      fila('g1-u03-l01', { prioritaria: true }),
      fila('g1-u03-l02', { porcentaje_dominan: 0.25, dominan: 1 }),
      fila('g1-u05-l01', { habilitada: false, total: 1, dominan: 0, porcentaje_dominan: 0,
        conteos: { dominado: 0, repaso: 0, en_progreso: 1, no_iniciado: 0 },
        estudiantes: { dominado: [], repaso: [], en_progreso: [3], no_iniciado: [] } }),
    ],
    por_estudiante: [
      { estudiante_id: 3, nombre: 'Marta Ruiz', codigo: 'E3', total: 2, conteos: { dominado: 0, repaso: 0, en_progreso: 2, no_iniciado: 0 },
        alertas_dificultad: 1, alertas_excelencia: 0 },
      { estudiante_id: 1, nombre: 'Ana Pérez', codigo: 'E1', total: 2, conteos: { dominado: 2, repaso: 0, en_progreso: 0, no_iniciado: 0 },
        alertas_dificultad: 0, alertas_excelencia: 1 },
    ],
    alertas_dificultad: 1, alertas_excelencia: 1, periodo: null, ...extra,
  };
}

function alerta(extra: Partial<AlertaNucleo> = {}): AlertaNucleo {
  return {
    tipo: 'dificultad', motivo: 'refuerzo_insuficiente', estudiante_id: 3, estudiante_nombre: 'Marta Ruiz',
    leccion_id: 'g1-u03-l02', leccion_titulo: 'Restemos de forma horizontal', precision: 0.3, problemas: 12,
    prerrequisito_id: 'g1-u02-l01', prerrequisito_titulo: 'Conozcamos los números del 0 al 10',
    precision_prerrequisito: 0.25, refuerzo_recibido: 6, prerrequisito_asignado: false, dominan_salon: 18, total_salon: 25,
    sugerencia: { accion: 'asignar', leccion_id: 'g1-u02-l01', titulo: 'Conozcamos los números del 0 al 10' },
    oculta: false, anio_lectivo_id: 9, salon_nombre: '1B', ...extra,
  };
}

const excelencia = alerta({
  tipo: 'excelencia', motivo: 'extension', estudiante_id: 1, estudiante_nombre: 'Ana Pérez', leccion_id: 'g2-u02-l01',
  leccion_titulo: 'Sumemos llevando', precision: 0.9, problemas: 10, prerrequisito_id: null, prerrequisito_titulo: null,
  precision_prerrequisito: null, refuerzo_recibido: 0, prerrequisito_asignado: false, dominan_salon: null, total_salon: null,
  sugerencia: { accion: 'habilitar', leccion_id: 'g2-u02-l01', titulo: 'Sumemos llevando' },
});

describe('textos y agrupación', () => {
  it('la alerta de dificultad nombra estudiante, lección, prerrequisito y compañeros', () => {
    const t = textoAlerta(alerta());
    expect(t.titulo).toBe('Marta Ruiz tiene dificultad con «Restemos de forma horizontal»');
    expect(t.detalle.join(' ')).toContain('Ya recibió 6 problemas de repaso de «Conozcamos los números del 0 al 10» y ahí sigue con 25 %');
    expect(t.detalle).toContain('18 de 25 compañeros ya la dominan.');
  });

  it('textos de los otros motivos', () => {
    expect(textoAlerta(alerta({ motivo: 'sin_refuerzo' })).detalle.join(' ')).toContain('conviene apoyarlo en clase');
    expect(textoAlerta(alerta({ motivo: 'detras_del_salon' })).detalle.join(' ')).toContain('la mayoría del salón ya lo hizo');
    expect(textoAlerta(excelencia).titulo).toBe('Ana Pérez sobresale en «Sumemos llevando»');
  });

  it('agrupa por unidad, deja las asignadas al final y puede ordenar por menor dominio', () => {
    const grupos = agruparAvance(datos().por_leccion);
    expect(grupos.map((g) => g.titulo)).toEqual(['1.º · Unidad 3 · Unidad 3', 'Asignadas individualmente']);
    expect(agruparAvance(datos().por_leccion, true)[0].filas.map((f) => f.leccion_id)).toEqual(['g1-u03-l02', 'g1-u03-l01']);
  });
});

describe('TablaAvance', () => {
  it('muestra una barra por lección y al tocarla los estudiantes por estado', () => {
    const onAbrirFicha = vi.fn();
    render(<TablaAvance datos={datos()} onAbrirFicha={onAbrirFicha} />);
    const filaL1 = screen.getByTestId('avance-g1-u03-l01');
    expect(within(filaL1).getByText('50 %')).toBeInTheDocument();
    expect(within(filaL1).getByText(/2 de 4 dominan · 1 en repaso · 1 en progreso/)).toBeInTheDocument();
    expect(within(filaL1).getByRole('img').getAttribute('aria-label')).toBe('Dominan: 1, En repaso: 1, En progreso: 1, Sin empezar: 1');
    expect(within(filaL1).queryByText('Marta Ruiz')).toBeNull();
    fireEvent.click(within(filaL1).getByRole('button', { expanded: false }));
    fireEvent.click(within(filaL1).getByRole('button', { name: 'Marta Ruiz' }));
    expect(onAbrirFicha).toHaveBeenCalledWith(3);
    expect(screen.getByText('Asignadas individualmente')).toBeInTheDocument();
  });

  it('la vista por estudiante pone primero a quien necesita atención', () => {
    render(<TablaAvance datos={datos()} onAbrirFicha={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Por estudiante' }));
    const filas = screen.getAllByTestId(/^avance-est-/);
    expect(filas.map((f) => f.getAttribute('data-testid'))).toEqual(['avance-est-3', 'avance-est-1']);
    expect(within(filas[0]).getByText('Dificultad en 1')).toBeInTheDocument();
    expect(within(filas[1]).getByText('Sobresale en 1')).toBeInTheDocument();
  });

  it('con un trimestre muestra lo que pasó en ese periodo', () => {
    const onAbrirFicha = vi.fn();
    render(<TablaAvance onAbrirFicha={onAbrirFicha} datos={datos({
      trimestre: 2, periodo: { numero: 2, inicio: '2026-06-08', fin: '2026-09-04', por_leccion: [{
        leccion_id: 'g1-u03-l01', titulo: 'Sumemos de forma horizontal', grado: 1, unidad_numero: 3, unidad_titulo: 'U3',
        leccion_numero: 1, habilitada: true, dominaron: [1, 2], practicaron: 3, problemas: 40, precision: 0.75,
      }] },
    })} />);
    const f = screen.getByTestId('periodo-g1-u03-l01');
    expect(within(f).getByText('75 %')).toBeInTheDocument();
    fireEvent.click(within(f).getByRole('button', { name: 'Luis Gómez' }));
    expect(onAbrirFicha).toHaveBeenCalledWith(2);
    expect(screen.queryByText('Primero las menos dominadas')).toBeNull();
  });

  it('sin lecciones habilitadas lo dice', () => {
    render(<TablaAvance datos={datos({ por_leccion: [] })} onAbrirFicha={vi.fn()} />);
    expect(screen.getByText(/Todavía no hay lecciones habilitadas/)).toBeInTheDocument();
  });
});

describe('ListaAlertas', () => {
  function montar(alertas: AlertaNucleo[], extra = {}) {
    const props = { alertas, onAsignar: vi.fn(), onHabilitar: vi.fn(), onOcultar: vi.fn(), onAbrirFicha: vi.fn(), ...extra };
    render(<ListaAlertas {...props} />);
    return props;
  }

  it('dificultad: asignar el prerrequisito, ver ficha y ocultar', () => {
    const a = alerta();
    const props = montar([a]);
    fireEvent.click(screen.getByRole('button', { name: 'Asignarle «Conozcamos los números del 0 al 10»' }));
    expect(props.onAsignar).toHaveBeenCalledWith(a, 'g1-u02-l01');
    fireEvent.click(screen.getByRole('button', { name: 'Ver ficha' }));
    expect(props.onAbrirFicha).toHaveBeenCalledWith(a);
    fireEvent.click(screen.getByRole('button', { name: /Ocultar/ }));
    expect(props.onOcultar).toHaveBeenCalledWith(a);
  });

  it('dificultad con el prerrequisito ya asignado: lo dice y no ofrece asignarlo otra vez', () => {
    montar([alerta({ sugerencia: null, prerrequisito_asignado: true })]);
    expect(screen.getByText(/Ya le asignaste «Conozcamos los números del 0 al 10»/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Asignarle/ })).not.toBeInTheDocument();
  });

  it('excelencia: habilitar para el salón o asignar solo al estudiante', () => {
    const props = montar([excelencia], { mostrarSalon: true });
    expect(screen.getByText('Excelencia · Salón 1B')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Habilitar para el salón' }));
    expect(props.onHabilitar).toHaveBeenCalledWith(excelencia);
    fireEvent.click(screen.getByRole('button', { name: 'Asignársela solo a Ana' }));
    expect(props.onAsignar).toHaveBeenCalledWith(excelencia, 'g2-u02-l01');
  });

  it('sin sugerencia ni en solo lectura no hay botones de acción', () => {
    montar([alerta({ sugerencia: null }), excelencia], { soloLectura: true });
    expect(screen.queryByRole('button', { name: /Asignar|Habilitar|Ocultar/ })).toBeNull();
    expect(screen.getAllByRole('button', { name: 'Ver ficha' })).toHaveLength(2);
  });

  it('sin alertas explica cuándo aparecen', () => {
    montar([]);
    expect(screen.getByText(/Aparecen cuando alguien se atasca/)).toBeInTheDocument();
  });
});

describe('FichaEstudiante', () => {
  const ficha: Ficha = {
    estudiante: { id: 3, nombre: 'Marta Ruiz', codigo: 'E3' },
    salon: { anio_lectivo_id: 9, nombre: '1B', grado: 1, anio: 2026, cerrado: false },
    trimestre: null, periodo: null, banco_forzado: true,
    lecciones: [{
      leccion_id: 'g1-u03-l02', titulo: 'Restemos de forma horizontal', grado: 1, unidad_numero: 3, leccion_numero: 2,
      caminos: ['naturales.resta'], estado: 'en_progreso', habilitada: true, prioritaria: false, asignada: false,
      aciertos_recientes: 3, problemas_recientes: 10, problemas_periodo: 0, aciertos_periodo: 0,
      extension_problemas: 0, extension_aciertos: 0, ultima_practica: '2026-11-12T15:00:00',
    }],
    por_camino: [{ camino: 'naturales.resta', nombre: 'Resta con naturales', total: 2, dominadas: 1, en_progreso: 1 }],
    errores: [
      { codigo: 'naturales.resta.sumo', descripcion: 'Sumó en vez de restar', camino: 'naturales.resta', camino_nombre: 'Resta con naturales', veces: 7 },
      { codigo: 'no_clasificado', descripcion: 'Otro error (sin clasificar)', camino: null, camino_nombre: null, veces: 1 },
    ],
    asignaciones: [{ id: 1, anio_lectivo_id: 9, estudiante_id: 3, leccion_id: 'g1-u02-l01', estado: 'activa',
      fecha_asignacion: '2026-11-10T10:00:00', fecha_cierre: null, leccion_titulo: 'Conozcamos los números del 0 al 10', estudiante_nombre: 'Marta Ruiz' }],
    sesiones: [{ id: 5, estado: 'completada', fecha_inicio: '2026-11-12T15:00:00', fecha_fin: '2026-11-12T15:09:00',
      problemas: 10, cantidad_problemas: 10, aciertos: 4 }],
    anios_anteriores: [{ anio_lectivo_id: 2, anio: 2025, salon: 'K-B', grado: 1, problemas: 140, aciertos: 105, lecciones_dominadas: 3 }],
  };

  it('muestra caminos, lecciones, errores con nombre para docentes, sesiones y años anteriores', () => {
    render(<FichaEstudiante ficha={ficha} />);
    expect(within(screen.getByTestId('camino-naturales.resta')).getByText('domina 1 de 2')).toBeInTheDocument();
    const fila = screen.getByTestId('ficha-leccion-g1-u03-l02');
    expect(within(fila).getByText('En progreso')).toBeInTheDocument();
    expect(within(fila).getByText('3 de 10')).toBeInTheDocument();
    const errores = screen.getAllByTestId('error-frecuente');
    expect(errores[0]).toHaveTextContent('Sumó en vez de restar');
    expect(errores[0]).toHaveTextContent('7 veces');
    expect(screen.queryByText('naturales.resta.sumo')).toBeNull();          // nunca el código interno
    expect(screen.getByText('Asignada: Conozcamos los números del 0 al 10')).toBeInTheDocument();
    expect(screen.getByText(/Siempre con opciones/)).toBeInTheDocument();
    expect(screen.getByText(/10 de 10 problemas · 4 aciertos · 9 min/)).toBeInTheDocument();
    expect(screen.getByTestId('anios-anteriores')).toHaveTextContent('2025 · Salón K-B (1.º) · 3 lecciones dominadas · 140 problemas (75 % de acierto)');
  });

  it('con un trimestre usa los números del periodo', () => {
    render(<FichaEstudiante ficha={{ ...ficha, trimestre: 1, periodo: { numero: 1, inicio: '2026-03-02', fin: '2026-05-29' }, errores: [] }} />);
    expect(screen.getByText('En el trimestre')).toBeInTheDocument();
    expect(within(screen.getByTestId('ficha-leccion-g1-u03-l02')).getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.getByText('Sin errores registrados en este trimestre.')).toBeInTheDocument();
  });
});

describe('PlanTrimestre', () => {
  const plan = {
    trimestres: [
      { numero: 1, inicio: '2026-03-02', fin: '2026-05-29' }, { numero: 2, inicio: '2026-06-08', fin: '2026-09-04' },
      { numero: 3, inicio: '2026-09-14', fin: '2026-12-11' },
    ],
    vigente: 3, plan: { 'g1-u03-l01': [1, 2] },
  };

  it('marca trimestres, guarda el plan y muestra el ajuste manual', async () => {
    const cat = catalogoBase();
    cat[0] = { ...cat[0], plan_trimestres: [1, 2], ajuste_manual: true };
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    const onDevolver = vi.fn();
    render(<PlanTrimestre catalogo={cat} plan={plan} gradoSalon={1} soloLectura={false} onGuardar={onGuardar} onDevolver={onDevolver} />);
    expect(screen.getByTestId('trimestre-vigente')).toHaveTextContent('Trimestre vigente: T3');
    const guardar = screen.getByRole('button', { name: 'Guardar plan' });
    expect(guardar).toBeDisabled();
    fireEvent.click(screen.getByLabelText('Restemos de forma horizontal en el trimestre 3'));
    fireEvent.click(screen.getByLabelText('Sumemos de forma horizontal en el trimestre 1'));
    fireEvent.click(guardar);
    await waitFor(() => expect(onGuardar).toHaveBeenCalledWith({ 'g1-u03-l01': [2], 'g1-u03-l02': [3] }));
    const filaManual = screen.getByTestId('plan-g1-u03-l01');
    expect(within(filaManual).getByText(/Ajuste manual/)).toBeInTheDocument();
    fireEvent.click(within(filaManual).getByRole('button', { name: /Devolver al plan/ }));
    expect(onDevolver).toHaveBeenCalledWith('g1-u03-l01');
  });

  it('solo muestra el grado del salón con ejercicios, salvo que se pidan todas', () => {
    render(<PlanTrimestre catalogo={catalogoBase()} plan={{ ...plan, plan: {}, vigente: null }} gradoSalon={1}
      soloLectura={false} onGuardar={vi.fn()} onDevolver={vi.fn()} />);
    expect(screen.queryByTestId('plan-g2-u03-l01')).toBeNull();
    expect(screen.getByText(/El año todavía no empezó/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Ver también lecciones de otros grados/));
    expect(screen.getByTestId('plan-g2-u03-l01')).toBeInTheDocument();
  });
});

describe('fechaDelServidor', () => {
  it('lee como UTC las horas sin zona y deja las fechas solas en hora local', () => {
    expect(fechaDelServidor('2026-11-15T00:02:00').toISOString()).toBe('2026-11-15T00:02:00.000Z');
    expect(fechaDelServidor('2026-11-15T00:02:00Z').toISOString()).toBe('2026-11-15T00:02:00.000Z');
    expect(fechaDelServidor('2026-11-15T00:02:00+00:00').toISOString()).toBe('2026-11-15T00:02:00.000Z');
    const dia = fechaDelServidor('2026-11-14');
    expect([dia.getFullYear(), dia.getMonth(), dia.getDate()]).toEqual([2026, 10, 14]);
  });
});
