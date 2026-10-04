#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["opencv-python>=4.8", "openai>=1.40", "python-dotenv>=1.0"]
# ///
"""Snap a portrait with the USB webcam and turn it into a simple cartoon SVG.

The photo is sent to Kimi-K2.6 on Nebius Token Factory, which replies with a
playful, smiley-style line drawing as SVG: stroke-only paths, few lines, so the
SO-101 can later trace it with a pen.

    camera/portrait_<timestamp>.jpg   the captured photo
    image/portrait_<timestamp>.svg    the generated cartoon

Usage:
    cp .env.example .env   # then put your key in .env (git-ignored)
    uv run scripts/portrait_cartoon.py                    # preview, SPACE to snap
    uv run scripts/portrait_cartoon.py --no-preview       # snap after warm-up
    uv run scripts/portrait_cartoon.py --image camera/x.jpg   # skip the camera
    uv run scripts/portrait_cartoon.py --list-cameras
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAMERA_DIR = PROJECT_ROOT / "camera"
IMAGE_DIR = PROJECT_ROOT / "image"

# A real environment variable wins over .env.
load_dotenv(PROJECT_ROOT / ".env")

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "moonshotai/Kimi-K2.6"

# 1080p webcam; the driver falls back to its nearest supported mode.
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080
WARMUP_FRAMES = 20

CARTOON_PROMPT = """\
You are a cartoonist drawing for a robot arm that holds a single pen.

Look at this portrait photo and draw the person as a funny, super simple
cartoon, like a smiley-face doodle. Exaggerate for fun. Keep it friendly.

First write ONE line starting with "Features:" naming the 2 or 3 things that
make this person recognizable (hair shape and length, glasses, beard, hat...).
Then write the SVG.

Layout guide for the 512x512 canvas (y grows downward):
- Head: one closed oval centered near (256, 260), about 220 wide, 260 tall.
- Hair: outline it around the top and sides of the head, matching the photo.
- Eyes: two small dots or happy arcs at y = 240, x = 210 and x = 302.
- Glasses (only if worn): one ring around EACH eye plus a short bridge between.
- Nose: optional, one tiny curve near (256, 285).
- Mouth: a big smiling arc around y = 320, from x = 200 to x = 312.
- Do not draw a neck, body, or background.

SVG rules (strict):
- <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
- Use only <path> elements. Straight lines (M, L) and Bezier curves (C, Q) are fine.
- Every path: fill="none" stroke="black" stroke-width="4" stroke-linecap="round" stroke-linejoin="round".
- No fills, no text, no gradients, no images, no transforms, no <style>.
- At most 15 paths. Fewer, longer, continuous strokes are better.
- No markdown code fences.
"""


def list_cameras(max_index: int = 5) -> None:
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ok, frame = cap.read()
            size = f"{frame.shape[1]}x{frame.shape[0]}" if ok else "no frame"
            print(f"  camera {index}: {size}")
        cap.release()


def capture_portrait(camera_index: int, preview: bool) -> Path:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        sys.exit(
            f"Could not open camera {camera_index}. "
            "Try --list-cameras, and allow camera access for your terminal in "
            "System Settings > Privacy & Security > Camera."
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

    frame = None
    try:
        if preview:
            print("Preview open: SPACE to take the photo, Q or ESC to cancel.")
            while True:
                ok, frame = cap.read()
                if not ok:
                    sys.exit("Camera stopped sending frames.")
                cv2.imshow("Robotticelli - SPACE to snap", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord(" "):
                    break
                if key in (ord("q"), 27):
                    sys.exit("Cancelled.")
        else:
            # Let auto-exposure settle before keeping a frame.
            for _ in range(WARMUP_FRAMES):
                ok, frame = cap.read()
                time.sleep(0.03)
            if frame is None or not ok:
                sys.exit("Camera opened but returned no frame.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    CAMERA_DIR.mkdir(exist_ok=True)
    path = CAMERA_DIR / f"portrait_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    cv2.imwrite(str(path), frame)
    print(f"Saved photo: {path.relative_to(PROJECT_ROOT)} ({frame.shape[1]}x{frame.shape[0]})")
    return path


def encode_image(path: Path, max_side: int = 1024) -> str:
    """Downscale to keep the request small, return a JPEG data URL."""
    image = cv2.imread(str(path))
    if image is None:
        sys.exit(f"Could not read image: {path}")
    scale = max_side / max(image.shape[:2])
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        sys.exit(f"Could not encode image: {path}")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()


def extract_svg(text: str) -> str:
    match = re.search(r"<svg\b.*?</svg>", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("The model reply contained no <svg> element.")
    return match.group(0)


def cartoonize(photo: Path, model: str) -> Path:
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        sys.exit("Set NEBIUS_API_KEY in .env (see .env.example) or in your environment.")

    client = OpenAI(base_url=NEBIUS_BASE_URL, api_key=api_key)
    print(f"Asking {model} for a cartoon...")
    response = client.chat.completions.create(
        model=model,
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": encode_image(photo)}},
                    {"type": "text", "text": CARTOON_PROMPT},
                ],
            }
        ],
        # Kimi otherwise spends the whole token budget reasoning before the SVG.
        extra_body={"chat_template_kwargs": {"thinking": False}},
    )
    choice = response.choices[0]
    reply = choice.message.content or ""
    try:
        svg = extract_svg(reply)
    except ValueError as error:
        sys.exit(f"{error} (finish_reason={choice.finish_reason})\nReply was:\n{reply[:2000]}")

    IMAGE_DIR.mkdir(exist_ok=True)
    path = IMAGE_DIR / f"{photo.stem}.svg"
    path.write_text(svg + "\n", encoding="utf-8")
    print(f"Saved cartoon: {path.relative_to(PROJECT_ROOT)}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera-index", type=int, default=int(os.environ.get("CAMERA_INDEX", 0)),
                        help="OpenCV camera index of the USB webcam (default: $CAMERA_INDEX or 0)")
    parser.add_argument("--no-preview", action="store_true", help="Snap automatically without a preview window")
    parser.add_argument("--image", type=Path, help="Cartoonize this photo instead of using the camera")
    parser.add_argument("--model", default=os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL),
                        help=f"Nebius model id (default: $NEBIUS_MODEL or {DEFAULT_MODEL})")
    parser.add_argument("--list-cameras", action="store_true", help="Print available camera indices and exit")
    args = parser.parse_args()

    if args.list_cameras:
        list_cameras()
        return

    photo = args.image.resolve() if args.image else capture_portrait(args.camera_index, preview=not args.no_preview)
    cartoonize(photo, args.model)


if __name__ == "__main__":
    main()
