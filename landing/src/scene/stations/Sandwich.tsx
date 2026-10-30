import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import "../three-elements";
import { isMobile, range, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { placeLabel } from "../../lib/labels";
import { DIM, PAPER, RULE, STAMP } from "../palette";
import { firstMesh, modelUrl, useStation } from "../useStation";

const NOISE = isMobile ? 70 : 130;
const CLUSTER = 18;
const COUNT = NOISE + CLUSTER * 2;
const AXIS_Y = -1.25;
const X_BUY = -1.75;
const X_SELL = 1.95;
const SCALE = isMobile ? 0.48 : 0.78;

function seeded(seed: number) {
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

/**
 * Trades on a time axis. Noise first, then the fund order rises at zero,
 * the price steps up, and the two suspicious clusters light up on either
 * side of it: the sandwich.
 */
export function Sandwich() {
  const { nodes } = useGLTF(modelUrl("slab"), false, false);
  const slabGeo = useMemo(() => firstMesh(nodes as Record<string, THREE.Object3D>).geometry, [nodes]);
  const { group } = useStation("sandwich");
  const inst = useRef<THREE.InstancedMesh>(null);
  const slab = useRef<THREE.Mesh>(null);
  const price = useRef<THREE.Line>(null);
  const bracket = useRef<THREE.Line>(null);
  const anchors = useRef<(THREE.Object3D | null)[]>([]);

  const data = useMemo(() => {
    const rnd = seeded(7);
    const items: { x: number; y: number; kind: 0 | 1 | 2; phase: number }[] = [];
    for (let i = 0; i < NOISE; i++) {
      const x = -3.6 + rnd() * 7.2;
      items.push({ x, y: AXIS_Y + 0.25 + rnd() * 1.9 + (x > 0 ? 0.6 : 0), kind: 0, phase: rnd() * Math.PI * 2 });
    }
    for (let i = 0; i < CLUSTER; i++) {
      items.push({ x: X_BUY + (rnd() - 0.5) * 0.7, y: AXIS_Y + 0.3 + rnd() * 0.9, kind: 1, phase: rnd() * 6 });
    }
    for (let i = 0; i < CLUSTER; i++) {
      items.push({ x: X_SELL + (rnd() - 0.5) * 0.7, y: AXIS_Y + 0.95 + rnd() * 0.9, kind: 2, phase: rnd() * 6 });
    }
    return items;
  }, []);

  const pricePoints = useMemo(() => {
    const rnd = seeded(21);
    const pts: number[] = [];
    let y = AXIS_Y + 1.05;
    for (let i = 0; i <= 120; i++) {
      const x = -3.6 + (i / 120) * 7.2;
      y += (rnd() - 0.5) * 0.08;
      if (x > -0.05 && x < 0.6) y += 0.1;
      pts.push(x, y, 0.02);
    }
    return new Float32Array(pts);
  }, []);

  const bracketPoints = useMemo(
    () => new Float32Array([X_BUY - 0.5, AXIS_Y - 0.25, 0, X_BUY - 0.5, AXIS_Y - 0.5, 0, X_SELL + 0.5, AXIS_Y - 0.5, 0, X_SELL + 0.5, AXIS_Y - 0.25, 0]),
    [],
  );

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const scales = useMemo(() => new Float32Array(COUNT), []);

  useEffect(() => {
    const m = inst.current;
    if (!m) return;
    for (let i = 0; i < COUNT; i++) {
      dummy.position.set(data[i].x, data[i].y, 0);
      dummy.scale.setScalar(0.0001);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
      m.setColorAt(i, DIM);
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, [data, dummy]);

  useFrame((state, dt) => {
    const m = inst.current;
    if (!m) return;
    const p = scroll.p.sandwich;
    const t = state.clock.elapsedTime;
    const noiseIn = smooth(range(p, 0.0, 0.3));
    const orderIn = smooth(range(p, 0.28, 0.5));
    const buyOn = smooth(range(p, 0.5, 0.68));
    const sellOn = smooth(range(p, 0.68, 0.86));
    const bracketOn = smooth(range(p, 0.84, 1));
    const k = Math.min(1, dt * 7);

    for (let i = 0; i < COUNT; i++) {
      const d = data[i];
      let target: number;
      if (d.kind === 0) target = 0.065 * range(noiseIn, (i / NOISE) * 0.8, (i / NOISE) * 0.8 + 0.2);
      else if (d.kind === 1) target = 0.065 * noiseIn + 0.06 * buyOn;
      else target = 0.065 * noiseIn + 0.06 * sellOn;
      scales[i] += (target - scales[i]) * k;
      const lit = d.kind === 1 ? buyOn : d.kind === 2 ? sellOn : 0;
      const pull = d.kind === 0 ? 0 : lit * 0.35;
      dummy.position.set(d.x, d.y - pull * (d.y - (d.kind === 1 ? AXIS_Y + 0.55 : AXIS_Y + 1.25)), 0.02 * Math.sin(t + d.phase));
      dummy.rotation.set(0, 0, d.kind === 0 ? 0 : lit * Math.PI * 0.25);
      dummy.scale.setScalar(Math.max(0.0001, scales[i] * (1 + 0.12 * Math.sin(t * 2 + d.phase) * lit)));
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
      color.copy(DIM).lerp(PAPER, 0.55).lerp(STAMP, d.kind === 0 ? 0 : lit);
      m.setColorAt(i, color);
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;

    if (slab.current) {
      slab.current.position.y = AXIS_Y + 1.15 - (1 - orderIn) * 3.2;
      slab.current.scale.set(1, 0.3 + 0.7 * orderIn, 1);
      slab.current.rotation.y = Math.PI / 2 + Math.sin(t * 0.5) * 0.04;
      const mat = slab.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.5 + 0.5 * Math.sin(t * 2) * orderIn;
    }
    if (price.current) price.current.geometry.setDrawRange(0, Math.floor(121 * smooth(range(p, 0.1, 0.55))));
    if (bracket.current) bracket.current.geometry.setDrawRange(0, bracketOn > 0 ? 2 + Math.floor(2.99 * bracketOn) : 0);

    const on = scroll.v.sandwich > 0.4;
    placeLabel("sw-buy", anchors.current[0], state.camera, state.size, on && buyOn > 0.5);
    placeLabel("sw-order", anchors.current[1], state.camera, state.size, on && orderIn > 0.6);
    placeLabel("sw-sell", anchors.current[2], state.camera, state.size, on && sellOn > 0.5);
    placeLabel("sw-bracket", anchors.current[3], state.camera, state.size, on && bracketOn > 0.6);
  });

  const pos: [number, number, number] = isMobile ? [0.35, 0.9, 0] : [2.7, 0.2, 0];

  return (
    <group ref={group} position={pos} userData={{ baseScale: SCALE, baseY: pos[1] }}>
      <instancedMesh ref={inst} args={[undefined, undefined, COUNT]} frustumCulled={false}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.45} metalness={0.15} envMapIntensity={0.8} />
      </instancedMesh>

      <threeLine ref={price} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[pricePoints, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={PAPER} opacity={0.9} />
      </threeLine>

      <threeLine frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[new Float32Array([-3.8, AXIS_Y, 0, 3.8, AXIS_Y, 0]), 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={PAPER} opacity={0.4} />
      </threeLine>

      <threeLine ref={bracket} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[bracketPoints, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={STAMP} opacity={0.9} />
      </threeLine>

      <mesh ref={slab} geometry={slabGeo} scale={[1, 1, 1]}>
        <meshStandardMaterial color="#1b2740" roughness={0.3} metalness={0.4} emissive={RULE} emissiveIntensity={0.6} envMapIntensity={1.2} />
      </mesh>

      <object3D ref={(el) => { anchors.current[0] = el; }} position={[X_BUY, AXIS_Y + 1.5, 0]} />
      <object3D ref={(el) => { anchors.current[1] = el; }} position={[0, AXIS_Y + 2.45, 0]} />
      <object3D ref={(el) => { anchors.current[2] = el; }} position={[X_SELL, AXIS_Y + 2.1, 0]} />
      <object3D ref={(el) => { anchors.current[3] = el; }} position={[(X_BUY + X_SELL) / 2, AXIS_Y - 0.6, 0]} />
    </group>
  );
}
