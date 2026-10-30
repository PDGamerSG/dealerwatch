import { useEffect, useRef } from "react";
import { gsap, ScrollTrigger } from "../lib/gsap";
import { useScrollUI, type Station } from "../lib/scroll";

const TICKS: { id: Station; label: string }[] = [
  { id: "hero", label: "Tape" },
  { id: "gap", label: "Gap" },
  { id: "sandwich", label: "Detect" },
  { id: "call", label: "Gather" },
  { id: "link", label: "Link" },
  { id: "chain", label: "Verify" },
  { id: "ledger", label: "Record" },
  { id: "decide", label: "Decide" },
  { id: "proof", label: "Proof" },
  { id: "close", label: "Run" },
];

/** The ledger's red margin line, filling with page progress. */
export function Rule() {
  const fill = useRef<HTMLDivElement>(null);
  const ticks = useRef<HTMLDivElement>(null);
  const active = useScrollUI((s) => s.active);

  useEffect(() => {
    if (!fill.current) return;
    const st = ScrollTrigger.create({
      start: 0,
      end: "max",
      onUpdate: (self) => gsap.set(fill.current, { scaleY: self.progress }),
    });
    const place = () => {
      const max = ScrollTrigger.maxScroll(window);
      if (!ticks.current || !max) return;
      const vh = window.innerHeight;
      for (const el of Array.from(ticks.current.children) as HTMLElement[]) {
        const target = document.getElementById(el.dataset.id ?? "");
        if (!target) continue;
        const top = target.getBoundingClientRect().top + window.scrollY;
        el.style.top = `${(Math.min(top, max) / max) * vh}px`;
      }
    };
    place();
    ScrollTrigger.addEventListener("refresh", place);
    return () => {
      st.kill();
      ScrollTrigger.removeEventListener("refresh", place);
    };
  }, []);

  return (
    <div className="rule" aria-hidden>
      <div ref={fill} className="rule__fill" />
      <div ref={ticks} className="rule__ticks">
        {TICKS.map((t) => (
          <div key={t.id} data-id={t.id} className={`rule__tick${active === t.id ? " is-active" : ""}`}>
            <span>{t.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
