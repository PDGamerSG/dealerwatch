import { useScrollUI } from "../lib/scroll";
import { useStationSection } from "../lib/use-station-section";
import { rowText, tapeRows } from "../lib/tape-data";
import { Marquee } from "../ui/Marquee";
import { MagneticButton } from "../ui/MagneticButton";
import { SplitHeading } from "../ui/SplitHeading";
import { useLenis } from "lenis/react";

const ROWS = tapeRows(18, 7).map(rowText);

export function Hero() {
  const { ref } = useStationSection("hero");
  const ready = useScrollUI((s) => s.ready);
  const lenis = useLenis();

  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { duration: 1.8 });
    else el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="hero" className="hero" aria-label="Introduction">
      <div className="hero__scroll" aria-hidden>
        <i />
        <span>Scroll to follow the tape</span>
      </div>

      {ready && (
        <SplitHeading as="h1" className="display display--hero hero__title" immediate delay={0.1}>
          Front-running leaves a trail on the tape.
        </SplitHeading>
      )}
      {!ready && <h1 className="display display--hero hero__title" style={{ opacity: 0 }}>Front-running leaves a trail on the tape.</h1>}

      <div className="hero__row">
        <p className="lede">
          DealerWatch joins what was said on the dealer desk to the trades that followed and the accounts that profited. Rules recommend.
          A person escalates.
        </p>
        <div className="hero__actions">
          <MagneticButton className="btn btn--solid" href="#sandwich" onClick={go("sandwich")}>
            <span className="btn__dot" />
            Follow the evidence
          </MagneticButton>
          <MagneticButton className="btn" href="#close" onClick={go("close")}>
            Run it in one command
          </MagneticButton>
        </div>
      </div>

      <div className="hero__tape">
        <Marquee className="tape-strip" duration={70}>
          {ROWS.map((r) => (
            <span key={r}>{r}</span>
          ))}
        </Marquee>
      </div>
    </section>
  );
}
