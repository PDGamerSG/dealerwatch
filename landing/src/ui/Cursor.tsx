import { useEffect, useRef, useState } from "react";
import { gsap } from "../lib/gsap";
import { isTouch } from "../lib/motion";
import { scroll } from "../lib/scroll";

/**
 * Ring cursor. Elements opt in with data-cursor="hover" (grow) or
 * data-cursor-label="text" (grow and show a label).
 */
export function Cursor() {
  const root = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<{ hover: boolean; label: string }>({ hover: false, label: "" });

  useEffect(() => {
    if (isTouch || !root.current) return;
    const el = root.current;
    const toX = gsap.quickTo(el, "x", { duration: 0.35, ease: "power3.out" });
    const toY = gsap.quickTo(el, "y", { duration: 0.35, ease: "power3.out" });
    const onMove = (e: PointerEvent) => {
      toX(e.clientX);
      toY(e.clientY);
      scroll.pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      scroll.pointer.y = -((e.clientY / window.innerHeight) * 2 - 1);
      const target = (e.target as HTMLElement | null)?.closest<HTMLElement>("[data-cursor],[data-cursor-label],a,button");
      if (!target) {
        setState((s) => (s.hover || s.label ? { hover: false, label: "" } : s));
        return;
      }
      const label = target.dataset.cursorLabel ?? "";
      setState((s) => (s.hover && s.label === label ? s : { hover: true, label }));
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  if (isTouch) return null;
  return (
    <div ref={root} className={`cursor${state.hover ? " is-hover" : ""}${state.label ? " is-label" : ""}`} aria-hidden>
      <div className="cursor__dot" />
      <div className="cursor__ring">
        <span className="cursor__label">{state.label}</span>
      </div>
    </div>
  );
}
