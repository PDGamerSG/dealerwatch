import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { ReactLenis, useLenis, type LenisRef } from "lenis/react";
import { gsap, ScrollTrigger } from "../lib/gsap";
import { scroll, useScrollUI } from "../lib/scroll";
import { reducedMotion } from "../lib/motion";

const OPTIONS = { autoRaf: false, lerp: 0.09, wheelMultiplier: 0.95 } as const;

/**
 * Lenis drives native scroll; GSAP's ticker drives Lenis so ScrollTrigger
 * and the WebGL frame share one clock. The Lenis instance only exists after
 * ReactLenis's own effect, so everything that needs it goes through the ref
 * lazily or through the `useLenis` hook in <Bridge>.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const lenisRef = useRef<LenisRef>(null);

  useEffect(() => {
    if (reducedMotion) return;
    const update = (time: number) => lenisRef.current?.lenis?.raf(time * 1000);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => gsap.ticker.remove(update);
  }, []);

  if (reducedMotion) return <>{children}</>;
  return (
    <ReactLenis root options={OPTIONS} ref={lenisRef}>
      <Bridge />
      {children}
    </ReactLenis>
  );
}

/** Scroll velocity feeds the Archivo width axis through --wdth; the loader locks scroll. */
function Bridge() {
  const ready = useScrollUI((s) => s.ready);
  const setWidth = useMemo(() => gsap.quickTo(document.documentElement, "--wdth", { duration: 0.5, ease: "power2.out" }), []);

  const lenis = useLenis((l) => {
    ScrollTrigger.update();
    scroll.velocity = l.velocity;
    scroll.page = l.progress;
    // 100 at rest, up to about 118 at speed
    setWidth(100 + Math.min(18, Math.abs(l.velocity) * 0.45));
  });

  useEffect(() => {
    if (!lenis) return;
    if (ready) lenis.start();
    else lenis.stop();
  }, [lenis, ready]);

  return null;
}
