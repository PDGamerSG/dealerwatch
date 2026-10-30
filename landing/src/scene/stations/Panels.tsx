import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { isMobile, lowPower, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { placeLabel } from "../../lib/labels";
import { firstMesh, modelUrl, useStation } from "../useStation";

const LABELS = ["Recorder", "Blotter", "KYC"];
const X = isMobile ? 0 : 1.7;

/** Three frosted panels drift apart, then stack into one as you scroll. */
export function Panels() {
  const { nodes } = useGLTF(modelUrl("slab"), false, false);
  const geometry = useMemo(() => firstMesh(nodes as Record<string, THREE.Object3D>).geometry, [nodes]);
  const { group } = useStation("gap");
  const slabs = useRef<(THREE.Mesh | null)[]>([]);
  const anchors = useRef<(THREE.Object3D | null)[]>([]);
  const cur = useRef([0, 0, 0]);

  useFrame((state, dt) => {
    const p = smooth(scroll.p.gap);
    const t = state.clock.elapsedTime;
    for (let i = 0; i < 3; i++) {
      const m = slabs.current[i];
      if (!m) continue;
      const spread = (i - 1) * (isMobile ? 1.5 : 2.05);
      cur.current[i] += (p - cur.current[i]) * Math.min(1, dt * 5);
      const k = cur.current[i];
      m.position.x = X + spread * (1 - k) + Math.sin(t * 0.6 + i) * 0.05 * (1 - k);
      m.position.z = (i - 1) * 0.42 * k;
      m.position.y = Math.sin(t * 0.8 + i * 2) * 0.08 * (1 - k) + (i - 1) * 0.06 * k;
      m.rotation.y = (i - 1) * 0.55 * (1 - k) + Math.sin(t * 0.4 + i) * 0.03;
      m.rotation.z = (i - 1) * 0.08 * (1 - k);
      placeLabel(`panel-${i}`, anchors.current[i], state.camera, state.size, scroll.v.gap > 0.3);
    }
  });

  return (
    <group ref={group} position={[0, 0, 0]} userData={{ baseScale: 1, baseY: 0 }}>
      {LABELS.map((label, i) => (
        <mesh key={label} ref={(el) => {
                slabs.current[i] = el;
              }} geometry={geometry} scale={isMobile ? 0.8 : 1.15}>
          {lowPower ? (
            <meshStandardMaterial color="#f2e9d8" roughness={0.6} metalness={0.05} opacity={0.6} />
          ) : (
            <meshPhysicalMaterial
              color="#f2e9d8"
              transmission={0.72}
              thickness={0.9}
              roughness={0.42}
              ior={1.4}
              envMapIntensity={1.1}
              attenuationColor="#e8d8b8"
              attenuationDistance={2.2}
            />
          )}
          <object3D
            ref={(el) => {
              anchors.current[i] = el;
            }}
            position={[0, 0.72, 0.1]}
          />
        </mesh>
      ))}
    </group>
  );
}

useGLTF.preload(modelUrl("slab"), false, false);
