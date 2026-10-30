import { useStationSection } from "../lib/use-station-section";
import { SplitHeading } from "../ui/SplitHeading";

export function GapSection() {
  const { ref } = useStationSection("gap", { pin: true, length: 160 });
  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="gap" className="station pin gap" aria-labelledby="gap-title">
      <div className="pin__view">
        <div className="pin__copy">
          <div className="station__head">
            <b>The gap</b>
            <span>three systems</span>
          </div>
          <SplitHeading className="display display--section" id="gap-title">
            Calls, orders and relationships live apart.
          </SplitHeading>
          <p className="body">
            The dealing desk keeps its call recordings. The order blotter keeps the fund's orders. KYC keeps who is related to whom. Proving a leak means
            joining all three by hand, after the fact, under a SEBI mandate that expects fund houses to catch it themselves. DealerWatch makes that join
            the default.
          </p>
        </div>
      </div>
    </section>
  );
}
