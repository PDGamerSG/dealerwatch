import { createRoot } from "react-dom/client";
import "@fontsource-variable/archivo/wdth.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles/global.css";
import "./styles/ui.css";
import "./styles/sections.css";
import { App } from "./App";

// StrictMode is off: drei's Html portals re-mount roots during the double
// invoke and log unmount warnings that do not occur in production.
createRoot(document.getElementById("root")!).render(<App />);
