import { useRef } from "react";
import { gsap, useGSAP } from "./gsap";
import { isMobile, reducedMotion } from "./motion";
import { presenceTrigger, stationVars, type Station } from "./scroll";

interface Options {
  /** pin the section and scrub through `length` percent of viewport height */
  pin?: boolean;
  length?: number;
  /** called with choreography progress 0..1 */
  onUpdate?: (p: number) => void;
  /** add scrubbed tweens to the station timeline */
  build?: (tl: gsap.core.Timeline) => void;
  /** skip pinning on phones even when `pin` is set */
  noPinOnMobile?: boolean;
}

/**
 * Wires a page section to its station in the scene: one ScrollTrigger for
 * choreography progress (optionally pinned and scrubbed) and one for the
 * presence envelope the WebGL station fades with.
 */
export function useStationSection(id: Station, opts: Options = {}) {
  const ref = useRef<HTMLElement>(null);
  const pinned = Boolean(opts.pin) && !reducedMotion && !(opts.noPinOnMobile && isMobile);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return;
      const tl = gsap.timeline({
        scrollTrigger: stationVars(id, {
          trigger: el,
          start: pinned ? "top top" : "top 70%",
          end: pinned ? `+=${opts.length ?? 200}%` : "bottom 30%",
          pin: pinned,
          pinSpacing: true,
          anticipatePin: pinned ? 1 : 0,
          scrub: pinned ? 0.5 : false,
          invalidateOnRefresh: true,
          onUpdate: (self) => opts.onUpdate?.(reducedMotion ? 1 : self.progress),
        }),
      });
      opts.build?.(tl);
      if (!tl.getChildren().length) tl.to({}, { duration: 1 });
      if (reducedMotion) opts.onUpdate?.(1);
      presenceTrigger(id, el, () => (pinned ? ((opts.length ?? 200) / 100) * window.innerHeight : 0));
    },
    { scope: ref },
  );

  return { ref, pinned };
}
