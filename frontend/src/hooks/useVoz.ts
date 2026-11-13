/**
 * Lectura en voz alta con la Web Speech API. `disponible` es false si el navegador no tiene
 * síntesis de voz o no tiene ninguna voz en español: en ese caso el botón no se muestra.
 * Las voces se cargan de forma asíncrona (evento `voiceschanged`).
 */

import { useCallback, useEffect, useState } from 'react';
import { elegirVozEspanol } from '@/utils/nucleo/lectura';

export function useVoz() {
  const [voz, setVoz] = useState<SpeechSynthesisVoice | null>(null);

  useEffect(() => {
    const sintesis = typeof window !== 'undefined' ? window.speechSynthesis : undefined;
    if (!sintesis) return;
    const cargar = () => setVoz(elegirVozEspanol(sintesis.getVoices()));
    cargar();
    sintesis.addEventListener?.('voiceschanged', cargar);
    return () => {
      sintesis.removeEventListener?.('voiceschanged', cargar);
      sintesis.cancel();
    };
  }, []);

  const hablar = useCallback((texto: string) => {
    const sintesis = window.speechSynthesis;
    if (!sintesis || !voz) return;
    sintesis.cancel();
    const frase = new SpeechSynthesisUtterance(texto);
    frase.voice = voz;
    frase.lang = voz.lang;
    frase.rate = 0.85; // más despacio para niños de 6 años
    sintesis.speak(frase);
  }, [voz]);

  const callar = useCallback(() => window.speechSynthesis?.cancel(), []);

  return { disponible: voz !== null, hablar, callar };
}
