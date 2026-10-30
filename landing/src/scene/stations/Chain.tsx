import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { isMobile, range } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { RULE } from "../palette";
import { firstMesh, modelUrl, useStation } from "../useStation";

export const LINKS = 9;
const PITCH = 1.46;
const TRAVEL = PITCH * (LINKS - 1);

const elastic = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1);

/**
 * Nine metal links snap into a chain, one per evidence check, sliding in
 * step with the horizontal cards below.
 */
export function Chain() {
  const { nodes } = useGLTF(modelUrl("chain_link"));
  const geometry = useMemo(() => firstMesh(nodes as Record<string, THREE.Object3D>).geometry, [nodes]);
  const { group } = useStation("chain", { lift: 0.3 });
  const slider = useRef<THREE.Group>(null);
  const links = useRef<(THREE.Mesh | null)[]>([]);

  useFrame((state) => {
    const p = scroll.p.chain;
    const t = state.clock.elapsedTime;
    if (slider.current) {
      slider.current.position.x = (isMobile ? 0 : 1.2) - p * TRAVEL;
      slider.current.rotation.y = 0.28 + Math.sin(t * 0.3) * 0.03;
    }
    for (let i = 0; i < LINKS; i++) {
      const m = links.current[i];
      if (!m) continue;
      const local = range(p, (i - 0.2) / (LINKS + 0.4), (i + 1.1) / (LINKS + 0.4));
      const s = elastic(Math.min(1, local * 1.6));
      m.scale.setScalar(Math.max(0.0001, s));
      m.position.y = (1 - Math.min(1, local * 1.6)) * 1.4;
      m.rotation.x = (i % 2) * (Math.PI / 2) + (1 - s) * 0.8;
      const mat = m.material as THREE.MeshStandardMaterial;
      const current = Math.abs(p * (LINKS - 1) - i) < 0.6 ? 1 : 0;
      mat.emissiveIntensity += (current * 0.55 - mat.emissiveIntensity) * 0.1;
    }
  });

  return (
    <group ref={group} position={[0, isMobile ? 2.0 : -0.62, 0]} userData={{ baseScale: isMobile ? 0.5 : 0.84, baseY: isMobile ? 2.0 : -0.62 }}>
      <group ref={slider}>
        {Array.from({ length: LINKS }, (_, i) => (
          <mesh key={i} ref={(el) => {
                links.current[i] = el;
              }} geometry={geometry} position={[i * PITCH, 0, 0]} scale={0.0001}>
            <meshStandardMaterial color="#d9cdb6" metalness={0.95} roughness={0.26} envMapIntensity={1.3} emissive={RULE} emissiveIntensity={0} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

useGLTF.preload(modelUrl("chain_link"));
