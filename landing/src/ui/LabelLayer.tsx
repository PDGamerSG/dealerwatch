import type { ReactNode } from "react";
import { registerLabel } from "../lib/labels";
import { CASE, fmtQty } from "../lib/tape-data";

interface LabelDef {
  id: string;
  className: string;
  /** which corner of the label sits on the anchor */
  origin: string;
  content: ReactNode;
}

const LABELS: LabelDef[] = [
  { id: "panel-0", className: "panel-label", origin: "-50%, -50%", content: "Recorder" },
  { id: "panel-1", className: "panel-label", origin: "-50%, -50%", content: "Blotter" },
  { id: "panel-2", className: "panel-label", origin: "-50%, -50%", content: "KYC" },
  {
    id: "sw-buy",
    className: "callout callout--alert",
    origin: "-50%, -100%",
    content: (
      <>
        {CASE.preTrade.time} <em>buy</em> {fmtQty(CASE.preTrade.qty)} {CASE.scrip}
        <small>account {CASE.account}, 41 min before the order</small>
      </>
    ),
  },
  {
    id: "sw-order",
    className: "callout callout--ok",
    origin: "-50%, -100%",
    content: (
      <>
        {CASE.order.time} <em>fund order</em> buy {fmtQty(CASE.order.qty)} {CASE.scrip}
        <small>price steps up on the tape</small>
      </>
    ),
  },
  {
    id: "sw-sell",
    className: "callout callout--alert",
    origin: "-50%, -100%",
    content: (
      <>
        {CASE.postTrade.time} <em>sell</em> {fmtQty(CASE.postTrade.qty)} {CASE.scrip}
        <small>same account, 22 min after</small>
      </>
    ),
  },
  {
    id: "sw-bracket",
    className: "callout callout--alert",
    origin: "-50%, 0",
    content: (
      <>
        sandwich <em>+₹{fmtQty(CASE.profitInr)}</em> matched quantity
        <small>repeat 3 of 3 on this account</small>
      </>
    ),
  },
  { id: "hop-0", className: "callout callout--ok", origin: "-50%, -100%", content: <>Dealer {CASE.dealer}<small>dealing desk</small></> },
  { id: "hop-1", className: "callout callout--ok", origin: "-50%, -100%", content: <>{CASE.relative}<small>declared relative</small></> },
  { id: "hop-2", className: "callout callout--ok", origin: "-50%, -100%", content: <>{CASE.sharedAttr}<small>KYC attribute</small></> },
  { id: "hop-3", className: "callout callout--alert", origin: "-50%, -100%", content: <>account {CASE.account}<small>trading account</small></> },
];

/** Fixed layer of labels the scene positions every frame. */
export function LabelLayer() {
  return (
    <div className="labels" aria-hidden>
      {LABELS.map((l) => (
        <div key={l.id} className="label" ref={(el) => registerLabel(l.id, el)}>
          <div className={l.className} style={{ transform: `translate(${l.origin})` }}>
            {l.content}
          </div>
        </div>
      ))}
    </div>
  );
}
