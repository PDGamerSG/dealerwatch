# DealerWatch landing page

A standalone, scroll-driven marketing page for DealerWatch. It has no backend dependency: every number and name on it is static, synthetic and consistent with the seed 7 universe described in the repository root.

The page follows one ribbon of printed tape through the investigation: the gap between systems, the sandwich the detector finds, the recorded call, the account-link path, the nine-link verification chain, the hash-chained ledger, and the one thing the software never does, the human decision. The visitor can hold a button to approve an escalation; nothing else on the page pretends to act.

## Run

```bash
cd landing
npm install
npm run dev
```

Open the printed URL. `npm run build` writes a static site to `dist/`; `npm run preview` serves it. `npm run typecheck` runs the TypeScript project references.

## Stack

- Vite 8, React 19, TypeScript 5.9
- three 0.186 through React Three Fiber 9 and drei 10, with bloom and vignette from `@react-three/postprocessing`
- GSAP 3.15 (ScrollTrigger, SplitText) and Lenis for smooth scrolling
- Archivo variable (width axis driven by scroll velocity) and IBM Plex Mono, self-hosted through Fontsource

## 3D assets

`public/models/*.glb` are generated headlessly by Blender from `tools/blender/make_assets.py`:

```bash
npm run assets
```

This needs `blender` on the PATH (Blender 4.2 or newer; built with 5.2 LTS). The script writes a stadium chain link, a bevelled slab and a bevelled seal. The GLBs are committed so the page builds without Blender.

## Structure

- `src/scene/` the fixed WebGL canvas: `Tape` (the ribbon), one station per section under `stations/`, and `useStation` for presence fading
- `src/sections/` one React component per page section, each wired to its station with `useStationSection`
- `src/lib/scroll.ts` the single source of truth for scroll progress that both the DOM and the scene read
- `src/ui/` loader, nav, cursor, marquee, counters, the ledger rule and the projected label layer
- `src/styles/` tokens, type roles, section layouts

## Behaviour notes

- `prefers-reduced-motion` turns off smoothing, pinning and heavy post-processing; every station renders its final state.
- Phones use the same page with lighter scene density and a native horizontal scroll for the nine-link section instead of pinning.
- All copy, figures and transcripts are fictional. The page does not call the DealerWatch API.
