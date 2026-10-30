import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import glsl from "vite-plugin-glsl";

export default defineConfig({
  base: "./",
  plugins: [react(), glsl({ minify: true })],
  resolve: { dedupe: ["three"] },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1200,
    rolldownOptions: {
      output: {
        advancedChunks: {
          groups: [
            { name: "three", test: /node_modules[\\/]three[\\/]/ },
            { name: "r3f", test: /node_modules[\\/](@react-three|postprocessing|n8ao|maath|troika|zustand|its-fine|suspend-react)/ },
            { name: "motion", test: /node_modules[\\/](gsap|@gsap|lenis)[\\/]/ },
          ],
        },
      },
    },
  },
});
