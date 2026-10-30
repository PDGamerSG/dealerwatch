import { extend, type ThreeElement } from "@react-three/fiber";
import * as THREE from "three";

/** `<line>` collides with the SVG element in JSX, so three's Line gets its own tag. */
class ThreeLine extends THREE.Line {}
extend({ ThreeLine });

declare module "@react-three/fiber" {
  interface ThreeElements {
    threeLine: ThreeElement<typeof ThreeLine>;
  }
}
