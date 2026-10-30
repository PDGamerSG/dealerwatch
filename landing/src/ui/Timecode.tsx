import { useEffect, useRef } from "react";
import { ScrollTrigger } from "../lib/gsap";

const OPEN = 9 * 3600 + 15 * 60;
const CLOSE = 15 * 3600 + 30 * 60;
const pad = (n: number) => String(n).padStart(2, "0");

/** A trading-day clock that runs from open to close as the page scrolls. */
export function Timecode() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const st = ScrollTrigger.create({
      start: 0,
      end: "max",
      onUpdate: (self) => {
        if (!ref.current) return;
        const s = Math.round(OPEN + (CLOSE - OPEN) * self.progress);
        ref.current.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)} ist`;
      },
    });
    return () => st.kill();
  }, []);
  return (
    <div className="timecode mono" aria-hidden>
      <div ref={ref}>09:15:00 ist</div>
    </div>
  );
}
