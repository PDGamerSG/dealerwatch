import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { isMobile, range, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { PAPER, STAMP } from "../palette";
import { useStation } from "../useStation";

const BARS = isMobile ? 120 : 200;
const RADIUS = 1.65;
const X = isMobile ? 0 : 2.0;
const Y = isMobile ? 0.9 : 0.1;

/**
 * A ring of bars behaves like a recorded call: silence, speech, then the
 * leak cue flares a red segment and the ring expands.
 */
export function Waveform() {
  const { group } = useStation("call");
  const inst = useRef<THREE.InstancedMesh>(null);
  const ring = useRef<THREE.Mesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const heights = useMemo(() => new Float32Array(BARS).fill(0.08), []);

  useEffect(() => {
    const m = inst.current;
    if (!m) return;
    for (let i = 0; i < BARS; i++) m.setColorAt(i, PAPER);
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, []);

  useFrame((state, dt) => {
    const m = inst.current;
    if (!m) return;
    const p = scroll.p.call;
    const t = state.clock.elapsedTime;
    const talk = smooth(range(p, 0.12, 0.3)) * (1 - 0.7 * smooth(range(p, 0.8, 1)));
    const cue = smooth(range(p, 0.5, 0.62)) * (1 - 0.35 * smooth(range(p, 0.85, 1)));
    const k = Math.min(1, dt * 9);
    const speech = 0.55 + 0.45 * Math.sin(t * 2.3) * Math.sin(t * 0.7 + 1.3);

    for (let i = 0; i < BARS; i++) {
      const a = (i / BARS) * Math.PI * 2;
      const inCue = Math.abs(((a + Math.PI) % (Math.PI * 2)) - Math.PI) < 0.42; // around angle 0 (right side)
      const voice = 0.5 + 0.5 * Math.sin(t * 7 + i * 0.37) * Math.sin(t * 3.1 + i * 0.11);
      let target = 0.06 + talk * speech * voice * 0.85;
      if (inCue) target += cue * (0.5 + 0.35 * Math.sin(t * 9 + i));
      heights[i] += (target - heights[i]) * k;
      const r = RADIUS + (inCue ? cue * 0.25 : 0);
      dummy.position.set(Math.cos(a) * (r + heights[i] / 2), Math.sin(a) * (r + heights[i] / 2), 0);
      dummy.rotation.set(0, 0, a);
      dummy.scale.set(heights[i], 0.028, 0.028);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
      color.copy(PAPER).lerp(STAMP, inCue ? cue : 0);
      m.setColorAt(i, color);
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    if (ring.current) {
      ring.current.rotation.z = t * 0.08;
      const s = 1 + 0.03 * Math.sin(t * 2) * talk + 0.08 * cue;
      ring.current.scale.setScalar(s);
    }
  });

  return (
    <group ref={group} position={[X, Y, -0.4]} userData={{ baseScale: isMobile ? 0.7 : 1, baseY: Y }}>
      <instancedMesh ref={inst} args={[undefined, undefined, BARS]} frustumCulled={false}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.55} metalness={0.05} />
      </instancedMesh>
      <mesh ref={ring}>
        <torusGeometry args={[RADIUS - 0.08, 0.006, 8, 160]} />
        <meshBasicMaterial color={PAPER} opacity={0.35} />
      </mesh>
      <mesh>
        <torusGeometry args={[RADIUS + 0.95, 0.004, 8, 160]} />
        <meshBasicMaterial color={PAPER} opacity={0.12} />
      </mesh>
    </group>
  );
}
