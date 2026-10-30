import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { damp, isMobile, smooth } from "../lib/motion";
import { scroll } from "../lib/scroll";
import { makeTapeTexture } from "./tape-texture";

const SEGMENTS = isMobile ? 160 : 320;
const WIDTH = 1.25;

/**
 * The protagonist: a ribbon of printed tape sweeping through the hero and
 * returning at the close. Built every frame from a Catmull-Rom curve whose
 * control points breathe, with a slow twist so the paper catches light.
 */
export function Tape() {
  const mesh = useRef<THREE.Mesh>(null);
  const texture = useMemo(() => makeTapeTexture(), []);
  useEffect(() => () => texture.dispose(), [texture]);

  const base = useMemo(
    () => [
      new THREE.Vector3(-11, 4.6, -4),
      new THREE.Vector3(-6.5, 2.4, -2.2),
      new THREE.Vector3(-2.2, 1.3, -0.6),
      new THREE.Vector3(1.6, -0.6, 0.8),
      new THREE.Vector3(5.2, -2.1, 0.2),
      new THREE.Vector3(8.4, -3.2, -1.6),
      new THREE.Vector3(12, -4.6, -4),
    ],
    [],
  );
  const points = useMemo(() => base.map((p) => p.clone()), [base]);
  const curve = useMemo(() => new THREE.CatmullRomCurve3(points, false, "centripetal", 0.5), [points]);

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const n = SEGMENTS + 1;
    const pos = new Float32Array(n * 2 * 3);
    const uv = new Float32Array(n * 2 * 2);
    const idx: number[] = [];
    for (let i = 0; i < n; i++) {
      const u = (i / SEGMENTS) * 5.2;
      uv[i * 4] = u;
      uv[i * 4 + 1] = 0;
      uv[i * 4 + 2] = u;
      uv[i * 4 + 3] = 1;
      if (i < SEGMENTS) {
        const a = i * 2;
        idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    }
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    g.setIndex(idx);
    return g;
  }, []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  const tmp = useMemo(
    () => ({ p: new THREE.Vector3(), n: new THREE.Vector3(), b: new THREE.Vector3(), o: new THREE.Vector3(), opacity: 1 }),
    [],
  );

  useFrame((state, dt) => {
    const m = mesh.current;
    if (!m) return;
    const t = state.clock.elapsedTime;
    const hero = scroll.p.hero;
    const close = scroll.v.close;
    // the tape owns the hero; it comes back for the close
    const target = Math.max(1 - smooth(Math.min(1, hero * 1.4)), close);
    tmp.opacity = damp(tmp.opacity, target, 4, dt);
    const mat = m.material as THREE.MeshStandardMaterial;
    mat.opacity = tmp.opacity;
    m.visible = tmp.opacity > 0.01;
    if (!m.visible) return;

    // breathe the control points and let scroll pull the ribbon down and away
    const sink = smooth(Math.min(1, hero * 1.2)) * 3.5 * (1 - close);
    for (let i = 0; i < points.length; i++) {
      const b = base[i];
      points[i].set(
        b.x + Math.sin(t * 0.35 + i * 1.7) * 0.25,
        b.y + Math.sin(t * 0.5 + i * 1.1) * 0.35 - sink + close * 1.2,
        b.z + Math.cos(t * 0.3 + i * 0.9) * 0.3,
      );
    }
    curve.updateArcLengths();
    const frames = curve.computeFrenetFrames(SEGMENTS, false);
    const pos = geometry.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i <= SEGMENTS; i++) {
      const u = i / SEGMENTS;
      curve.getPointAt(u, tmp.p);
      tmp.n.copy(frames.normals[i]);
      tmp.b.copy(frames.binormals[i]);
      const twist = u * Math.PI * 0.9 + t * 0.18 + Math.sin(u * 6 + t * 0.4) * 0.2;
      tmp.o.copy(tmp.n).multiplyScalar(Math.cos(twist)).addScaledVector(tmp.b, Math.sin(twist)).multiplyScalar(WIDTH / 2);
      pos.setXYZ(i * 2, tmp.p.x - tmp.o.x, tmp.p.y - tmp.o.y, tmp.p.z - tmp.o.z);
      pos.setXYZ(i * 2 + 1, tmp.p.x + tmp.o.x, tmp.p.y + tmp.o.y, tmp.p.z + tmp.o.z);
    }
    pos.needsUpdate = true;
    geometry.computeVertexNormals();
    // the print runs along the tape, faster when the page is scrolled fast
    texture.offset.x += dt * (0.045 + Math.min(0.5, Math.abs(scroll.velocity) * 0.004));
  });

  return (
    <mesh ref={mesh} geometry={geometry} frustumCulled={false}>
      <meshStandardMaterial map={texture} roughness={0.82} metalness={0} side={THREE.DoubleSide} transparent envMapIntensity={0.35} />
    </mesh>
  );
}
