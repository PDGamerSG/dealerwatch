import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { damp } from "../lib/motion";
import { scroll, type Station } from "../lib/scroll";

type Fade = THREE.Material & { opacity: number };

/**
 * Presence handling shared by every station: the group hides when its
 * section is off screen, scales in as it arrives, and every transparent
 * material under it fades with the envelope. Returns the group ref plus a
 * smoothed presence value for the station's own choreography.
 */
export function useStation(id: Station, options: { lift?: number } = {}) {
  const group = useRef<THREE.Group>(null);
  const mats = useRef<{ m: Fade; max: number }[]>([]);
  const state = useRef({ v: 0 });
  const lift = options.lift ?? 0.6;

  useEffect(() => {
    const list: { m: Fade; max: number }[] = [];
    group.current?.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh && !(o as THREE.Points).isPoints && !(o as THREE.Line).isLine) return;
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of materials) {
        if (!m) continue;
        m.transparent = true;
        list.push({ m: m as Fade, max: m.userData.maxOpacity ?? (m as Fade).opacity ?? 1 });
      }
    });
    mats.current = list;
  }, []);

  useFrame((_, dt) => {
    const g = group.current;
    if (!g) return;
    const target = scroll.v[id];
    const v = (state.current.v = damp(state.current.v, target, 6, dt));
    g.visible = v > 0.004;
    if (!g.visible) return;
    const base = (g.userData.baseScale as number | undefined) ?? 1;
    const baseY = (g.userData.baseY as number | undefined) ?? 0;
    g.scale.setScalar(base * (0.9 + 0.1 * v));
    g.position.y = baseY + (1 - v) * -lift;
    for (const { m, max } of mats.current) m.opacity = max * v;
  });

  return { group, state };
}

/** Toggle a class on a DOM element only when the boolean changes. */
export function flag(el: HTMLElement | null, cls: string, on: boolean) {
  if (!el) return;
  if (on) {
    if (!el.classList.contains(cls)) el.classList.add(cls);
  } else if (el.classList.contains(cls)) {
    el.classList.remove(cls);
  }
}

// Models are plain GLBs. Draco and meshopt decoders are turned off at every useGLTF
// call so no WebAssembly is compiled; the hosted CSP allows script-src 'self' only.
export const modelUrl = (name: string) => `${import.meta.env.BASE_URL}models/${name}.glb`;

export function firstMesh(nodes: Record<string, THREE.Object3D>): THREE.Mesh {
  const mesh = Object.values(nodes).find((n) => (n as THREE.Mesh).isMesh) as THREE.Mesh | undefined;
  if (!mesh) throw new Error("GLB contains no mesh");
  return mesh;
}
