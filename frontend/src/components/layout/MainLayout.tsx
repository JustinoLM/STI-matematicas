/**
 * Layout principal de la aplicación.
 *
 * Aplica el tema del estudiante estableciendo:
 *   - data-narrative="tema-xxx" en <html> → el CSS sobreescribe --primary via selector
 *   - --primary / --ring en <html> → color personalizado del inventario
 *   - Color mágico (gradiente): cicla --primary por todos los tonos del arcoíris
 *   - backgroundImage / backgroundColor en el div raíz → fondo activo (no en body)
 */

import { useState, useEffect } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useThemeStore } from '@/store/themeStore';
import { useAudioPlayer } from '@/hooks/useAudioPlayer';
import { playSound } from '@/utils';

interface MainLayoutProps {
  children: React.ReactNode;
  userName: string;
  userRole: 'estudiante' | 'profesor';
  onLogout: () => void;
  hideSidebar?: boolean;
}

/** Convierte un color hex (#RRGGBB) a la cadena "H S% L%" que usa Tailwind/shadcn */
function hexToHslString(hex: string): string | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return null;

  const r = parseInt(result[1], 16) / 255;
  const g = parseInt(result[2], 16) / 255;
  const b = parseInt(result[3], 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0, s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }

  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

export function MainLayout({ children, userName, userRole, onLogout, hideSidebar = false }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Reproductor de música de fondo — solo estudiantes.
  // Si el rol es profesor, el hook hace fade out y pausa inmediatamente.
  useAudioPlayer(userRole === 'estudiante');

  // Sonido de click global en botones (solo estudiantes)
  useEffect(() => {
    if (userRole !== 'estudiante') return;

    const handleMouseDown = (e: MouseEvent) => {
      const { efectosSonidoActivados, volumen } = useThemeStore.getState();
      if (!efectosSonidoActivados) return;
      const target = e.target as HTMLElement;
      if (target.closest('button:not([disabled]), [role="button"]:not([disabled]), .cursor-pointer, a[href]')) {
        playSound('/assets/sound_effects/click.mp3', (volumen / 100) * 0.45);
      }
    };

    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [userRole]);

  const temaActivoId      = useThemeStore(s => s.temaActivoId);
  const colorActivoId     = useThemeStore(s => s.colorActivoId);
  const preferenciasTema  = useThemeStore(s => s.preferenciasPorTema[s.temaActivoId]);
  const getFondoActivo    = useThemeStore(s => s.getFondoActivo);
  const getColorActivo    = useThemeStore(s => s.getColorActivo);

  useEffect(() => {
    if (userRole !== 'estudiante') return;

    const html = document.documentElement;
    const color = getColorActivo();

    // ---- 1. Tema narrativo → data-narrative en <html> ----
    html.setAttribute('data-narrative', temaActivoId);

    // ---- 2. Color personalizado del inventario ----
    let magicInterval: ReturnType<typeof setInterval> | null = null;
    const colorHex = color?.config?.colorHex;

    if (colorHex && colorHex.startsWith('linear-gradient')) {
      // ✨ Color mágico: ciclar --primary por todos los tonos del arcoíris
      let hue = 0;
      magicInterval = setInterval(() => {
        hue = (hue + 1) % 360;
        html.style.setProperty('--primary', `${hue} 80% 55%`);
        html.style.setProperty('--ring', `${hue} 80% 55%`);
        html.style.setProperty('--primary-foreground', '0 0% 98%');
      }, 40); // ~25fps — ciclo completo en ~14s
    } else if (colorHex) {
      // Color sólido normal
      const hsl = hexToHslString(colorHex);
      if (hsl) {
        html.style.setProperty('--primary', hsl);
        html.style.setProperty('--ring', hsl);
        html.style.setProperty('--primary-foreground', '0 0% 98%');
      }
    } else {
      // Sin color → el selector CSS del tema toma control de --primary
      html.style.removeProperty('--primary');
      html.style.removeProperty('--ring');
      html.style.removeProperty('--primary-foreground');
    }

    // ---- 3. Tamaño de texto base para estudiantes ----
    html.style.fontSize = '18px';

    // ---- 4. Frosted-glass: data-has-bg cuando hay imagen de fondo activa ----
    const fondoActual = getFondoActivo();
    const urlImagen = fondoActual?.config?.urlImagen;
    const fondoColorHex = fondoActual?.config?.colorHex;
    if (urlImagen || (fondoColorHex && !fondoColorHex.startsWith('linear'))) {
      html.setAttribute('data-has-bg', 'true');
    } else {
      html.removeAttribute('data-has-bg');
    }

    return () => {
      if (magicInterval) clearInterval(magicInterval);
      html.removeAttribute('data-narrative');
      html.removeAttribute('data-has-bg');
      html.style.removeProperty('--primary');
      html.style.removeProperty('--ring');
      html.style.removeProperty('--primary-foreground');
      html.style.fontSize = '';
    };
  // preferenciasTema cubre cambios de fondo; colorActivoId cubre cambios de color
  }, [temaActivoId, colorActivoId, preferenciasTema, userRole, getColorActivo, getFondoActivo]);

  // ---- Fondo activo → inline style en el div raíz ----
  // Se lee directamente en el render para que el fondo se aplique en el
  // div que contiene toda la UI, evitando que bg-background lo tape.
  const fondoActivo = userRole === 'estudiante' ? getFondoActivo() : null;
  const fondoBgStyle = (() => {
    if (!fondoActivo) return {} as React.CSSProperties;
    const { urlImagen, colorHex } = fondoActivo.config ?? {};
    if (urlImagen) {
      // Overlay blanco semitransparente dentro del mismo backgroundImage
      // para reducir la intensidad sin necesitar un div extra con z-index.
      return {
        backgroundImage: `linear-gradient(rgba(255,255,255,0.835), rgba(255,255,255,0.835)), url(${urlImagen})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundAttachment: 'fixed',
      } as React.CSSProperties;
    }
    if (colorHex && !colorHex.startsWith('linear')) {
      return { backgroundColor: colorHex } as React.CSSProperties;
    }
    return {} as React.CSSProperties;
  })();
  const hasCustomBg = Object.keys(fondoBgStyle).length > 0;

  return (
    <div className={`min-h-screen ${hasCustomBg ? '' : 'bg-background'}`} style={fondoBgStyle}>
      <Header
        userName={userName}
        userRole={userRole}
        onLogout={onLogout}
        onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <div className="flex">
        {!hideSidebar && (
          <Sidebar
            userRole={userRole}
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
        )}

        <main className="flex-1 p-6">
          <div className="container mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
