/**
 * Motivación del núcleo (fase 7b): barras (nivel, caminos, casillas hacia el dominio), mapa del camino
 * según el tema, celebraciones entre problemas y al final, medallero del núcleo, y "Comprobar" en una
 * barra pegada abajo en vertical.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { BarraNivel, BarrasCamino, CasillasDominio } from '@/components/nucleo/motivacion/Barras';
import { ListaCelebraciones } from '@/components/nucleo/motivacion/Celebraciones';
import { textoCelebracion } from '@/components/nucleo/motivacion/textos';
import { MapaCamino } from '@/components/nucleo/motivacion/MapaCamino';
import { MedalleroNucleo } from '@/components/nucleo/motivacion/MedalleroNucleo';
import { EntreProblemas } from '@/components/nucleo/EntreProblemas';
import { ResumenSesion } from '@/components/nucleo/ResumenSesion';
import { ProblemaNucleo } from '@/components/nucleo/ProblemaNucleo';
import { nucleoService } from '@/services/nucleoService';
import type { Celebracion, MedallaNucleo, ParadaMapa, ResultadoRespuesta } from '@/types/nucleo';
import { sumaBanco } from './fixtures';

afterEach(() => { vi.restoreAllMocks(); });

function conQuery(ui: ReactElement) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>);
}

const medalla = (extra: Partial<MedallaNucleo> = {}): MedallaNucleo => ({
  tipo: 'leccion', clave: 'g1-u03-l01', grado_medalla: '', titulo: 'Sumemos de forma horizontal',
  descripcion: 'Dominaste 1.º U3 L1.', meta: 1, logradas: 1, obtenida: true, fecha: '2026-11-15T04:30:00Z', ...extra,
});

const parada = (id: string, n: number, estado: ParadaMapa['estado'], extra: Partial<ParadaMapa> = {}): ParadaMapa => ({
  leccion_id: id, titulo: `Lección ${n}`, leccion_numero: n, estado, en_practica: true, siguiente: false,
  casillas: Array(10).fill(null), aciertos: 0, meta: 8, ventana: 10, ...extra,
});

describe('barras', () => {
  it('nivel y experiencia hacia el siguiente', () => {
    render(<BarraNivel nivel={4} enNivel={216} paraSubir={240} />);
    expect(screen.getByTestId('barra-nivel')).toHaveTextContent('216 de 240 de experiencia para el nivel 5');
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '216');
  });

  it('cada camino: dominadas sobre el total, y las por confirmar aparte', () => {
    render(<BarrasCamino caminos={[{ camino: 'naturales.suma', nombre: 'Suma', total: 8, dominadas: 2, provisionales: 1 }]} />);
    expect(screen.getByTestId('barra-camino-naturales.suma')).toHaveTextContent('2 de 8 lecciones · 1 por confirmar');
  });

  it('las casillas hacia el dominio no restan ni usan rojo: un fallo deja la casilla vacía', () => {
    const casillas = [true, false, true, true, false, true, true, null, null, null];
    render(<CasillasDominio casillas={casillas} aciertos={5} meta={8} />);
    const todas = screen.getAllByTestId('casilla');
    expect(todas).toHaveLength(10);
    expect(todas.filter(c => c.dataset.estado === 'estrella')).toHaveLength(5);
    expect(todas.filter(c => c.dataset.estado === 'sin-estrella')).toHaveLength(2);
    expect(screen.getByTestId('casillas-dominio').innerHTML).not.toMatch(/red-|rose-/);
    expect(screen.getByTestId('casillas-dominio').textContent).not.toMatch(/[−-]\s*\d/);
    expect(screen.getByTestId('casillas-dominio')).toHaveTextContent('Llevas 5 estrellas en tus últimos problemas. Meta: 8.');
  });
});

describe('mapa del camino', () => {
  const unidades = [{
    unidad_numero: 3, titulo: 'Suma y resta',
    lecciones: [
      parada('a', 1, 'dominado'), parada('b', 2, 'provisional'), parada('c', 3, 'en_progreso', { siguiente: true }),
      parada('d', 4, 'no_iniciado', { en_practica: false }),
    ],
  }];

  it('dominadas encendidas, la siguiente visible, la provisional distinta y las demás tenues', () => {
    render(<MapaCamino unidades={unidades} temaId="tema-default" grado={1} elegida={null} onElegir={vi.fn()} />);
    expect(screen.getByTestId('parada-a').className).toMatch(/bg-emerald-500/);
    expect(screen.getByTestId('parada-b').className).toMatch(/border-dashed/);
    expect(screen.getByTestId('parada-b')).toHaveAccessibleName(/Por confirmar/);
    expect(within(screen.getByTestId('parada-c')).getByText('¡Vas aquí!')).toBeInTheDocument();
    expect(screen.getByTestId('parada-d').className).toMatch(/opacity-40/);
    expect(screen.getByTestId('parada-a').className).not.toMatch(/opacity-40/);
  });

  it('se decora según el tema activo, con dibujos propios', () => {
    const { rerender } = render(<MapaCamino unidades={unidades} temaId="tema-piratas" grado={1} elegida={null} onElegir={vi.fn()} />);
    expect(screen.getByTestId('mapa-camino')).toHaveAttribute('data-tema', 'tema-piratas');
    expect(screen.getByText(/La ruta del tesoro/)).toBeInTheDocument();
    expect(screen.getAllByTestId('adorno')).toHaveLength(4);
    rerender(<MapaCamino unidades={unidades} temaId="tema-astronautas" grado={1} elegida={null} onElegir={vi.fn()} />);
    expect(screen.getByText(/Viaje por las estrellas/)).toBeInTheDocument();
    rerender(<MapaCamino unidades={unidades} temaId="tema-que-no-existe" grado={1} elegida={null} onElegir={vi.fn()} />);
    expect(screen.getByText(/Mi camino/)).toBeInTheDocument();
  });
});

describe('celebraciones', () => {
  const todas: Celebracion[] = [
    { tipo: 'leccion_dominada', leccion_id: 'a', titulo: 'Sumemos', experiencia: 50 },
    { tipo: 'leccion_recuperada', leccion_id: 'a', titulo: 'Sumemos', experiencia: 10 },
    { tipo: 'medalla', medalla: medalla({ tipo: 'camino', grado_medalla: 'bronce', titulo: 'Suma de naturales' }) },
    { tipo: 'nivel', nivel: 5 },
  ];

  it('textos de lección dominada, recuperada, medalla y nivel', () => {
    expect(todas.map(textoCelebracion)).toEqual([
      '¡Dominaste «Sumemos»!',
      '¡La recuperaste! «Sumemos» vuelve a estar dominada.',
      '¡Medalla nueva! Suma de naturales · Bronce',
      '¡Subiste al nivel 5!',
    ]);
  });

  it('entre problemas se muestran después del acierto', () => {
    const resultado: ResultadoRespuesta = {
      correcto: true, huecos: {}, intentos_restantes: 2, problema_terminado: true, solucion: null,
      experiencia_ganada: 53, evento_dominio: 'dominada', sesion_completada: false, celebraciones: todas.slice(0, 1).concat(todas.slice(3)),
    };
    render(<EntreProblemas resultado={resultado} problema={sumaBanco} onSiguiente={vi.fn()} />);
    expect(screen.getByTestId('celebracion-leccion_dominada')).toBeInTheDocument();
    expect(screen.getByTestId('celebracion-nivel')).toHaveTextContent('¡Subiste al nivel 5!');
    expect(screen.queryByText('¡Ya dominas esta lección!')).toBeNull();     // no se repite
  });

  it('al final de la sesión: lo celebrado y la barra de experiencia', () => {
    render(<ResumenSesion resultados={[{ correcto: true, experiencia: 53 }]} celebraciones={todas}
      nivel={{ nivel: 5, experiencia_en_nivel: 56, experiencia_para_subir: 300 }} onInicio={vi.fn()} onOtra={vi.fn()} />);
    expect(within(screen.getByTestId('resumen')).getAllByRole('listitem')).toHaveLength(4);
    expect(screen.getByTestId('barra-nivel')).toHaveTextContent('56 de 300 de experiencia para el nivel 6');
  });

  it('sin celebraciones no se muestra nada', () => {
    const { container } = render(<ListaCelebraciones celebraciones={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('medallero del núcleo', () => {
  it('agrupa hitos, unidades y lecciones; las no ganadas muestran su avance', async () => {
    vi.spyOn(nucleoService, 'medallas').mockResolvedValue({
      grado: 1, obtenidas: 2, total: 4, medallas: [
        medalla(),
        medalla({ tipo: 'unidad', clave: 'g1-u03', titulo: 'Suma y resta', meta: 3, logradas: 1, obtenida: false, fecha: null }),
        medalla({ tipo: 'camino', clave: 'naturales.suma@1', grado_medalla: 'bronce', titulo: 'Suma', meta: 2, logradas: 2 }),
        medalla({ tipo: 'camino', clave: 'naturales.suma@1', grado_medalla: 'oro', titulo: 'Suma', meta: 8, logradas: 2, obtenida: false, fecha: null }),
      ],
    });
    conQuery(<MedalleroNucleo />);
    expect(await screen.findByTestId('medallero-nucleo')).toHaveTextContent('Tienes 2 de 4 medallas de 1.º.');
    expect(screen.getByText('Hitos de mis caminos (1 de 2)')).toBeInTheDocument();
    expect(screen.getByTestId('medalla-unidad-g1-u03')).toHaveTextContent('1 de 3');
    expect(screen.getByTestId('medalla-camino-naturales.suma@1-oro')).toHaveAttribute('data-obtenida', 'false');
    expect(screen.getByTestId('medalla-camino-naturales.suma@1-bronce')).toHaveTextContent('Suma · Bronce');
  });
});

describe('"Comprobar" en vertical', () => {
  it('va en una barra pegada al borde de abajo, junto con el mensaje', () => {
    render(<ProblemaNucleo sesionId={1} turno={{ sesion_completada: false, problema_sesion_id: 2, problema: sumaBanco, intentos_restantes: 3 }}
      icono="🍎" onTerminado={vi.fn()} />);
    const barra = screen.getByTestId('barra-comprobar');
    expect(barra.className).toMatch(/\bsticky\b/);
    expect(barra.className).toMatch(/bottom-0/);
    expect(barra.className).toMatch(/md:landscape:static/);
    expect(within(barra).getByTestId('comprobar')).toBeInTheDocument();
  });
});
