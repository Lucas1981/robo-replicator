# Robotticelli — the bot-based art replicator

This repository turns a photo into vector drawing paths and optionally a LeRobot replay dataset for a Hugging Face SO-101 arm. The pipeline covers image upload, OpenAI-powered outline generation, bitmap-to-SVG vectorization, and a separate SVG-to-robot-dataset export step.

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
DEBUG_SKIP_ROBOT_STEP=false
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
| `DEBUG_SKIP_ROBOT_STEP` | Skips SVG-to-LeRobotDataset export | `backend/resources/draw-sample.zip` |

`/api/process` returns an SVG path file (`{name}-paths.svg`). `/api/robot-dataset` accepts that SVG and returns a LeRobotDataset zip (`{name}-draw.zip`) for `lerobot-replay`.

Regenerate sample assets after updating the outline sample:

```bash
python backend/scripts/generate_paths_sample.py
python backend/scripts/generate_robot_sample.py
```

Robot dataset export requires LeRobot:

```bash
pip install -r backend/requirements-robot.txt
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

Open http://localhost:5173, upload an image, click **Process file**, then **Download SVG** or **Generate robot dataset**. With all debug flags off, image processing usually takes 30–90 seconds; with all debug flags on both steps return immediately.

The frontend proxies `/api` to the backend, so both must be running.

## Sample robot outputs

These scripts live under `samples/` and do not require the web app:

| Script | Purpose |
|--------|---------|
| `samples/viz-sample.sh` | Joint-plot replay in Rerun |
| `samples/viz-sample-urdf.sh` | 3D SO-101 URDF replay in Rerun |
| `samples/replay-sample.sh` | Replay the square sample on a physical SO-101 |
| `samples/replay-draw.sh` | Replay any generated `*-draw` dataset on hardware |
| `scripts/viz-complete-output-example.sh` | Visualize the checked-in full pipeline output (SO-101 URDF + joints) in Rerun |

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

Convert an SVG path file to a dataset offline:

```bash
python backend/scripts/generate_robot_dataset.py backend/resources/paths-sample.svg --output /tmp/my_draw
```

Replay a downloaded dataset (unzip `{name}-draw.zip` first):

```bash
SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ./samples/replay-draw.sh /path/to/extracted_draw_folder
```

## Vin: portrait → cartoon (webcam + Kimi-K2.6)

Snap a portrait with the USB webcam and let Kimi-K2.6 (Nebius Token Factory) turn it into a simple, smiley-style line drawing. The model replies with stroke-only SVG paths, which is the vector format the drawing pipeline needs.

```bash
cp .env.example .env                         # put your Nebius Token Factory key in .env
scripts/portrait-cartoon.sh                  # preview window, SPACE to snap
scripts/portrait-cartoon.sh --no-preview
scripts/portrait-cartoon.sh --image camera/portrait_20261003_181500.jpg
scripts/portrait-cartoon.sh --list-cameras   # if the webcam isn't index 0
```

Photos go to `camera/`, cartoons to `image/`. Those and `.env` are git-ignored. On a shared machine, delete `.env` (and the photos) when you're done.

## Project layout

```
backend/          FastAPI API (image validation, OpenAI outline generation)
backend/resources/  Sample assets and complete-output-example LeRobotDataset
frontend/         React upload UI
scripts/          Dataset generators and URDF visualizer
samples/          Example LeRobot datasets and helper scripts
```

## Roadmap

- [x] Upload interface for source images
- [x] LLM connection to produce a cartoon-style outline
- [x] Convert the outline to vector paths
- [x] Map paths to SO-101 joint movements
- [x] Export robot-ready command files (LeRobotDataset v3.0 zip via `/api/robot-dataset`)
