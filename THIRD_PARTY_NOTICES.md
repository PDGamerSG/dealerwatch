# Third-party notices

DealerWatch includes open-source packages and self-hosted font files. The lock files record the versions installed for the build. This document identifies the direct runtime and build dependencies and their upstream license terms. Each package remains under its own license.

## Python dependencies

| Package | License | Upstream |
|---|---|---|
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Starlette | BSD-3-Clause | https://github.com/encode/starlette |
| Pydantic | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| NetworkX | BSD-3-Clause | https://github.com/networkx/networkx |
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy |
| HTTPX | BSD-3-Clause | https://github.com/encode/httpx |
| python-multipart | Apache-2.0 | https://github.com/Kludex/python-multipart |
| OpenAI Python client | MIT | https://github.com/openai/openai-python |
| Anthropic Python client | MIT | https://github.com/anthropics/anthropic-sdk-python |
| AnyIO | MIT | https://github.com/agronholm/anyio |
| Click | BSD-3-Clause | https://github.com/pallets/click |

The complete transitive dependency set is pinned in `requirements.lock` and `uv.lock`.

## Frontend dependencies

| Package | License | Upstream |
|---|---|---|
| React and React DOM | MIT | https://github.com/facebook/react |
| Vite | MIT, with notices for bundled dependencies | https://github.com/vitejs/vite/blob/main/LICENSE.md |
| Three.js | MIT, with notices for included example assets | https://github.com/mrdoob/three.js/blob/dev/LICENSE |
| React Three Fiber | MIT | https://github.com/pmndrs/react-three-fiber |
| Drei | MIT | https://github.com/pmndrs/drei |
| React Three Postprocessing | MIT | https://github.com/pmndrs/react-postprocessing |
| Lenis | MIT | https://github.com/darkroomengineering/lenis |
| Zustand | MIT | https://github.com/pmndrs/zustand |
| GSAP | GreenSock standard no-charge license | https://gsap.com/standard-license |
| `@gsap/react` | GreenSock standard no-charge license | https://gsap.com/standard-license |
| TypeScript | Apache-2.0 | https://github.com/microsoft/TypeScript |
| `@vitejs/plugin-react` | MIT | https://github.com/vitejs/vite-plugin-react |
| `vite-plugin-glsl` | MIT | https://github.com/UstymUkhman/vite-plugin-glsl |

The complete frontend dependency tree is pinned in `landing/package-lock.json`.

## Fonts

The landing page and console ship subsets from these packages:

- Archivo Variable from `@fontsource-variable/archivo`, licensed under the SIL Open Font License 1.1: https://scripts.sil.org/OFL
- IBM Plex Mono from `@fontsource/ibm-plex-mono`, licensed under the SIL Open Font License 1.1: https://scripts.sil.org/OFL

The font package license files remain available under `landing/node_modules` during development. The distributed font subsets are used under the OFL terms.

## Declared reusable material

`toolkit/asr.py` contains a small Sarvam speech-to-text adapter. Its WAV-windowing and response-shaping helpers were adapted from the MIT-licensed Kyun project by Team Vulcan, as recorded in [DECLARED_COMPONENTS.md](DECLARED_COMPONENTS.md). `toolkit/grounding.py` follows the validation idea described there and was rewritten for this project.

The Sarvam API is an optional external service. It is not bundled with the repository. A user who enables it must use their own account, credentials, and applicable Sarvam terms: https://www.sarvam.ai/

## Project-owned material

The DealerWatch application, synthetic data generator, evaluation scenarios, static console, landing-page source, diagrams, and scripts in this repository were written for the project unless a notice above says otherwise. The repository does not include customer records, confidential source data, or provider credentials.
