/**
 * Registro de eventos de un problema del núcleo (docs/DISENO_MODULAR.md, sección 3 → Registro
 * de eventos por intento): qué opción eligió, si cambió de opción antes de confirmar, cuánto
 * tardó y si usó la lectura en voz alta.
 *
 * - `ms` de cada evento: desde que se mostró el problema.
 * - `tiempo_ms` de cada intento: desde que empezó ese intento (el primero, al mostrarse el
 *   problema; los siguientes, al recibir la corrección del anterior).
 * - Los eventos y el uso de la voz se envían con el intento en que ocurrieron.
 */

import type { EventoNucleo } from '@/types/nucleo';
import type { EventoSinTiempo } from './respuestas';

export const MAX_EVENTOS_POR_INTENTO = 500; // límite del backend (RespuestaIn.eventos)

export interface DatosIntento {
  tiempo_ms: number;
  uso_voz: boolean;
  eventos: EventoNucleo[];
}

export class RegistroEventos {
  private inicioProblema: number;
  private inicioIntento: number;
  private eventos: EventoNucleo[] = [];
  private usoVoz = false;

  constructor(private reloj: () => number = () => performance.now()) {
    this.inicioProblema = reloj();
    this.inicioIntento = this.inicioProblema;
  }

  private ms(): number {
    return Math.max(0, Math.round(this.reloj() - this.inicioProblema));
  }

  registrar(evento: EventoSinTiempo): void {
    if (this.eventos.length >= MAX_EVENTOS_POR_INTENTO) return;
    this.eventos.push({ ...evento, ms: this.ms() });
  }

  registrarVarios(eventos: EventoSinTiempo[]): void {
    eventos.forEach(e => this.registrar(e));
  }

  /** El niño escuchó el enunciado en voz alta */
  usarVoz(): void {
    this.usoVoz = true;
    this.registrar({ tipo: 'voz' });
  }

  /** Datos del intento que se envía; deja listo el registro para el siguiente */
  cerrarIntento(): DatosIntento {
    const ahora = this.reloj();
    const datos: DatosIntento = {
      tiempo_ms: Math.max(0, Math.round(ahora - this.inicioIntento)),
      uso_voz: this.usoVoz,
      eventos: this.eventos,
    };
    this.eventos = [];
    this.usoVoz = false;
    return datos;
  }

  /** Si el envío falla (red, respuesta mal formada), el intento sigue abierto con sus eventos */
  reabrir(datos: DatosIntento): void {
    this.eventos = [...datos.eventos, ...this.eventos].slice(0, MAX_EVENTOS_POR_INTENTO);
    this.usoVoz = this.usoVoz || datos.uso_voz;
  }

  /** El siguiente intento empieza a contar ahora (al terminar de ver la corrección) */
  empezarIntento(): void {
    this.inicioIntento = this.reloj();
  }
}
