import { useEffect, useRef, useState } from "react";
import { useProgress } from "@react-three/drei";
import { gsap } from "../lib/gsap";
import { useScrollUI } from "../lib/scroll";
import { reducedMotion } from "../lib/motion";
import { rowText, tapeRows } from "../lib/tape-data";

const ROWS = tapeRows(14, 3).map(rowText);
const MIN_MS = 1600;
const IDLE_MS = 2600; // nothing started loading by then: assume there is nothing to load

/**
 * Prints tape rows while assets load, counts to 100, then a paper wipe
 * reveals the page. Scroll stays locked until it finishes.
 */
export function Loader() {
  const { progress, total } = useProgress();
  const setReady = useScrollUI((s) => s.setReady);
  const [shown, setShown] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const tape = useRef<HTMLDivElement>(null);
  const count = useRef<HTMLDivElement>(null);
  const latest = useRef({ progress, total });
  latest.current = { progress, total };

  useEffect(() => {
    const start = performance.now();
    let value = 0;
    let finished = false;
    let raf = 0;

    const paint = (v: number) => {
      if (count.current) count.current.textContent = String(Math.round(v)).padStart(3, "0");
      setShown(Math.min(ROWS.length, Math.floor((v / 100) * ROWS.length) + 1));
    };

    const finish = () => {
      finished = true;
      paint(100);
      if (reducedMotion || !tape.current || !root.current) {
        setReady();
        gsap.set(root.current, { display: "none" });
        return;
      }
      gsap
        .timeline({ defaults: { ease: "power4.inOut" } })
        .to(tape.current, { scaleX: 1, duration: 0.7 }, 0.2)
        .set(root.current, { background: "transparent" })
        .set([".loader__rows", ".loader__foot"], { autoAlpha: 0 })
        .add(() => setReady())
        .set(tape.current, { transformOrigin: "right" })
        .to(tape.current, { scaleX: 0, duration: 0.8 }, "+=0.05")
        .set(root.current, { display: "none" });
    };

    const tick = () => {
      if (finished) return;
      const elapsed = performance.now() - start;
      const { progress: real, total: items } = latest.current;
      const loaded = items > 0 ? real >= 100 : elapsed > IDLE_MS;
      const clock = Math.min(1, elapsed / MIN_MS) * 100;
      const ceiling = loaded ? 100 : Math.max(real, 88);
      const target = Math.min(ceiling, Math.max(real, clock));
      value += (target - value) * 0.12;
      if (loaded && elapsed >= MIN_MS && value > 99) {
        finish();
        return;
      }
      paint(value);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [setReady]);

  return (
    <div ref={root} className="loader" role="status" aria-live="polite" aria-label="Loading">
      <div className="loader__rows">
        {ROWS.slice(0, shown).map((r) => (
          <div key={r}>{r}</div>
        ))}
      </div>
      <div className="loader__foot">
        <div ref={count} className="loader__count">
          000
        </div>
        <div className="loader__label">Loading the seed 7 universe. Forty orders, 2,558 trades, twenty-five calls. All synthetic.</div>
      </div>
      <div ref={tape} className="loader__tape" />
    </div>
  );
}
