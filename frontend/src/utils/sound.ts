/**
 * Utilidad de efectos de sonido — reproduce audio puntual sin interferir
 * con la música de fondo (cada llamada crea su propio elemento <audio>).
 *
 * Uso:
 *   playSound('/assets/sound_effects/correcto.mp3', 0.7);
 */

/**
 * Reproduce un archivo de audio de forma independiente.
 * @param url     Ruta al archivo (relativa a /public)
 * @param volume  Volumen 0–1 (default 0.6)
 */
export function playSound(url: string, volume = 0.6): void {
  try {
    const audio = new Audio(url);
    audio.volume = Math.max(0, Math.min(1, volume));
    audio.play().catch(() => {
      // Silencioso: autoplay bloqueado o archivo no encontrado
    });
  } catch {
    // Silencioso: entornos que no soportan Audio
  }
}
