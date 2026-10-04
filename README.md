# Slide

https://claude.ai/artifact/J4whwPnUjDR6cakT5ZgBmG

# Robotticelli

Turn a photo into SVG drawing paths and an SO-101 replay dataset.

**Web pipeline:** upload or webcam capture → OpenAI outline → SVG paths → LeRobot zip

## Setup

- Python 3.12+, Node.js 18+, [OpenAI API key](https://platform.openai.com/api-keys) with `gpt-image-1` image edits

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-robot.txt   # robot dataset export only
cp backend/.env.example backend/.env           # set OPENAI_API_KEY
cd frontend && npm install && cd ..
```

## Run

```bash
./backend/run.sh              # terminal 1 — http://127.0.0.1:8000
cd frontend && npm run dev    # terminal 2 — http://localhost:5173
```

In the UI: **Take photo** or **Choose file** → **Process file** → **Download SVG** or **Generate robot dataset**.

Processing usually takes 30–90 seconds with debug flags off.

## Outputs

| Step | API | File |
|------|-----|------|
| Vector paths | `POST /api/process` | `{name}-paths.svg` |
| Robot replay | `POST /api/robot-dataset` | `{name}-draw.zip` |

Unzip the robot zip, then:

```bash
./replay-virtual.sh                                          # Rerun 3D SO-101 arm preview
SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ID ./replay-follower.sh
```

## Debug mode

In `backend/.env`, set flags to `true` to skip slow or costly steps:

| Flag | Skips | Sample used |
|------|-------|-------------|
| `DEBUG_SKIP_LLM_STEP` | OpenAI outline | `backend/resources/outline-sample.png` |
| `DEBUG_SKIP_VECTORIZE_STEP` | Bitmap → SVG | `backend/resources/paths-sample.svg` |
| `DEBUG_SKIP_ROBOT_STEP` | SVG → dataset | `backend/resources/draw-sample.zip` |

`curl http://127.0.0.1:8000/api/health` — check active flags.

Regenerate samples: `python backend/scripts/generate_paths_sample.py` and `python backend/scripts/generate_robot_sample.py`

## Helper scripts

| Script | Purpose |
|--------|---------|
| `scripts/viz-complete-output-example.sh` | 3D URDF preview of checked-in pipeline output |
| `samples/replay-sample.sh` | Replay the square demo on hardware |
| `backend/scripts/generate_robot_dataset.py` | Convert an SVG to a dataset offline |

## Vin: portrait cartoon (Nebius / Kimi)

Webcam portrait to smiley-style line-art SVG via `scripts/portrait_cartoon.py`. Uses root `.env` with `NEBIUS_API_KEY` (see `.env.example`).

- **Web app:** **Take photo** saves the capture to `camera/` (`POST /api/portrait/photo`); **Sketch with Vin** saves the cartoon to `image/` (`POST /api/portrait/cartoon`) and feeds it to the robot dataset step.
- **CLI:** `scripts/portrait-cartoon.sh` (preview window, SPACE to snap).
