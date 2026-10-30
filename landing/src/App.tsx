import { lazy, Suspense } from "react";
import { SmoothScroll } from "./ui/SmoothScroll";
import { Loader } from "./ui/Loader";
import { Nav } from "./ui/Nav";
import { Rule } from "./ui/Rule";
import { Cursor } from "./ui/Cursor";
import { Timecode } from "./ui/Timecode";
import { LabelLayer } from "./ui/LabelLayer";
import { Hero } from "./sections/Hero";
import { GapSection } from "./sections/GapSection";
import { SandwichSection } from "./sections/SandwichSection";
import { CallSection } from "./sections/CallSection";
import { LinkSection } from "./sections/LinkSection";
import { ChainSection } from "./sections/ChainSection";
import { LedgerSection } from "./sections/LedgerSection";
import { DecideSection } from "./sections/DecideSection";
import { Proof } from "./sections/Proof";
import { Fit } from "./sections/Fit";
import { Close } from "./sections/Close";

const Scene = lazy(() => import("./scene/Scene").then((m) => ({ default: m.Scene })));

export function App() {
  return (
    <SmoothScroll>
      <Loader />
      <Suspense fallback={null}>
        <Scene />
      </Suspense>
      <LabelLayer />
      <Rule />
      <Nav />
      <Cursor />
      <Timecode />
      <main className="page">
        <Hero />
        <GapSection />
        <SandwichSection />
        <CallSection />
        <LinkSection />
        <ChainSection />
        <LedgerSection />
        <DecideSection />
        <Proof />
        <Fit />
        <Close />
      </main>
      <div className="grain" aria-hidden />
    </SmoothScroll>
  );
}
