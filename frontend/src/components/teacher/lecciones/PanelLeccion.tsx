/**
 * Panel para configurar una lección del salón: signo, dibujos, pistas, prioridad y
 * prerrequisitos de este año. Todo explicado en lenguaje de docente.
 *
 * Guardar envía la configuración (si la lección está habilitada y cambió) y los prerrequisitos
 * (si cambiaron). Los errores del servidor (máximo de prioritarias, ciclo) se muestran aquí.
 */

import { useMemo, useState } from 'react';
import { Loader2, RotateCcw, Star, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ConfigLeccion, LeccionSalon, ModoLeccion, PistasLeccion } from '@/types/nucleo';
import { MAX_PRIORITARIAS, configDe, nombreLeccion, prioritarias, puedeSerPrioritaria } from '@/lib/leccionesSalon';

interface Props {
  leccion: LeccionSalon;
  catalogo: LeccionSalon[];
  soloLectura: boolean;
  onGuardar: (cambios: { config: ConfigLeccion | null; prerrequisitos: string[] | null }) => Promise<void>;
  onRestaurar: () => Promise<void>;
  onCerrar: () => void;
}

const OPCIONES_SIGNO: { valor: ModoLeccion; texto: string }[] = [
  { valor: 'siempre', texto: 'Siempre visible' },
  { valor: 'nunca', texto: 'Oculto: el estudiante elige el signo' },
  { valor: 'azar', texto: 'A veces visible, a veces oculto' },
];

const OPCIONES_ICONOS: { valor: ModoLeccion; texto: string }[] = [
  { valor: 'siempre', texto: 'Siempre' },
  { valor: 'nunca', texto: 'Nunca' },
  { valor: 'azar', texto: 'A veces sí, a veces no' },
];

const PISTAS: { nivel: keyof PistasLeccion; texto: string }[] = [
  { nivel: '1', texto: 'Pista 1: una idea para empezar' },
  { nivel: '2', texto: 'Pista 2: un paso del procedimiento' },
  { nivel: '3', texto: 'Pista 3: casi la respuesta' },
];

const iguales = (a: string[], b: string[]) => a.length === b.length && a.every((x, i) => x === b[i]);

function Seccion({ titulo, ayuda, children }: { titulo: string; ayuda: string; children: React.ReactNode }) {
  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-semibold">{titulo}</legend>
      <p className="text-xs text-muted-foreground">{ayuda}</p>
      {children}
    </fieldset>
  );
}

function GrupoModo({ nombre, valor, opciones, onChange, deshabilitado }: {
  nombre: string; valor: ModoLeccion; opciones: { valor: ModoLeccion; texto: string }[];
  onChange: (m: ModoLeccion) => void; deshabilitado: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
      {opciones.map((o) => (
        <label key={o.valor}
          className={`flex min-h-[44px] cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${
            valor === o.valor ? 'border-primary bg-primary/5' : ''} ${deshabilitado ? 'opacity-60' : ''}`}>
          <input type="radio" name={nombre} value={o.valor} checked={valor === o.valor}
            disabled={deshabilitado} onChange={() => onChange(o.valor)} />
          {o.texto}
        </label>
      ))}
    </div>
  );
}

export function PanelLeccion({ leccion, catalogo, soloLectura, onGuardar, onRestaurar, onCerrar }: Props) {
  const [config, setConfig] = useState<ConfigLeccion>(() => configDe(leccion));
  const [pres, setPres] = useState<string[]>(leccion.prerrequisitos);
  const [agregar, setAgregar] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const porId = useMemo(() => new Map(catalogo.map((l) => [l.id, l])), [catalogo]);
  const configurable = leccion.habilitada && !soloLectura;
  const otrasPrioritarias = prioritarias(catalogo).filter((l) => l.id !== leccion.id);
  const limitePrioritarias = !puedeSerPrioritaria(catalogo, leccion.id) && !config.prioritaria;

  // Candidatas a prerrequisito: incluidas, distintas de esta y no elegidas, agrupadas por grado
  const candidatas = useMemo(() => {
    const porGrado = new Map<number, LeccionSalon[]>();
    for (const l of [...catalogo].sort((a, b) => a.orden_programa - b.orden_programa)) {
      if (!l.incluida || l.id === leccion.id || pres.includes(l.id)) continue;
      porGrado.set(l.grado, [...(porGrado.get(l.grado) ?? []), l]);
    }
    return [...porGrado.entries()];
  }, [catalogo, leccion.id, pres]);

  const configCambio = JSON.stringify(config) !== JSON.stringify(configDe(leccion));
  const presCambio = !iguales(pres, leccion.prerrequisitos);

  const guardar = async () => {
    setError(null);
    setGuardando(true);
    try {
      await onGuardar({
        config: configurable && configCambio ? config : null,
        prerrequisitos: presCambio ? pres : null,
      });
      onCerrar();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo guardar.');
    } finally {
      setGuardando(false);
    }
  };

  const restaurar = async () => {
    setError(null);
    try {
      await onRestaurar();
      setPres(leccion.prerrequisitos_programa);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo restaurar.');
    }
  };

  return (
    <div className="space-y-6" data-testid="panel-leccion">
      <div>
        <p className="text-xs text-muted-foreground">
          {leccion.grado}.º grado · Unidad {leccion.unidad_numero} · Lección {leccion.leccion_numero}
        </p>
        <h2 className="text-xl font-semibold">{leccion.leccion_titulo}</h2>
        {!leccion.habilitada && (
          <p className="mt-2 rounded-md bg-muted px-3 py-2 text-sm">
            Esta lección no está habilitada. Habilítala en el catálogo para configurar cómo se practica;
            sus prerrequisitos sí puedes revisarlos.
          </p>
        )}
      </div>

      <Seccion titulo="Signo de la operación"
        ayuda="Con el signo oculto, el estudiante debe reconocer si el problema es de sumar o de restar y elegir el signo.">
        <GrupoModo nombre="signo" valor={config.signo} opciones={OPCIONES_SIGNO} deshabilitado={!configurable}
          onChange={(signo) => setConfig({ ...config, signo })} />
      </Seccion>

      <Seccion titulo="Dibujos para contar"
        ayuda="Los dibujos (manzanas, estrellas…) ayudan a contar. Sin ellos, el estudiante calcula solo con los números.">
        <GrupoModo nombre="iconos" valor={config.iconos} opciones={OPCIONES_ICONOS} deshabilitado={!configurable}
          onChange={(iconos) => setConfig({ ...config, iconos })} />
      </Seccion>

      <Seccion titulo="Pistas que puede pedir"
        ayuda="Cada pista ayuda un poco más que la anterior. Un acierto con la pista 3 no cuenta para dominar la lección.">
        <div className="flex flex-col gap-2">
          {PISTAS.map((p) => (
            <label key={p.nivel} className="flex min-h-[44px] items-center gap-2 text-sm">
              <input type="checkbox" checked={config.pistas[p.nivel]} disabled={!configurable}
                onChange={(e) => setConfig({ ...config, pistas: { ...config.pistas, [p.nivel]: e.target.checked } })} />
              {p.texto}
            </label>
          ))}
        </div>
      </Seccion>

      <Seccion titulo="Prioridad"
        ayuda={`Una lección prioritaria ocupa la mitad de cada práctica hasta que el estudiante la domina. Úsala para lo que estás enseñando ahora. Máximo ${MAX_PRIORITARIAS} a la vez.`}>
        <label className={`flex min-h-[44px] items-center gap-2 text-sm ${limitePrioritarias ? 'opacity-60' : ''}`}>
          <input type="checkbox" checked={config.prioritaria} disabled={!configurable || limitePrioritarias}
            onChange={(e) => setConfig({ ...config, prioritaria: e.target.checked })} data-testid="check-prioritaria" />
          <Star className="h-4 w-4 text-amber-500" /> Prioritaria
        </label>
        {configurable && limitePrioritarias && (
          <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800" role="status">
            Ya tienes {MAX_PRIORITARIAS} lecciones prioritarias ({otrasPrioritarias.map((l) => l.leccion_titulo).join(', ')}).
            Quita la prioridad a una para elegir esta.
          </p>
        )}
      </Seccion>

      <Seccion titulo="Prerrequisitos en este salón"
        ayuda="Lo que el estudiante debe saber antes. Si falla en esta lección, el sistema le mezcla problemas de repaso de sus prerrequisitos. Los cambios valen solo para este salón y este año.">
        <div className="flex flex-wrap gap-2">
          {pres.length === 0 && <span className="text-sm text-muted-foreground">Sin prerrequisitos.</span>}
          {pres.map((id) => {
            const l = porId.get(id);
            return (
              <span key={id} className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-3 py-1 text-sm">
                {l ? nombreLeccion(l) : id}
                {!soloLectura && (
                  <button type="button" aria-label={`Quitar ${l?.leccion_titulo ?? id}`}
                    className="ml-1 rounded-full p-1 hover:bg-muted" onClick={() => setPres(pres.filter((x) => x !== id))}>
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            );
          })}
        </div>
        {!soloLectura && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <select aria-label="Agregar prerrequisito" value={agregar} onChange={(e) => setAgregar(e.target.value)}
              className="min-h-[44px] w-full min-w-0 flex-1 rounded-md border bg-background px-2 text-sm">
              <option value="">Elegir una lección…</option>
              {candidatas.map(([grado, ls]) => (
                <optgroup key={grado} label={`${grado}.º grado`}>
                  {ls.map((l) => <option key={l.id} value={l.id}>{nombreLeccion(l)}</option>)}
                </optgroup>
              ))}
            </select>
            <Button type="button" variant="outline" disabled={!agregar}
              onClick={() => { setPres([...pres, agregar]); setAgregar(''); }}>
              Agregar
            </Button>
          </div>
        )}
        {leccion.prerrequisitos_editados && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Cambiados en este salón. En el programa:{' '}
              {leccion.prerrequisitos_programa.map((id) => porId.get(id)?.leccion_titulo ?? id).join(', ') || 'ninguno'}.
            </span>
            {!soloLectura && (
              <Button type="button" variant="ghost" size="sm" onClick={restaurar}>
                <RotateCcw className="mr-1 h-3 w-3" /> Volver a los del programa
              </Button>
            )}
          </div>
        )}
      </Seccion>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCerrar}>{soloLectura ? 'Cerrar' : 'Cancelar'}</Button>
        {!soloLectura && (
          <Button type="button" onClick={guardar} disabled={guardando || (!configCambio && !presCambio)}>
            {guardando && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Guardar
          </Button>
        )}
      </div>
    </div>
  );
}
