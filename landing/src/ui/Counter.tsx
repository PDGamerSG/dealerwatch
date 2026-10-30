import { useRef } from "react";
import { gsap, useGSAP } from "../lib/gsap";
import { reducedMotion } from "../lib/motion";

interface Props {
  to: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  locale?: string;
  className?: string;
}

/** Counts up once when scrolled into view. */
export function Counter({ to, decimals = 0, prefix = "", suffix = "", locale = "en-IN", className }: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const format = (n: number) => prefix + n.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;

  useGSAP(() => {
    if (!ref.current) return;
    if (reducedMotion) {
      ref.current.textContent = format(to);
      return;
    }
    const obj = { v: 0 };
    gsap.to(obj, {
      v: to,
      duration: 1.8,
      ease: "power3.out",
      scrollTrigger: { trigger: ref.current, start: "top 85%", once: true, refreshPriority: -1 },
      onUpdate: () => {
        if (ref.current) ref.current.textContent = format(obj.v);
      },
    });
  }, [to]);

  return (
    <span ref={ref} className={className}>
      {format(0)}
    </span>
  );
}
