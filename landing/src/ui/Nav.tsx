import { useScrollUI } from "../lib/scroll";
import { MagneticButton } from "./MagneticButton";

export const REPO_URL = "https://github.com/PDGamerSG/dealerwatch";
/** The reviewer console. On the hosted site it is served next to this page at /app. */
export const APP_URL: string = import.meta.env.VITE_APP_URL ?? "/app";

/** One fixed control, top right, on every screen of the page: the way into the console. */
export function Nav() {
  const ready = useScrollUI((s) => s.ready);
  return (
    <nav className="nav" aria-label="Primary" style={{ opacity: ready ? undefined : 0 }}>
      <MagneticButton className="btn btn--small" href={APP_URL}>
        Open the console
      </MagneticButton>
    </nav>
  );
}
