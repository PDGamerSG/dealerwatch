import { useRef } from "react";
import { useStationSection } from "../lib/use-station-section";
import { flag } from "../scene/useStation";
import { CASE } from "../lib/tape-data";
import { SplitHeading } from "../ui/SplitHeading";

const HOPS = [
  { at: 0.17, text: `Dealer ${CASE.dealer} on the desk` },
  { at: 0.4, text: `Declared relative: ${CASE.relative}` },
  { at: 0.6, text: `Shared mobile number in KYC` },
  { at: 0.8, text: `Trading account ${CASE.account}`, alert: true },
];

export function LinkSection() {
  const steps = useRef<(HTMLLIElement | null)[]>([]);
  const { ref } = useStationSection("link", {
    pin: true,
    length: 220,
    onUpdate: (p) => HOPS.forEach((h, i) => flag(steps.current[i], "is-on", p >= h.at)),
  });
  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="link" className="station pin" aria-labelledby="link-title">
      <div className="pin__view">
        <div className="pin__copy">
          <div className="station__head">
            <b>Link</b>
            <span>graph, exact matches</span>
          </div>
          <SplitHeading className="display display--section" id="link-title">
            From the desk to the account in four hops.
          </SplitHeading>
          <p className="body">
            The graph joins declared relatives with shared phones, emails, bank accounts and devices from KYC. Every hop is shown. None is inferred, and
            a pattern without a path never escalates.
          </p>
          <ol className="steps">
            {HOPS.map((h, i) => (
              <li key={h.text} ref={(el) => {
                steps.current[i] = el;
              }} className={`step${h.alert ? " step--alert" : ""}`}>
                {h.text}
              </li>
            ))}
          </ol>
        </div>
        <div className="pin__meta">
          60 accounts, 25 calls
          <br />
          NetworkX over declared links
          <br />
          <b>and shared KYC attributes</b>
        </div>
      </div>
    </section>
  );
}
