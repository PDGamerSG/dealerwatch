import * as THREE from "three";
import { rowText, tapeRows } from "../lib/tape-data";

/**
 * A long strip of printed tape: two lines of monospaced trade rows on
 * cream paper, with a faint red margin rule and perforation marks. The
 * texture repeats along the ribbon.
 */
export function makeTapeTexture(width = 4096, height = 256): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d")!;

  ctx.fillStyle = "#f2e9d8";
  ctx.fillRect(0, 0, width, height);

  // subtle paper mottle
  for (let i = 0; i < 2600; i++) {
    ctx.fillStyle = `rgba(90, 70, 40, ${Math.random() * 0.05})`;
    ctx.fillRect(Math.random() * width, Math.random() * height, 2 + Math.random() * 4, 1 + Math.random() * 2);
  }

  // perforation rows
  ctx.fillStyle = "#070b14";
  for (let x = 24; x < width; x += 48) {
    ctx.beginPath();
    ctx.arc(x, 18, 5, 0, Math.PI * 2);
    ctx.arc(x, height - 18, 5, 0, Math.PI * 2);
    ctx.fill();
  }

  // red margin rule
  ctx.strokeStyle = "rgba(230, 59, 46, 0.85)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, 46);
  ctx.lineTo(width, 46);
  ctx.stroke();

  const rows = tapeRows(40, 11);
  ctx.font = "500 34px 'IBM Plex Mono', Menlo, monospace";
  ctx.textBaseline = "middle";
  let x = 40;
  let i = 0;
  while (x < width + 400) {
    const r = rows[i % rows.length];
    const text = rowText(r);
    ctx.fillStyle = "#070b14";
    ctx.fillText(text, x, height * 0.42);
    ctx.fillStyle = r.side === "BUY" ? "rgba(230,59,46,0.9)" : "rgba(7,11,20,0.55)";
    ctx.font = "400 22px 'IBM Plex Mono', Menlo, monospace";
    ctx.fillText(`${r.side === "BUY" ? "bid" : "ask"} ${r.account}  lot ${r.qty}  nse`, x, height * 0.72);
    ctx.font = "500 34px 'IBM Plex Mono', Menlo, monospace";
    x += ctx.measureText(text).width + 110;
    i++;
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
}
