import { create } from "zustand";
import { ScrollTrigger } from "./gsap";
import { clamp01, reducedMotion } from "./motion";

export const STATIONS = [
  "hero",
  "gap",
  "sandwich",
  "call",
  "link",
  "chain",
  "ledger",
  "decide",
  "proof",
  "close",
] as const;
export type Station = (typeof STATIONS)[number];

const zeros = () => Object.fromEntries(STATIONS.map((s) => [s, 0])) as Record<Station, number>;

/**
 * Per-frame scroll data read inside useFrame. Mutable on purpose: no React
 * re-renders, no allocations. `p` is the choreography progress through a
 * station's pinned span; `v` is a 0..1 presence envelope while the station
 * is on screen.
 */
export const scroll = {
  p: zeros(),
  v: zeros(),
  velocity: 0,
  page: 0,
  pointer: { x: 0, y: 0 },
};

interface ScrollUIState {
  active: Station;
  ready: boolean;
  setActive: (s: Station) => void;
  setReady: () => void;
}

/** React-reactive bits only: current station for the nav, loader readiness. */
export const useScrollUI = create<ScrollUIState>((set) => ({
  active: "hero",
  ready: false,
  setActive: (active) => set({ active }),
  setReady: () => set({ ready: true }),
}));

/**
 * ScrollTrigger vars for a station. Writes choreography progress to
 * `scroll.p[id]` and marks the station active for the nav. Spread the
 * result into a timeline's `scrollTrigger` or `ScrollTrigger.create`.
 */
export function stationVars(id: Station, vars: ScrollTrigger.Vars = {}): ScrollTrigger.Vars {
  if (reducedMotion) {
    scroll.p[id] = 1;
    scroll.v[id] = 1;
  }
  return {
    ...vars,
    onUpdate: (self) => {
      scroll.p[id] = reducedMotion ? 1 : self.progress;
      vars.onUpdate?.(self);
    },
    onToggle: (self) => {
      if (self.isActive) useScrollUI.getState().setActive(id);
      vars.onToggle?.(self);
    },
  };
}

/**
 * Presence envelope: 0 while off screen, rising to 1 while the element is
 * in view, falling back to 0 as it leaves. Stations use it to fade and
 * scale their geometry in and out.
 */
export function presenceTrigger(id: Station, trigger: HTMLElement, pinnedExtra: () => number = () => 0) {
  return ScrollTrigger.create({
    trigger,
    start: "top bottom",
    // approach + (pinned travel) + leave
    end: () => `+=${trigger.offsetHeight + window.innerHeight + pinnedExtra()}`,
    invalidateOnRefresh: true,
    onUpdate: (self) => {
      if (reducedMotion) return;
      const vh = window.innerHeight * 0.8;
      const pos = self.scroll() - self.start;
      const total = self.end - self.start;
      scroll.v[id] = Math.min(clamp01(pos / vh), clamp01((total - pos) / vh));
    },
  });
}

/** The one thing the page asks the visitor to do: hold to approve. */
export const human = { hold: 0, sealed: false };
