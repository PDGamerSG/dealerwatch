import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { isMobile, range, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { GRAPHITE, PAPER, RULE, STAMP } from "../palette";
import { useStation } from "../useStation";

export const BLOCKS = 14;
export const TAMPERED = 3;
const STEP = 0.34;

/**
 * Hash-chained blocks stack up, a verification sweep paints them blue, one
 * block is edited and turns red, and the next sweep stops exactly there.
 */
export function Ledger() {
  const { group } = useStation("ledger");
  const inst = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const cur = useMemo(() => new Float32Array(BLOCKS), []);

  useEffect(() => {
    const m = inst.current;
    if (!m) return;
    for (let i = 0; i < BLOCKS; i++) m.setColorAt(i, GRAPHITE);
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, []);

  useFrame((state, dt) => {
    const m = inst.current;
    if (!m) return;
    const p = scroll.p.ledger;
    const t = state.clock.elapsedTime;
    const build = smooth(range(p, 0, 0.38));
    const sweep1 = range(p, 0.4, 0.6);
    const tamper = smooth(range(p, 0.62, 0.7));
    const sweep2 = range(p, 0.74, 0.96);
    const k = Math.min(1, dt * 8);
    for (let i = 0; i < BLOCKS; i++) {
      const target = range(build, i / BLOCKS, i / BLOCKS + 1.2 / BLOCKS);
      cur[i] += (target - cur[i]) * k;
      const s = cur[i];
      const isBad = i === TAMPERED;
      const jitter = isBad ? tamper * (0.18 + Math.sin(t * 40) * 0.01 * (1 - smooth(range(p, 0.7, 0.78)))) : 0;
      dummy.position.set(jitter, -2.3 + i * STEP + (1 - s) * 1.2, 0);
      dummy.rotation.set(0, isBad ? tamper * 0.08 : 0, 0);
      dummy.scale.set(1.9 * s, 0.24 * s, 0.7 * s);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);

      const v1 = sweep1 > 0 ? smooth(range(sweep1, i / BLOCKS, i / BLOCKS + 0.1)) : 0;
      const reach2 = sweep2 > 0 ? smooth(range(sweep2, i / BLOCKS, i / BLOCKS + 0.1)) : 0;
      const verified = tamper > 0.5 ? (i < TAMPERED ? reach2 : 0) : v1;
      color.copy(GRAPHITE).lerp(PAPER, 0.42 * s).lerp(RULE, verified);
      if (isBad) color.lerp(STAMP, tamper);
      m.setColorAt(i, color);
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  });

  return (
    <group ref={group} position={isMobile ? [0, 0.9, 0] : [0.5, 0.1, 0]} rotation={[0.18, -0.55, 0]} userData={{ baseScale: isMobile ? 0.45 : 0.6, baseY: isMobile ? 0.9 : 0.1 }}>
      <instancedMesh ref={inst} args={[undefined, undefined, BLOCKS]} frustumCulled={false}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.35} metalness={0.5} envMapIntensity={1.1} />
      </instancedMesh>
      <mesh position={[0, -2.3 + (BLOCKS * STEP) / 2 - STEP / 2, 0]}>
        <cylinderGeometry args={[0.025, 0.025, BLOCKS * STEP + 0.6, 12]} />
        <meshStandardMaterial color={PAPER} roughness={0.3} metalness={0.8} opacity={0.6} />
      </mesh>
    </group>
  );
}
