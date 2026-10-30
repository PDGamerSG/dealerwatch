import * as THREE from "three";

/**
 * DOM labels anchored to 3D objects without drei's Html portals. Sections
 * render the markup inside <LabelLayer>; stations call `placeLabel` each
 * frame with the anchor object and whether the label should be visible.
 */
const els = new Map<string, HTMLElement>();
const v = new THREE.Vector3();

export function registerLabel(id: string, el: HTMLElement | null) {
  if (el) els.set(id, el);
  else els.delete(id);
}

export function placeLabel(id: string, anchor: THREE.Object3D | null, camera: THREE.Camera, size: { width: number; height: number }, on: boolean) {
  const el = els.get(id);
  if (!el || !anchor) return;
  let visible = on;
  if (visible) {
    anchor.getWorldPosition(v).project(camera);
    if (v.z > 1) visible = false;
    else {
      const x = (v.x * 0.5 + 0.5) * size.width;
      const y = (-v.y * 0.5 + 0.5) * size.height;
      el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    }
  }
  const has = el.classList.contains("is-on");
  if (visible && !has) el.classList.add("is-on");
  else if (!visible && has) el.classList.remove("is-on");
}
