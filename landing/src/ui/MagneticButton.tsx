import { useRef, type AnchorHTMLAttributes, type ReactNode } from "react";
import { gsap } from "../lib/gsap";
import { isTouch, reducedMotion } from "../lib/motion";

type Props = AnchorHTMLAttributes<HTMLAnchorElement> & { children: ReactNode };

/** Anchor that leans toward the pointer and springs back. */
export function MagneticButton({ children, className = "btn", ...rest }: Props) {
  const ref = useRef<HTMLAnchorElement>(null);
  const still = isTouch || reducedMotion;

  const onMove = (e: React.PointerEvent) => {
    if (still || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2);
    const dy = e.clientY - (r.top + r.height / 2);
    gsap.to(ref.current, { x: dx * 0.28, y: dy * 0.32, duration: 0.5, ease: "power3.out" });
  };
  const onLeave = () => {
    if (still || !ref.current) return;
    gsap.to(ref.current, { x: 0, y: 0, duration: 0.9, ease: "elastic.out(1, 0.45)" });
  };

  return (
    <a ref={ref} className={className} onPointerMove={onMove} onPointerLeave={onLeave} data-cursor="hover" {...rest}>
      {children}
    </a>
  );
}
