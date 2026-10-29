const mq = (q: string) => (typeof window !== "undefined" ? window.matchMedia(q).matches : false);

/** Static capability flags, read once at boot. */
export const reducedMotion = mq("(prefers-reduced-motion: reduce)");
export const isTouch = mq("(hover: none) and (pointer: coarse)");
export const isMobile = typeof window !== "undefined" ? window.innerWidth < 768 : false;
/** Heavy WebGL extras (bloom, transmission) are skipped on small or reduced-motion devices. */
export const lowPower = reducedMotion || isMobile;

export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
/** Maps v from [a,b] to [0,1], clamped. */
export const range = (v: number, a: number, b: number) => clamp01((v - a) / (b - a));
export const smooth = (t: number) => t * t * (3 - 2 * t);
/** Exponential damping that is frame-rate independent. */
export const damp = (current: number, target: number, lambda: number, dt: number) =>
  lerp(current, target, 1 - Math.exp(-lambda * dt));
