import { useRef, type ElementType, type ReactNode } from "react";
import { gsap, SplitText, useGSAP } from "../lib/gsap";
import { reducedMotion } from "../lib/motion";

interface Props {
  as?: ElementType;
  className?: string;
  children: ReactNode;
  /** play immediately instead of on scroll */
  immediate?: boolean;
  delay?: number;
  id?: string;
}

/** Line-masked heading reveal. Lines slide up from behind a clip. */
export function SplitHeading({ as: Tag = "h2", className = "", children, immediate = false, delay = 0, id }: Props) {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      if (!ref.current || reducedMotion) return;
      const split = SplitText.create(ref.current, { type: "lines", linesClass: "split-line", mask: "lines" });
      const tween = gsap.from(split.lines, {
        yPercent: 110,
        rotate: 1.5,
        duration: 1.1,
        ease: "power4.out",
        stagger: 0.08,
        delay,
        paused: !immediate,
        scrollTrigger: immediate ? undefined : { trigger: ref.current, start: "top 88%", once: true, refreshPriority: -1 },
      });
      if (immediate) tween.play();
      return () => split.revert();
    },
    { dependencies: [immediate] },
  );

  return (
    <Tag ref={ref} className={className} id={id}>
      {children}
    </Tag>
  );
}
