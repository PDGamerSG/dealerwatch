import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Environment, Lightformer, Preload } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { lowPower } from "../lib/motion";
import { Rig } from "./Rig";
import { Dust } from "./Dust";
import { Tape } from "./Tape";
import { Panels } from "./stations/Panels";
import { Sandwich } from "./stations/Sandwich";
import { Waveform } from "./stations/Waveform";
import { Graph } from "./stations/Graph";
import { Chain } from "./stations/Chain";
import { Ledger } from "./stations/Ledger";
import { Seal } from "./stations/Seal";

/**
 * One fixed canvas behind the page. Every station lives at the origin and
 * fades itself in and out from the scroll presence envelope, so the camera
 * never has to travel.
 */
export function Scene() {
  return (
    <div className="gl" aria-hidden>
      <Canvas
        dpr={[1, lowPower ? 1.25 : 1.6]}
        gl={{ antialias: !lowPower, powerPreference: "high-performance", alpha: false, stencil: false }}
        camera={{ fov: 34, near: 0.1, far: 60, position: [0, 0, 10] }}
        frameloop="always"
      >
        <color attach="background" args={["#070b14"]} />
        <fog attach="fog" args={["#070b14", 14, 30]} />
        <ambientLight intensity={0.35} />
        <directionalLight position={[4, 6, 6]} intensity={2.4} color="#fff4e2" />
        <directionalLight position={[-6, -2, 2]} intensity={0.9} color="#6fa8ff" />
        <Suspense fallback={null}>
          <Environment resolution={128} frames={1}>
            <Lightformer form="rect" intensity={3} position={[0, 5, -4]} scale={[10, 3, 1]} color="#fff2dc" />
            <Lightformer form="rect" intensity={1.4} position={[-6, 0, 2]} rotation-y={Math.PI / 2} scale={[6, 4, 1]} color="#6fa8ff" />
            <Lightformer form="rect" intensity={1.2} position={[6, -2, 2]} rotation-y={-Math.PI / 2} scale={[6, 4, 1]} color="#e9d7bb" />
          </Environment>
          <Rig />
          <Dust />
          <Tape />
          <Panels />
          <Sandwich />
          <Waveform />
          <Graph />
          <Chain />
          <Ledger />
          <Seal />
          <Preload all />
        </Suspense>
        {!lowPower && (
          <EffectComposer multisampling={0} enableNormalPass={false}>
            <Bloom luminanceThreshold={0.85} luminanceSmoothing={0.2} intensity={0.55} mipmapBlur radius={0.6} />
            <Vignette eskil={false} offset={0.18} darkness={0.75} />
          </EffectComposer>
        )}
      </Canvas>
    </div>
  );
}
