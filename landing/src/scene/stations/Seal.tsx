import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { isMobile, range, smooth } from "../../lib/motion";
import { scroll } from "../../lib/scroll";
import { STAMP } from "../palette";
import { firstMesh, modelUrl, useStation } from "../useStation";

/** A brass seal descends, presses, and leaves a red mark behind. */
export function Seal() {
  const { nodes } = useGLTF(modelUrl("seal"));
  const geometry = useMemo(() => firstMesh(nodes as Record<string, THREE.Object3D>).geometry, [nodes]);
  const { group } = useStation("decide");
  const seal = useRef<THREE.Mesh>(null);
  const mark = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const p = scroll.p.decide;
    const t = state.clock.elapsedTime;
    const down = smooth(range(p, 0.1, 0.48));
    const press = 1 - Math.abs(range(p, 0.44, 0.56) * 2 - 1); // 0 → 1 → 0 around the press
    const up = smooth(range(p, 0.56, 0.8));
    if (seal.current) {
      const y = 2.4 - down * 2.2 + up * 1.2 + Math.sin(t * 0.8) * 0.04 * up;
      seal.current.position.y = y;
      seal.current.rotation.y = t * 0.25 * (1 - down) + down * 0.4;
      seal.current.scale.set(1, 1 - press * 0.18, 1);
    }
    if (mark.current) {
      const on = smooth(range(p, 0.5, 0.6));
      mark.current.scale.setScalar(0.8 + 0.2 * on);
      const mat = mark.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = on * (1.6 + Math.sin(t * 3) * 0.2);
      mat.userData.maxOpacity = 1;
      mat.opacity = Math.min(mat.opacity, on);
    }
  });

  return (
    <group ref={group} position={isMobile ? [0, 1.4, 0] : [3.0, -0.6, 0]} rotation={[0.55, -0.35, 0]} userData={{ baseScale: isMobile ? 0.6 : 0.9, baseY: isMobile ? 1.4 : -0.6 }}>
      <mesh ref={seal} geometry={geometry} scale={1}>
        <meshStandardMaterial color="#c9a76a" metalness={0.92} roughness={0.32} envMapIntensity={1.4} />
      </mesh>
      <mesh ref={mark} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[0.72, 0.84, 96]} />
        <meshStandardMaterial color={STAMP} emissive={STAMP} emissiveIntensity={0} side={THREE.DoubleSide} opacity={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <ringGeometry args={[1.0, 1.6, 96]} />
        <meshBasicMaterial color="#141c30" opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

useGLTF.preload(modelUrl("seal"));
