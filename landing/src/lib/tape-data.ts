/**
 * Synthetic tape rows. Everything here is fictional and deterministic so the
 * page renders identically on every load. Figures echo the seeded
 * universe (seed 7) but are not read from it.
 */
const SCRIPS = [
  ["RELIANCE", 2871.4],
  ["HDFCBANK", 1642.2],
  ["INFY", 1518.6],
  ["TCS", 3966.0],
  ["ICICIBANK", 1239.9],
  ["SBIN", 812.5],
  ["LT", 3498.3],
  ["ITC", 468.2],
  ["AXISBANK", 1127.0],
  ["BHARTIARTL", 1689.4],
  ["KOTAKBANK", 1821.7],
  ["MARUTI", 12410.0],
] as const;

export interface TapeRow {
  time: string;
  side: "BUY" | "SELL";
  qty: number;
  scrip: string;
  price: number;
  account: string;
}

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const pad = (n: number, w = 2) => String(n).padStart(w, "0");
export const fmtQty = (n: number) => n.toLocaleString("en-IN");
export const fmtPrice = (n: number) => n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function tapeRows(count: number, seed = 7): TapeRow[] {
  const rnd = mulberry32(seed);
  const rows: TapeRow[] = [];
  let seconds = 9 * 3600 + 15 * 60 + 2;
  for (let i = 0; i < count; i++) {
    seconds += 3 + Math.floor(rnd() * 94);
    const [scrip, base] = SCRIPS[Math.floor(rnd() * SCRIPS.length)];
    const drift = 1 + (rnd() - 0.5) * 0.012;
    const lots = [50, 100, 150, 200, 250, 400, 600, 1200, 2400, 5000];
    rows.push({
      time: `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`,
      side: rnd() > 0.5 ? "BUY" : "SELL",
      qty: lots[Math.floor(rnd() * lots.length)],
      scrip,
      price: Math.round(base * drift * 20) / 20,
      account: `a${1000 + Math.floor(rnd() * 8999)}`,
    });
  }
  return rows;
}

export const rowText = (r: TapeRow) =>
  `${r.time}  ${r.side.padEnd(4)}  ${fmtQty(r.qty).padStart(6)}  ${r.scrip.padEnd(10)}  ${fmtPrice(r.price).padStart(9)}  ${r.account}`;

/** The one planted case the page walks through. */
export const CASE = {
  scrip: "RELIANCE",
  dealer: "R. Mehta",
  relative: "brother-in-law",
  sharedAttr: "shared mobile number",
  account: "a4471",
  preTrade: { time: "11:23", side: "BUY", qty: 2400, price: 2871.4 },
  order: { time: "12:04", side: "BUY", qty: 180000 },
  postTrade: { time: "12:26", side: "SELL", qty: 2400, price: 2950.6 },
  profitInr: 190080,
  reviewer: "A. Rao",
  decidedAt: "14:02",
} as const;
