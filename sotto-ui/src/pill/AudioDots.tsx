import { useEffect, useRef } from "react";

interface WaveformProps {
  level: number; // 0–1 normalized
}

const BAR_COUNT = 7;
const MIN_HEIGHT = 3;
const MAX_HEIGHT = 22;

// Center bars react most, edges dampened — natural speech envelope
const SENSITIVITY = [0.45, 0.65, 0.85, 1.0, 0.85, 0.65, 0.45];

// Each bar has a slight phase offset for organic wave motion
const PHASE_OFFSET = [0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9];

// Interpolation: rise fast, fall slow (feels responsive but smooth)
const LERP_UP = 0.28;
const LERP_DOWN = 0.08;

export function AudioDots({ level }: WaveformProps) {
  const barsRef = useRef<(HTMLDivElement | null)[]>([]);
  const heights = useRef<number[]>(new Array(BAR_COUNT).fill(MIN_HEIGHT));
  const rafRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    const animate = (timestamp: number) => {
      if (!timeRef.current) timeRef.current = timestamp;
      const elapsed = (timestamp - timeRef.current) / 1000;

      barsRef.current.forEach((bar, i) => {
        if (!bar) return;

        // Add subtle organic variation per bar using sine wave with phase offset
        const variation = 0.15 * Math.sin(elapsed * 3.5 + PHASE_OFFSET[i] * Math.PI * 2);
        const adjustedLevel = Math.max(0, Math.min(1, level * SENSITIVITY[i] + variation * level));
        const targetHeight = MIN_HEIGHT + adjustedLevel * (MAX_HEIGHT - MIN_HEIGHT);

        // Smooth interpolation
        const current = heights.current[i];
        const lerp = targetHeight > current ? LERP_UP : LERP_DOWN;
        const newHeight = current + (targetHeight - current) * lerp;
        heights.current[i] = newHeight;

        bar.style.height = `${newHeight}px`;
        bar.style.opacity = `${0.35 + adjustedLevel * 0.6}`;
      });

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [level]);

  return (
    <div className="waveform">
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => { barsRef.current[i] = el; }}
          className="bar"
          style={{ height: MIN_HEIGHT, opacity: 0.35 }}
        />
      ))}
    </div>
  );
}
