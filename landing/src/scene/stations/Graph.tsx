import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import "../three-elements";
import { isMobile, range, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { CASE } from "../../lib/tape-data";
import { DIM, PAPER, RULE, STAMP } from "../palette";
import { placeLabel } from "../../lib/labels";
import { useStation } from "../useStation";

const N = isMobile ? 28 : 48;
const PATH: { pos: [number, number, number]; label: string; sub: string }[] = [
  { pos: [-1.2, 1.35, 0.3], label: `Dealer ${CASE.dealer}`, sub: "dealing desk" },
  { pos: [0.35, 0.55, 0.5], label: CASE.relative, sub: "declared relative" },
  { pos: [1.7, -0.35, 0.2], label: CASE.sharedAttr, sub: "KYC attribute" },
  { pos: [3.1, -1.3, 0.45], label: `account ${CASE.account}`, sub: "trading account" },
];

function seeded(seed: number) {
  return () => {
    seed = (seed * 48271) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

/** A constellation of accounts; one path lights up hop by hop. */
export function Graph() {
  const { group } = useStation("link");
  const nodes = useRef<THREE.InstancedMesh>(null);
  const path = useRef<THREE.Line>(null);
  const hops = useRef<(THREE.Mesh | null)[]>([]);
  const anchors = useRef<(THREE.Object3D | null)[]>([]);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const { positions, edges } = useMemo(() => {
    const rnd = seeded(5);
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i < N; i++) {
      const a = rnd() * Math.PI * 2;
      const r = 0.6 + Math.sqrt(rnd()) * 3.4;
      pts.push(new THREE.Vector3(1 + Math.cos(a) * r, Math.cos(a * 1.7) * 0.2 + Math.sin(a) * r * 0.62, -0.8 + rnd() * 1.4));
    }
    const seg: number[] = [];
    for (let i = 0; i < N; i++) {
      const dists = pts.map((q, j) => ({ j, d: j === i ? Infinity : pts[i].distanceTo(q) })).sort((a, b) => a.d - b.d);
      for (let k = 0; k < 2; k++) {
        const j = dists[k].j;
        if (j > i) seg.push(pts[i].x, pts[i].y, pts[i].z, pts[j].x, pts[j].y, pts[j].z);
      }
    }
    return { positions: pts, edges: new Float32Array(seg) };
  }, []);

  const pathPoints = useMemo(() => {
    const arr: number[] = [];
    for (let s = 0; s < PATH.length - 1; s++) {
      const a = new THREE.Vector3(...PATH[s].pos);
      const b = new THREE.Vector3(...PATH[s + 1].pos);
      for (let i = 0; i < 24; i++) {
        const v = a.clone().lerp(b, i / 24);
        v.y += Math.sin((i / 24) * Math.PI) * 0.18;
        arr.push(v.x, v.y, v.z);
      }
    }
    const last = PATH[PATH.length - 1].pos;
    arr.push(last[0], last[1], last[2]);
    return new Float32Array(arr);
  }, []);
  const totalPts = pathPoints.length / 3;

  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    const p = scroll.p.link;
    const m = nodes.current;
    if (m) {
      for (let i = 0; i < N; i++) {
        const q = positions[i];
        dummy.position.set(q.x, q.y + Math.sin(t * 0.6 + i) * 0.03, q.z);
        dummy.scale.setScalar(0.035 + 0.01 * Math.sin(t + i * 0.7));
        dummy.updateMatrix();
        m.setMatrixAt(i, dummy.matrix);
      }
      m.instanceMatrix.needsUpdate = true;
    }
    const draw = smooth(range(p, 0.15, 0.85));
    if (path.current) path.current.geometry.setDrawRange(0, Math.floor(totalPts * draw));
    for (let i = 0; i < PATH.length; i++) {
      const reached = smooth(range(draw, i / 3 - 0.1, i / 3 + 0.0001));
      const h = hops.current[i];
      if (h) {
        const mat = h.material as THREE.MeshStandardMaterial;
        mat.color.copy(DIM).lerp(i === PATH.length - 1 ? STAMP : RULE, reached);
        mat.emissive.copy(i === PATH.length - 1 ? STAMP : RULE);
        mat.emissiveIntensity = reached * (0.9 + 0.3 * Math.sin(t * 3 + i));
        h.scale.setScalar(0.07 + 0.06 * reached);
      }
      placeLabel(`hop-${i}`, anchors.current[i], state.camera, state.size, scroll.v.link > 0.4 && reached > 0.6);
    }
    void dt;
  });

  return (
    <group ref={group} position={isMobile ? [-0.9, 0.7, -0.5] : [0.4, 0, -0.5]} userData={{ baseScale: isMobile ? 0.68 : 1, baseY: isMobile ? 0.7 : 0 }}>
      <instancedMesh ref={nodes} args={[undefined, undefined, N]} frustumCulled={false}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshStandardMaterial color={PAPER} roughness={0.6} opacity={0.75} />
      </instancedMesh>
      <lineSegments frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[edges, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={PAPER} opacity={0.14} />
      </lineSegments>
      <threeLine ref={path} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[pathPoints, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={RULE} opacity={0.95} />
      </threeLine>
      {PATH.map((hop, i) => (
        <mesh key={hop.label} ref={(el) => {
                hops.current[i] = el;
              }} position={hop.pos}>
          <sphereGeometry args={[1, 20, 20]} />
          <meshStandardMaterial color={DIM} roughness={0.35} metalness={0.2} />
          <object3D
            ref={(el) => {
              anchors.current[i] = el;
            }}
            position={[0, 1.6, 0]}
          />
        </mesh>
      ))}
    </group>
  );
}
