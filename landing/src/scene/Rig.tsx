import { useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { damp } from "../lib/motion";
import { scroll } from "../lib/scroll";

/** Camera leans a little toward the pointer; scroll velocity adds a gentle roll. */
export function Rig() {
  const state = useThree();
  useEffect(() => {
    if (import.meta.env.DEV) (window as unknown as { __dw: unknown }).__dw = state;
  }, [state]);
  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      scroll.pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      scroll.pointer.y = -((e.clientY / window.innerHeight) * 2 - 1);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);
  useFrame(({ camera }, dt) => {
    const px = scroll.pointer.x;
    const py = scroll.pointer.y;
    camera.position.x = damp(camera.position.x, px * 0.35, 2.5, dt);
    camera.position.y = damp(camera.position.y, py * 0.25, 2.5, dt);
    camera.rotation.z = damp(camera.rotation.z, -scroll.velocity * 0.00035, 3, dt);
    camera.lookAt(0, 0, 0);
  });
  return null;
}
