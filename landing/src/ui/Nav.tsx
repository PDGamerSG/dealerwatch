import { useEffect, useRef, useState } from "react";
import { useScrollUI, type Station } from "../lib/scroll";
import { useLenis } from "lenis/react";
import { MagneticButton } from "./MagneticButton";

const LINKS: { id: Station; label: string }[] = [
  { id: "sandwich", label: "Detect" },
  { id: "call", label: "Gather" },
  { id: "link", label: "Link" },
  { id: "chain", label: "Verify" },
  { id: "ledger", label: "Record" },
  { id: "decide", label: "Decide" },
];

export const REPO_URL = "https://github.com/PDGamerSG/dealerwatch";
/** The reviewer console. On the hosted site it is served next to this page at /app. */
export const APP_URL: string = import.meta.env.VITE_APP_URL ?? "/app";

export function Nav() {
  const active = useScrollUI((s) => s.active);
  const ready = useScrollUI((s) => s.ready);
  const lenis = useLenis();
  const [hidden, setHidden] = useState(false);
  const lastY = useRef(0);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      setHidden(y > lastY.current && y > 200);
      lastY.current = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { offset: 0, duration: 1.6 });
    else el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <nav className={`nav${hidden ? " is-hidden" : ""}`} aria-label="Primary" style={{ opacity: ready ? undefined : 0 }}>
      <a className="nav__mark" href="#hero" onClick={go("hero")}>
        DealerWatch <small>seed 7</small>
      </a>
      <div className="nav__links">
        {LINKS.map((l) => (
          <a key={l.id} href={`#${l.id}`} onClick={go(l.id)} className={active === l.id ? "is-active" : undefined}>
            {l.label}
          </a>
        ))}
      </div>
      <div className="nav__end">
        <MagneticButton className="btn btn--small" href={APP_URL}>
          Open the console
        </MagneticButton>
      </div>
    </nav>
  );
}
