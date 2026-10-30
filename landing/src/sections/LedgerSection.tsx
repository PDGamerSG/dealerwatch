import { useMemo, useRef } from "react";
import { useStationSection } from "../lib/use-station-section";
import { flag } from "../scene/useStation";
import { BLOCKS, TAMPERED } from "../scene/stations/Ledger";
import { SplitHeading } from "../ui/SplitHeading";

const EVENTS = [
  "run.started",
  "dataset.validated",
  "detector.indexed",
  "candidate.found",
  "calls.gathered",
  "cue.extracted",
  "links.resolved",
  "chain.verified",
  "summary.checked",
  "case.published",
  "review.started",
  "info.requested",
  "decision.recorded",
  "export.signed",
];

function digest(seed: number) {
  let x = (seed * 2654435761) >>> 0;
  let out = "";
  for (let i = 0; i < 10; i++) {
    x = (x ^ (x << 13)) >>> 0;
    x = (x ^ (x >>> 17)) >>> 0;
    x = (x ^ (x << 5)) >>> 0;
    out += (x & 0xf).toString(16);
  }
  return out;
}

export function LedgerSection() {
  const rows = useRef<(HTMLLIElement | null)[]>([]);
  const result = useRef<HTMLDivElement>(null);
  const digests = useMemo(() => Array.from({ length: BLOCKS }, (_, i) => digest(i + 11)), []);

  const { ref } = useStationSection("ledger", {
    pin: true,
    length: 260,
    onUpdate: (p) => {
      const build = Math.min(1, p / 0.38);
      const sweep1 = (p - 0.4) / 0.2;
      const tampered = p >= 0.64;
      const sweep2 = (p - 0.74) / 0.22;
      for (let i = 0; i < BLOCKS; i++) {
        const el = rows.current[i];
        flag(el, "is-on", build * BLOCKS >= i + 0.5);
        const verified = tampered ? sweep2 * BLOCKS >= i + 0.5 && i < TAMPERED : sweep1 * BLOCKS >= i + 0.5;
        flag(el, "is-verified", verified);
        flag(el, "is-tampered", tampered && i === TAMPERED);
      }
      const r = result.current;
      if (r) {
        const done1 = p >= 0.6 && p < 0.64;
        const done2 = p >= 0.96;
        flag(r, "is-on", done1 || done2);
        flag(r, "is-bad", done2);
        r.textContent = done2 ? `Mismatch at sequence 0${TAMPERED}: stored digest does not match the recomputed chain.` : `Chain verified. ${BLOCKS} events, head ${digests[BLOCKS - 1]}.`;
      }
    },
  });

  return (
    <section ref={ref as React.RefObject<HTMLElement>} id="ledger" className="station pin" aria-labelledby="ledger-title">
      <div className="pin__view">
        <div className="pin__copy">
          <div className="station__head">
            <b>Record</b>
            <span>hash chain</span>
          </div>
          <SplitHeading className="display display--section" id="ledger-title">
            Every step hashed. Every edit named.
          </SplitHeading>
          <p className="body">
            Pipeline stages and reviewer decisions append to a hash-chained ledger. Verification recomputes every digest; a tampered row is reported by
            its sequence number. Evidence exports carry their own digest so a file can be checked on its own.
          </p>
        </div>
        <div className="hash-rows" aria-hidden>
          <ol>
            {EVENTS.map((e, i) => (
              <li key={e} ref={(el) => {
                rows.current[i] = el;
              }} className="hash-row">
                <span>{String(i).padStart(2, "0")}</span>
                <span>{e}</span>
                <span className="hash-row__digest">{digests[i]}</span>
              </li>
            ))}
          </ol>
          <div ref={result} className="ledger__result" />
        </div>
      </div>
    </section>
  );
}
