import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
  duration?: number;
  reverse?: boolean;
}

/** Two copies of the content slide by; the track loops at -50%. */
export function Marquee({ children, className = "", duration = 60, reverse = false }: Props) {
  return (
    <div className={`marquee ${reverse ? "marquee--reverse " : ""}${className}`} style={{ ["--marquee-duration" as string]: `${duration}s` }}>
      <div className="marquee__track">
        <div className="marquee__group">{children}</div>
        <div className="marquee__group" aria-hidden>
          {children}
        </div>
      </div>
    </div>
  );
}
