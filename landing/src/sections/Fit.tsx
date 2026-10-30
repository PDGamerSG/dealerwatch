import { Marquee } from "../ui/Marquee";
import { SplitHeading } from "../ui/SplitHeading";

const ROW_A = ["FastAPI", "SQLite", "NetworkX", "Sarvam ASR", "Ollama", "OpenAI", "Anthropic", "Docker"];
const ROW_B = ["Order blotter in", "Call recordings in", "KYC links in", "Investigation queue out", "Evidence JSON out", "CSV out"];

export function Fit() {
  return (
    <section id="fit" className="station fit" aria-labelledby="fit-title">
      <div className="station__head">
        <b>Fit</b>
        <span>the systems a fund house already has</span>
      </div>
      <SplitHeading className="display display--section" id="fit-title">
        Blotter in. Queue out.
      </SplitHeading>
      <p className="body">
        One FastAPI service, SQLite persistence, no external dependency in the default mode. Hosted or local models and speech recognition are optional
        adapters with deterministic fallbacks, so the demonstration runs the same with the network unplugged.
      </p>
      <div className="fit__rows" aria-hidden>
        <Marquee className="fit__row" duration={46}>
          {ROW_A.map((s) => (
            <span key={s}>{s}</span>
          ))}
        </Marquee>
        <Marquee className="fit__row" duration={58} reverse>
          {ROW_B.map((s) => (
            <span key={s}>{s}</span>
          ))}
        </Marquee>
      </div>
    </section>
  );
}
