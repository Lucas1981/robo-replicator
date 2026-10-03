# Robotticelli — the bot-based art replicator

This repository turns a photo into vector drawing paths that a Hugging Face SO-101 arm can eventually trace. The current pipeline covers image upload, OpenAI-powered outline generation, bitmap-to-SVG vectorization, and sample robot playback datasets.

## Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- An [OpenAI API key](https://platform.openai.com/api-keys) with access to the image edit API (`gpt-image-1`)

## Setup

### 1. Python environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Backend configuration

Copy the example env file and add your API key:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_IMAGE_MODEL=gpt-image-1
DEBUG_SKIP_LLM_STEP=false
DEBUG_SKIP_VECTORIZE_STEP=false
```

Only `backend/.env.example` is committed. `backend/.env` is gitignored and must be created locally on each machine.

`OPENAI_IMAGE_MODEL` defaults to `gpt-image-1`. Some accounts no longer support `dall-e-2` for image edits; if you hit model errors, keep `gpt-image-1`.

#### Debug mode (skip expensive steps)

While working on later pipeline stages, enable debug flags to avoid costly or slow steps:

```env
DEBUG_SKIP_LLM_STEP=true
DEBUG_SKIP_VECTORIZE_STEP=true
```

| Flag | When `true` | Sample file used |
|------|-------------|------------------|
| `DEBUG_SKIP_LLM_STEP` | Skips OpenAI outline generation | `backend/resources/outline-sample.png` |
| `DEBUG_SKIP_VECTORIZE_STEP` | Skips bitmap-to-SVG conversion | `backend/resources/paths-sample.svg` |

The API still validates uploads. `/api/process` returns an SVG path file (`{name}-paths.svg`). Regenerate the paths sample after updating the outline sample:

```bash
python backend/scripts/generate_paths_sample.py
```

Check active flags: `curl http://127.0.0.1:8000/api/health`

### 3. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Run locally

Use two terminals.

**Terminal 1 — API** (logs stay in this window):

```bash
source .venv/bin/activate
./backend/run.sh
```

The API listens at http://127.0.0.1:8000. Interactive docs: http://127.0.0.1:8000/docs

**Terminal 2 — web UI**:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173, upload an image, click **Process file**, then **Download** the SVG paths file. With both debug flags off, processing usually takes 30–90 seconds; with both debug flags on it returns immediately.

The frontend proxies `/api` to the backend, so both must be running.

## Sample robot outputs

These scripts live under `samples/` and do not require the web app:

| Script | Purpose |
|--------|---------|
| `samples/viz-sample.sh` | Joint-plot replay in Rerun |
| `samples/viz-sample-urdf.sh` | 3D SO-101 URDF replay in Rerun |
| `samples/replay-sample.sh` | Replay on a physical SO-101 via `lerobot-replay` |

Generate the square sample dataset:

```bash
source .venv/bin/activate
pip install 'lerobot[dataset]'   # first time only
python scripts/generate_square_dataset.py
```

Replay on hardware:

```bash
SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ./samples/replay-sample.sh
```

## Project layout

```
backend/          FastAPI API (image validation, OpenAI outline generation)
backend/resources/  Sample assets (outline-sample.png, paths-sample.svg)
frontend/         React upload UI
scripts/          Dataset generators and URDF visualizer
samples/          Example LeRobot datasets and helper scripts
```

## Roadmap

- [x] Upload interface for source images
- [x] LLM connection to produce a cartoon-style outline
- [x] Convert the outline to vector paths
- [ ] Map paths to SO-101 joint movements
- [ ] Export robot-ready command files
