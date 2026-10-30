import { useState } from "react";
import { useStationSection } from "../lib/use-station-section";
import { rowText, tapeRows } from "../lib/tape-data";
import { Marquee } from "../ui/Marquee";
import { MagneticButton } from "../ui/MagneticButton";
import { REPO_URL } from "../ui/Nav";
import { SplitHeading } from "../ui/SplitHeading";

const CMD = "uv run --frozen python -m dealerwatch";
const ROWS = tapeRows(16, 13).map(rowText);

export function Close() {
  const { ref } = useStationSection("close");
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CMD);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };
  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="close" className="station close" aria-labelledby="close-title">
      <div className="close__inner">
        <div className="station__head">
          <b>Run</b>
          <span>one command, no keys</span>
        </div>
        <SplitHeading className="display display--section close__title" id="close-title">
          Run the whole investigation on your laptop.
        </SplitHeading>
        <div className="close__row">
          <p className="body">
            The command installs locked dependencies, builds the seed 7 universe, validates it, investigates it and serves the reviewer console at
            127.0.0.1:8077. Existing cases and decisions are preserved across runs.
          </p>
          <div className="close__links">
            <MagneticButton className="btn btn--solid" href={REPO_URL} target="_blank" rel="noreferrer">
              <span className="btn__dot" />
              View repository
            </MagneticButton>
            <MagneticButton className="btn" href={`${REPO_URL}/blob/main/ARCHITECTURE.md`} target="_blank" rel="noreferrer">
              Read the architecture
            </MagneticButton>
            <MagneticButton className="btn" href={`${REPO_URL}/blob/main/EVAL.md`} target="_blank" rel="noreferrer">
              See the evaluation
            </MagneticButton>
          </div>
          <div className="cmd close__cmd">
            <span>{CMD}</span>
            <button type="button" onClick={copy} data-cursor="hover">
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      </div>

      <footer className="footer">
        <div>
          <b>DealerWatch</b> is a hackathon rehearsal on synthetic data. Names, accounts, recordings and figures are fictional.
          <br />
          Rules recommend. A person escalates. Nothing on this page is investment or legal advice.
        </div>
        <div className="footer__right">
          Seed 7: 40 orders, 2,558 trades, 60 accounts, 25 calls
          <br />
          Python 3.12, FastAPI, SQLite, NetworkX, three.js
        </div>
      </footer>
      <div style={{ margin: "0 calc(-1 * var(--right)) 0 calc(-1 * var(--content))" }}>
        <Marquee className="tape-strip" duration={80} reverse>
          {ROWS.map((r) => (
            <span key={r}>{r}</span>
          ))}
        </Marquee>
      </div>
    </section>
  );
}
