import { useStationSection } from "../lib/use-station-section";
import { Counter } from "../ui/Counter";
import { SplitHeading } from "../ui/SplitHeading";

export function Proof() {
  const { ref } = useStationSection("proof");
  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="proof" className="station" aria-labelledby="proof-title">
      <div className="station__head">
        <b>Proof</b>
        <span>labelled synthetic universe</span>
      </div>
      <SplitHeading className="display display--section" id="proof-title">
        Nineteen of nineteen, and the decoys stay out.
      </SplitHeading>
      <div className="proof__grid">
        <div className="stat">
          <div className="stat__value">
            <Counter to={19} />
            <sub>of 19</sub>
          </div>
          <div className="stat__label">Labelled scenarios with the expected recommendation: 6 escalate, 10 review, 3 dismiss.</div>
        </div>
        <div className="stat">
          <div className="stat__value">
            <Counter to={1} decimals={3} />
          </div>
          <div className="stat__label">Escalation precision.</div>
          <div className="stat__vs">
            trade-score baseline <b>0.500</b>
          </div>
        </div>
        <div className="stat">
          <div className="stat__value">
            <Counter to={1} decimals={3} />
          </div>
          <div className="stat__label">Escalation F1. Six unlinked repeat-pattern decoys become review, not false escalations.</div>
          <div className="stat__vs">
            trade-score baseline <b>0.667</b>
          </div>
        </div>
        <div className="stat">
          <div className="stat__value">
            <Counter to={412} />
            <sub>ms</sub>
          </div>
          <div className="stat__label">Median to detect across 100,000 trades and 1,000 orders.</div>
          <div className="stat__vs">
            previous scan <b>6,271 ms</b>, identical candidates
          </div>
        </div>
      </div>
      <p className="proof__note small">
        Measured on the seed 7 synthetic universe with planted truth labels, including one injection attempt inside a transcript. These are controlled
        results, not production accuracy estimates. Real deployment needs the fund house's blotter, recording metadata and KYC feeds.
      </p>
    </section>
  );
}
