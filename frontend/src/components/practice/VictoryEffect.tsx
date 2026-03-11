/**
 * VictoryEffect — overlay de canvas animado al responder correctamente (Sección 4.4.6)
 *
 * Animaciones soportadas:
 *   stars-fall      → Lluvia de Estrellas
 *   confetti-burst  → Explosión de Confeti
 *   fireworks       → Fuegos Artificiales
 *   lightning-strike → Poder del Rayo
 *   aurora-borealis → Aurora Boreal
 */

import { useEffect, useRef } from 'react';
import { playSound } from '@/utils';

export type AnimationType =
  | 'stars-fall'
  | 'confetti-burst'
  | 'fireworks'
  | 'lightning-strike'
  | 'aurora-borealis';

interface VictoryEffectProps {
  animacion: AnimationType;
  duracionMs: number;
  onDone: () => void;
  /** URL del efecto de sonido a reproducir (opcional) */
  sonido?: string;
  /** Volumen 0-100 (de themeStore) */
  audioVolumen?: number;
}

// ─── Partícula: Estrella ──────────────────────────────────────────────────────
interface StarP {
  x: number; y: number; size: number; speed: number;
  opacity: number; phase: number; phaseSpeed: number;
}

// ─── Partícula: Confeti ───────────────────────────────────────────────────────
interface ConfettiP {
  x: number; y: number; vx: number; vy: number;
  rotation: number; rotSpeed: number;
  w: number; h: number; color: string; opacity: number;
}

// ─── Cohete / partícula de fuego artificial ───────────────────────────────────
interface FWParticle { x: number; y: number; vx: number; vy: number; opacity: number; size: number }
interface Rocket {
  x: number; y: number; vy: number; targetY: number;
  exploded: boolean; particles: FWParticle[];
  color: string; delay: number;
}

// ─── Segmento de rayo ─────────────────────────────────────────────────────────
interface BoltSegment { x: number; y: number }

// ─── Helpers ─────────────────────────────────────────────────────────────────

const CONFETTI_COLORS = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#c77dff', '#ff9f43', '#ff6b9d', '#00d4aa'];
const FW_COLORS      = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#c77dff', '#ff9f43', '#ffffff', '#00d4aa'];

/** Genera el trazado del rayo de manera estocástica (una sola vez). */
function buildBolt(startX: number, w: number, h: number): BoltSegment[] {
  const segs: BoltSegment[] = [{ x: startX, y: -10 }];
  let x = startX;
  let y = -10;
  while (y < h + 10) {
    x += (Math.random() - 0.5) * 90;
    x = Math.max(30, Math.min(w - 30, x));
    y += 35 + Math.random() * 50;
    segs.push({ x, y });
  }
  return segs;
}

/** Dibuja el rayo a partir de segmentos pre-generados. */
function drawBoltPath(ctx: CanvasRenderingContext2D, segs: BoltSegment[]) {
  ctx.beginPath();
  segs.forEach((s, i) => (i === 0 ? ctx.moveTo(s.x, s.y) : ctx.lineTo(s.x, s.y)));
  ctx.stroke();
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function VictoryEffect({ animacion, duracionMs, onDone, sonido, audioVolumen }: VictoryEffectProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Guardamos onDone en un ref para que nunca quede en el array de dependencias
  // del useEffect. De lo contrario, cualquier re-render de PracticePage crea una
  // nueva función inline `() => setEfectoVictoria(null)`, lo que provoca que el
  // efecto se limpie y reinicie (reproduciendo la animación dos veces).
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Reproducir sonido del efecto al inicio (si hay audio activo)
    if (sonido && audioVolumen && audioVolumen > 0) {
      playSound(sonido, (audioVolumen / 100) * 0.85);
    }

    const W = window.innerWidth;
    const H = window.innerHeight;
    canvas.width = W;
    canvas.height = H;

    let animId: number;
    const t0 = performance.now();

    // Fade-out helper — returns 0→1 alpha accounting for final fade
    const alpha = (now: number, fadeStartRatio = 0.7) => {
      const elapsed = now - t0;
      if (elapsed < duracionMs * fadeStartRatio) return 1;
      return Math.max(0, 1 - (elapsed - duracionMs * fadeStartRatio) / (duracionMs * (1 - fadeStartRatio)));
    };

    // ── STARS FALL ─────────────────────────────────────────────────────────────
    if (animacion === 'stars-fall') {
      const emojis = ['⭐', '✨', '🌟', '💫'];
      const stars: StarP[] = Array.from({ length: 55 }, () => ({
        x: Math.random() * W,
        y: -Math.random() * H * 0.6,
        size: 18 + Math.random() * 22,
        speed: 2.5 + Math.random() * 3.5,
        opacity: 0.75 + Math.random() * 0.25,
        phase: Math.random() * Math.PI * 2,
        phaseSpeed: 0.04 + Math.random() * 0.06,
      }));
      const emojiForStar = stars.map(() => emojis[Math.floor(Math.random() * emojis.length)]);

      const draw = (now: number) => {
        const a = alpha(now);
        ctx.clearRect(0, 0, W, H);
        stars.forEach((s, i) => {
          s.y += s.speed;
          s.phase += s.phaseSpeed;
          const xW = s.x + Math.sin(s.phase) * 22;
          ctx.globalAlpha = s.opacity * a;
          ctx.font = `${s.size}px serif`;
          ctx.fillText(emojiForStar[i], xW, s.y);
          if (s.y > H + 30) { s.y = -30; s.x = Math.random() * W; }
        });
        ctx.globalAlpha = 1;
        if (now - t0 < duracionMs) animId = requestAnimationFrame(draw);
      };
      animId = requestAnimationFrame(draw);

    // ── CONFETTI BURST ─────────────────────────────────────────────────────────
    } else if (animacion === 'confetti-burst') {
      const cx = W / 2, cy = H * 0.45;
      const particles: ConfettiP[] = Array.from({ length: 110 }, () => {
        const angle = Math.random() * Math.PI * 2;
        const speed = 6 + Math.random() * 12;
        return {
          x: cx, y: cy,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed - 4,
          rotation: Math.random() * Math.PI * 2,
          rotSpeed: (Math.random() - 0.5) * 0.35,
          w: 9 + Math.random() * 8,
          h: 5 + Math.random() * 5,
          color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
          opacity: 1,
        };
      });

      const draw = (now: number) => {
        const a = alpha(now, 0.55);
        ctx.clearRect(0, 0, W, H);
        particles.forEach(p => {
          p.x += p.vx; p.y += p.vy; p.vy += 0.35; p.vx *= 0.98;
          p.rotation += p.rotSpeed;
          ctx.save();
          ctx.globalAlpha = a;
          ctx.translate(p.x, p.y);
          ctx.rotate(p.rotation);
          ctx.fillStyle = p.color;
          ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
          ctx.restore();
        });
        if (now - t0 < duracionMs) animId = requestAnimationFrame(draw);
      };
      animId = requestAnimationFrame(draw);

    // ── FIREWORKS ──────────────────────────────────────────────────────────────
    } else if (animacion === 'fireworks') {
      const rockets: Rocket[] = Array.from({ length: 6 }, (_, i) => ({
        x: W * (0.15 + i * 0.14),
        y: H + 10,
        vy: -(9 + Math.random() * 5),
        targetY: H * (0.10 + Math.random() * 0.30),
        exploded: false,
        particles: [],
        color: FW_COLORS[i % FW_COLORS.length],
        delay: i * 280,
      }));

      const draw = (now: number) => {
        const elapsed = now - t0;
        // Don't fully clear — leave a dark trail
        ctx.fillStyle = 'rgba(0,0,0,0.18)';
        ctx.fillRect(0, 0, W, H);

        rockets.forEach(r => {
          if (elapsed < r.delay) return;
          if (!r.exploded) {
            r.y += r.vy; r.vy += 0.25;
            // Trail dot
            ctx.save();
            ctx.globalAlpha = 0.9;
            ctx.fillStyle = r.color;
            ctx.shadowColor = r.color;
            ctx.shadowBlur = 8;
            ctx.beginPath(); ctx.arc(r.x, r.y, 3, 0, Math.PI * 2); ctx.fill();
            ctx.restore();

            if (r.y <= r.targetY) {
              r.exploded = true;
              r.particles = Array.from({ length: 60 }, () => {
                const ang = Math.random() * Math.PI * 2;
                const spd = 1.5 + Math.random() * 7;
                return { x: r.x, y: r.y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd, opacity: 1, size: 1.5 + Math.random() * 2.5 };
              });
            }
          } else {
            r.particles.forEach(p => {
              p.x += p.vx; p.y += p.vy; p.vy += 0.07; p.vx *= 0.97;
              p.opacity = Math.max(0, p.opacity - 0.018);
              ctx.save();
              ctx.globalAlpha = p.opacity;
              ctx.fillStyle = r.color;
              ctx.shadowColor = r.color;
              ctx.shadowBlur = 6;
              ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2); ctx.fill();
              ctx.restore();
            });
          }
        });
        if (elapsed < duracionMs) animId = requestAnimationFrame(draw);
        else ctx.clearRect(0, 0, W, H); // wipe trail on finish
      };
      animId = requestAnimationFrame(draw);

    // ── LIGHTNING STRIKE ───────────────────────────────────────────────────────
    } else if (animacion === 'lightning-strike') {
      const boltX = W * (0.3 + Math.random() * 0.4);
      const bolt1 = buildBolt(boltX, W, H);
      const bolt2 = buildBolt(boltX + (Math.random() - 0.5) * 40, W, H);

      const draw = (now: number) => {
        const elapsed = now - t0;
        const t = elapsed / duracionMs;
        ctx.clearRect(0, 0, W, H);

        // Screen flash at beginning
        if (t < 0.15) {
          const flashA = (0.15 - t) / 0.15;
          ctx.fillStyle = `rgba(200, 230, 255, ${flashA * 0.35})`;
          ctx.fillRect(0, 0, W, H);
        }

        // Bolt visible from t=0 to t=0.75
        if (t < 0.75) {
          const boltA = t < 0.12 ? t / 0.12 : t > 0.55 ? 1 - (t - 0.55) / 0.2 : 1;

          // Glow pass
          ctx.save();
          ctx.shadowColor = '#aaeeff';
          ctx.shadowBlur = 24;
          ctx.strokeStyle = `rgba(150, 220, 255, ${boltA * 0.55})`;
          ctx.lineWidth = 10;
          ctx.lineJoin = 'round';
          drawBoltPath(ctx, bolt1);
          ctx.restore();

          // Core white bolt
          ctx.save();
          ctx.strokeStyle = `rgba(255, 255, 255, ${boltA})`;
          ctx.lineWidth = 2.5;
          ctx.lineJoin = 'round';
          drawBoltPath(ctx, bolt1);
          ctx.restore();

          // Secondary bolt (thinner)
          ctx.save();
          ctx.strokeStyle = `rgba(180, 240, 255, ${boltA * 0.6})`;
          ctx.lineWidth = 1.5;
          ctx.lineJoin = 'round';
          drawBoltPath(ctx, bolt2);
          ctx.restore();
        }

        if (elapsed < duracionMs) animId = requestAnimationFrame(draw);
      };
      animId = requestAnimationFrame(draw);

    // ── AURORA BOREALIS ────────────────────────────────────────────────────────
    } else if (animacion === 'aurora-borealis') {
      const bands = [
        { h1: 'rgba(0,255,120,',  h2: 'rgba(0,180,80,',   yBase: 0.08, amp: 0.07, freq: 0.0025, phase: 0 },
        { h1: 'rgba(0,160,255,',  h2: 'rgba(0,100,200,',  yBase: 0.17, amp: 0.065,freq: 0.003,  phase: 1.1 },
        { h1: 'rgba(140,0,255,',  h2: 'rgba(90,0,160,',   yBase: 0.25, amp: 0.055,freq: 0.004,  phase: 2.2 },
        { h1: 'rgba(0,220,180,',  h2: 'rgba(0,140,120,',  yBase: 0.11, amp: 0.05, freq: 0.005,  phase: 3.3 },
      ];

      const draw = (now: number) => {
        const elapsed = now - t0;
        const sec = elapsed / 1000;
        ctx.clearRect(0, 0, W, H);

        const fadeIn  = Math.min(1, elapsed / (duracionMs * 0.25));
        const fadeOut = elapsed > duracionMs * 0.72
          ? Math.max(0, 1 - (elapsed - duracionMs * 0.72) / (duracionMs * 0.28))
          : 1;
        const a = fadeIn * fadeOut;

        bands.forEach(b => {
          const gradH = H * 0.52;
          const grad = ctx.createLinearGradient(0, 0, 0, gradH);
          grad.addColorStop(0,   b.h1 + `${a * 0.04})`);
          grad.addColorStop(0.25, b.h1 + `${a * 0.55})`);
          grad.addColorStop(0.6,  b.h2 + `${a * 0.28})`);
          grad.addColorStop(1,    b.h1 + '0)');

          ctx.beginPath();
          ctx.moveTo(0, 0);
          for (let x = 0; x <= W; x += 4) {
            const y = H * b.yBase
              + Math.sin(x * b.freq + sec * 1.4 + b.phase) * H * b.amp
              + Math.sin(x * b.freq * 2.3 + sec * 0.7) * H * b.amp * 0.45;
            ctx.lineTo(x, y);
          }
          ctx.lineTo(W, 0);
          ctx.closePath();
          ctx.fillStyle = grad;
          ctx.fill();
        });

        // Subtle star field
        if (a > 0.3) {
          ctx.save();
          ctx.globalAlpha = a * 0.5;
          for (let i = 0; i < 60; i++) {
            const sx = (i * 137.5) % W;
            const sy = (i * 73.1) % (H * 0.35);
            const r = 1 + (i % 3) * 0.5;
            ctx.fillStyle = 'white';
            ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fill();
          }
          ctx.restore();
        }

        if (elapsed < duracionMs) animId = requestAnimationFrame(draw);
      };
      animId = requestAnimationFrame(draw);
    }

    const timer = setTimeout(() => {
      cancelAnimationFrame(animId);
      onDoneRef.current();
    }, duracionMs + 50);

    return () => {
      cancelAnimationFrame(animId);
      clearTimeout(timer);
    };
  // onDone excluido intencionalmente — se accede via ref para evitar re-ejecución
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animacion, duracionMs]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 9999,
      }}
    />
  );
}
