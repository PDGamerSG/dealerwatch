import { useRef } from "react";
import { isMobile } from "../lib/motion";
import { useStationSection } from "../lib/use-station-section";
import { flag } from "../scene/useStation";
import { SplitHeading } from "../ui/SplitHeading";

const LINKS = [
  ["Fund order", "A large order exists in the blotter for this scrip and time."],
  ["Pre-trade", "The account traded the same side inside the window before it."],
  ["Post-trade", "The account reversed inside the window after it."],
  ["Profit", "Matched quantity, realised against the order's price move."],
  ["Repeat pattern", "The same account has done this before, scored by count."],
  ["Link path", "A declared or shared-attribute path reaches the dealer."],
  ["Call in window", "The dealer spoke to someone on that path before the order."],
  ["Leak cue", "The transcript names the scrip, side, size or time, with citations."],
  ["Clause", "The conduct maps to a specific regulatory clause in the reference set."],
];

export function ChainSection() {
  const track = useRef<HTMLOListElement>(null);
  const cards = useRef<(HTMLLIElement | null)[]>([]);
  const mobile = isMobile;
  const { ref } = useStationSection("chain", {
    pin: true,
    length: 420,
    noPinOnMobile: true,
    onUpdate: (p) => LINKS.forEach((_, i) => flag(cards.current[i], "is-on", mobile || p * (LINKS.length - 1) >= i - 0.35)),
    build: (tl) => {
      if (mobile || !track.current) return;
      tl.to(track.current, {
        x: () => {
          const t = track.current!;
          const content = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--content")) || 100;
          return -(t.scrollWidth - window.innerWidth + content + 40);
        },
        ease: "none",
        duration: 1,
      });
    },
  });

  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="chain" className={`station pin chain${mobile ? " chain--mobile" : ""}`} aria-labelledby="chain-title">
      <div className="pin__view">
        <div className="chain__intro">
          <div className="station__head">
            <b>Verify</b>
            <span>nine checks</span>
          </div>
          <SplitHeading className="display display--section" id="chain-title">
            A case is a chain. Every link is checked.
          </SplitHeading>
        </div>
        <ol ref={track} className="chain__track">
          {LINKS.map(([title, text], i) => (
            <li key={title} ref={(el) => {
                cards.current[i] = el;
              }} className="link-card">
              <span className="link-card__n mono">
                {String(i + 1).padStart(2, "0")} of 09
              </span>
              <h3 className="link-card__title">{title}</h3>
              <p className="link-card__text">{text}</p>
              <span className="link-card__check">
                <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                  <path d="M2 7.5l3.2 3L12 3.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
                </svg>
                verified
              </span>
            </li>
          ))}
          <li className="link-card link-card--verdict">
            <span className="link-card__n mono">recommendation</span>
            <div className="verdict">
              <div className="is-escalate">
                <b>ESCALATE</b>
                <span>all nine links hold</span>
              </div>
              <div className="is-review">
                <b>REVIEW</b>
                <span>the pattern holds, part of the chain is missing</span>
              </div>
              <div className="is-dismiss">
                <b>DISMISS</b>
                <span>a sandwich with no path, call or cue</span>
              </div>
            </div>
            <p className="link-card__text">A recommendation is not a decision. Only a reviewer can change a case to escalated.</p>
          </li>
        </ol>
      </div>
    </section>
  );
}
