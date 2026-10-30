import { useRef, useState } from "react";
import { gsap } from "../lib/gsap";
import { human } from "../lib/scroll";
import { CASE } from "../lib/tape-data";
import { useStationSection } from "../lib/use-station-section";
import { SplitHeading } from "../ui/SplitHeading";

export function DecideSection() {
  const { ref } = useStationSection("decide", { pin: true, length: 170 });
  const ring = useRef<SVGCircleElement>(null);
  const tween = useRef<gsap.core.Tween | null>(null);
  const [sealed, setSealed] = useState(false);

  const setRing = () => {
    if (ring.current) ring.current.style.strokeDashoffset = String(100.5 * (1 - human.hold));
  };
  const start = () => {
    if (human.sealed) return;
    tween.current?.kill();
    tween.current = gsap.to(human, {
      hold: 1,
      duration: 1.3,
      ease: "power1.in",
      onUpdate: setRing,
      onComplete: () => {
        human.sealed = true;
        setSealed(true);
      },
    });
  };
  const stop = () => {
    if (human.sealed) return;
    tween.current?.kill();
    tween.current = gsap.to(human, { hold: 0, duration: 0.5, ease: "power2.out", onUpdate: setRing });
  };

  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="decide" className="station pin decide" aria-labelledby="decide-title">
      <div className="pin__view">
        <div className="decide__inner">
          <div className="station__head">
            <b>Decide</b>
            <span>human only</span>
          </div>
          <SplitHeading className="display display--statement decide__title" id="decide-title">
            Nothing escalates itself.
          </SplitHeading>
          <div className="decide__row">
            <div>
              <p className="body">
                The model extracts and explains. Rules recommend. A compliance officer starts the review, requests information, approves escalation or
                dismisses, and every choice is recorded with a revision and a retry key. The wording stays prima facie.
              </p>
              <div className="actions" aria-label="Reviewer actions">
                <span>Start review</span>
                <span>Request information</span>
                <span className="is-human">Approve escalation</span>
                <span>Dismiss</span>
              </div>
              <div style={{ marginTop: 28 }}>
                <button
                  type="button"
                  className={`hold${sealed ? " is-sealed" : ""}`}
                  onPointerDown={start}
                  onPointerUp={stop}
                  onPointerLeave={stop}
                  onPointerCancel={stop}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") start();
                  }}
                  onKeyUp={stop}
                  aria-pressed={sealed}
                >
                  <svg className="hold__ring" viewBox="0 0 36 36" aria-hidden>
                    <circle className="track" cx="18" cy="18" r="16" />
                    <circle ref={ring} className="fill" cx="18" cy="18" r="16" />
                  </svg>
                  <span>
                    {sealed ? "Escalation approved" : "Hold to approve escalation"}
                    <span className="hold__hint">{sealed ? `by ${CASE.reviewer}, ${CASE.decidedAt}` : "a person has to mean it"}</span>
                  </span>
                </button>
              </div>
            </div>
            <div className="decide__stamp">
              <div className={`stamp${sealed ? " is-on" : ""}`} aria-hidden>
                <strong>Escalated</strong>
                <span>prima facie, case 0007</span>
                <span>
                  reviewer {CASE.reviewer}, {CASE.decidedAt}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
