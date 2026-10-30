import { useRef } from "react";
import { useStationSection } from "../lib/use-station-section";
import { flag } from "../scene/useStation";
import { SplitHeading } from "../ui/SplitHeading";

const STEPS = [
  { at: 0.05, text: "Index every trade by scrip and time window" },
  { at: 0.32, text: "Find the large fund order" },
  { at: 0.52, text: "Same side shortly before it", alert: true },
  { at: 0.7, text: "Opposite side shortly after it", alert: true },
  { at: 0.86, text: "Score repeat count, matched profit and timing" },
];

export function SandwichSection() {
  const steps = useRef<(HTMLLIElement | null)[]>([]);
  const { ref } = useStationSection("sandwich", {
    pin: true,
    length: 280,
    onUpdate: (p) => STEPS.forEach((s, i) => flag(steps.current[i], "is-on", p >= s.at)),
  });
  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="sandwich" className="station pin" aria-labelledby="sandwich-title">
      <div className="pin__view">
        <div className="pin__copy">
          <div className="station__head">
            <b>Detect</b>
            <span>code only</span>
          </div>
          <SplitHeading className="display display--section" id="sandwich-title">
            Buy before the fund. Sell after.
          </SplitHeading>
          <p className="body">
            For every large fund order the detector looks for accounts that traded the same side shortly before and the opposite side shortly after. The
            score comes from repeat count, matched-quantity profit and timing. No model touches this step.
          </p>
          <ol className="steps">
            {STEPS.map((s, i) => (
              <li key={s.text} ref={(el) => {
                steps.current[i] = el;
              }} className={`step${s.alert ? " step--alert" : ""}`}>
                {s.text}
              </li>
            ))}
          </ol>
        </div>
        <div className="pin__meta">
          Indexed detector, Apple silicon
          <br />
          100,000 trades, 1,000 orders
          <br />
          <b>412 ms median</b> against 6,271 ms
        </div>
      </div>
    </section>
  );
}
