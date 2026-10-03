# Robotticelli — the bot-based art replicator

This repository turns a photo into a simple outline drawing that a Hugging Face SO-101 arm can eventually trace. The current pipeline covers image upload, OpenAI-powered outline generation, and sample robot playback datasets.

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
```

Only `backend/.env.example` is committed. `backend/.env` is gitignored and must be created locally on each machine.

`OPENAI_IMAGE_MODEL` defaults to `gpt-image-1`. Some accounts no longer support `dall-e-2` for image edits; if you hit model errors, keep `gpt-image-1`.

#### Debug mode (skip OpenAI)

While working on later pipeline stages, you can avoid costly LLM calls by setting:

```env
DEBUG_SKIP_LLM_STEP=true
```

When enabled, `/api/process` skips outline generation and returns the bundled sample at `backend/resources/outline-sample.png` instead. The API still validates your upload; only the OpenAI step is bypassed.

Set `DEBUG_SKIP_LLM_STEP=false` when you want real outline generation again. Optionally point at a different file with `DEBUG_OUTLINE_SAMPLE_PATH`.

Check whether debug mode is active: `curl http://127.0.0.1:8000/api/health` returns `"debug_skip_llm_step": true` or `false`.

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

Open http://localhost:5173, upload an image, click **Process file**, then **Download** when the outline is ready. With OpenAI enabled, processing usually takes 30–90 seconds; with `DEBUG_SKIP_LLM_STEP=true` it returns immediately.

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
backend/resources/  Sample assets (e.g. outline-sample.png for debug mode)
frontend/         React upload UI
scripts/          Dataset generators and URDF visualizer
samples/          Example LeRobot datasets and helper scripts
```

## Roadmap

- [x] Upload interface for source images
- [x] LLM connection to produce a cartoon-style outline
- [ ] Convert the outline to vector paths
- [ ] Map paths to SO-101 joint movements
- [ ] Export robot-ready command files
