"""Interactive terminal menu for the SO-101 follower arm.

Run from ~/lerobot so the venv has lerobot installed:
    .venv/bin/python ~/Documents/coding/tech_maker_hackaton_2026/arm_repo/arm.py

To try the menu without the arm, add --sim: a simulated arm accepts every
command at real speed, and paper setup writes to a scratch copy so the real
draw_area.json is never touched.

Pick a mode, then its options. Ctrl+C during a mode stops it and the arm
returns to its start pose; Ctrl+C at a menu goes back (or quits at the top).
The arm connects the first time a mode needs it and stays connected until you quit.
"""
import os
import shutil
import subprocess
import sys
import types

from dance import PORT, dance, make_robot
from draw import FONT, SHAPES, Plan, teach, text_strokes
from image_draw import DETAIL, IMAGES_DIR, METHODS, ImageDrawError, ai_available, image_to_strokes, list_images
from luck import LuckError, engines, lucky_subject, prompt_to_strokes
from moves import angry_cat, load_moves

BOLD, DIM, CYAN, YELLOW, RED, RESET = "\033[1m", "\033[2m", "\033[36m", "\033[33m", "\033[31m", "\033[0m"

BANNER = rf"""{CYAN}{BOLD}
  ░█▀▄░█▀█░█▀▄░█▀█░▀█▀░▀█▀░▀█▀░█▀▀░█▀▀░█░░░█░░░▀█▀
  ░█▀▄░█░█░█▀▄░█░█░░█░░░█░░░█░░█░░░█▀▀░█░░░█░░░░█░
  ░▀░▀░▀▀▀░▀▀░░▀▀▀░░▀░░░▀░░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀
{RESET}{DIM}  La Machine: a robotics hackathon by Tech Makers{RESET}
"""


CREDITS = "  A project made by Antoine, Daniel, Ilai, Lucas, Shaikha and Takako."


class SimRobot:
    """Stands in for the SO-101 with --sim: remembers the last pose it was sent."""

    def __init__(self):
        from dance import JOINTS
        self.config = types.SimpleNamespace(max_relative_target=10.0)
        self.bus = types.SimpleNamespace(enable_torque=lambda *a, **k: None, disable_torque=lambda *a, **k: None)
        self.pose = {j: 0.0 for j in JOINTS}
        self.commands = 0

    def get_observation(self):
        return {f"{j}.pos": v for j, v in self.pose.items()}

    def send_action(self, action):
        self.commands += 1
        self.pose = {j: action.get(f"{j}.pos", v) for j, v in self.pose.items()}
        return action

    def disconnect(self):
        print(f"{DIM}[sim] {self.commands} commands sent to the simulated arm{RESET}")


class Arm:
    """Connects to the arm on first use and keeps the connection open."""

    def __init__(self, sim: bool = False):
        self.robot = None
        self.sim = sim

    def get(self):
        if self.robot is None and self.sim:
            self.robot = SimRobot()
        if self.robot is None:
            if not os.path.exists(PORT):
                raise ConnectionError(f"Arm not found at {PORT}. Is the USB cable plugged in?")
            print(f"{DIM}Connecting to the arm...{RESET}")
            robot = make_robot()
            robot.connect(calibrate=False)
            self.robot = robot
        return self.robot

    def close(self):
        if self.robot is not None:
            self.robot.disconnect()
            self.robot = None


# ---------- small input helpers ----------

def clear():
    print("\033[2J\033[H", end="")


def choose(title: str, options: list[str], back: str = "Back", footer: str = "") -> int | None:
    """Show a numbered menu. Returns the chosen index, or None for back/quit."""
    print(f"{BOLD}{title}{RESET}\n")
    for i, label in enumerate(options, 1):
        print(f"  {CYAN}{i}{RESET}  {label}")
    print(f"  {CYAN}0{RESET}  {back}\n")
    if footer:
        print(f"{DIM}{footer}{RESET}\n")
    while True:
        try:
            raw = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        if raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"{YELLOW}Type a number from 0 to {len(options)}.{RESET}")


def ask_number(prompt: str, default: float, lo: float, hi: float, integer: bool = False) -> float:
    while True:
        raw = input(f"{prompt} {DIM}[{default:g}]{RESET}: ").strip()
        if not raw:
            return default
        try:
            value = int(raw) if integer else float(raw)
        except ValueError:
            print(f"{YELLOW}Not a number.{RESET}")
            continue
        if lo <= value <= hi:
            return value
        print(f"{YELLOW}Pick something between {lo:g} and {hi:g}.{RESET}")


def pause():
    try:
        input(f"\n{DIM}Press Enter to go back to the menu.{RESET}")
    except (KeyboardInterrupt, EOFError):
        print()


# ---------- modes ----------

# (label, loops, speed, scale)
DANCE_PRESETS = [
    ("Gentle   small, slow moves - good first run", 1, 0.7, 0.5),
    ("Groove   the normal dance, twice", 2, 1.0, 1.0),
    ("Party    bigger and faster, until Ctrl+C", 0, 1.3, 1.2),
]


def dance_mode(arm: Arm):
    while True:
        clear()
        print(BANNER)
        labels = [p[0] for p in DANCE_PRESETS] + ["Custom   choose loops, speed and size"]
        pick = choose("DANCE MODE", labels)
        if pick is None:
            return
        if pick < len(DANCE_PRESETS):
            _, loops, speed, scale = DANCE_PRESETS[pick]
        else:
            print()
            loops = ask_number("How many times? (0 = until Ctrl+C)", 2, 0, 100, integer=True)
            speed = ask_number("Speed (0.3 slow - 1.5 fast)", 1.0, 0.3, 1.5)
            scale = ask_number("Size of the moves (0.3 small - 1.3 big)", 1.0, 0.3, 1.3)
        print(f"\n{BOLD}Dancing!{RESET} {DIM}Ctrl+C to stop.{RESET}\n")
        dance(arm.get(), loops, speed, scale)
        pause()


# (label, rounds, speed)
CAT_PRESETS = [
    ("Grumpy   5 rounds, a little slower", 5, 0.75),
    ("Furious  full speed, until Ctrl+C", 0, 1.0),
]
CAT_MAX_STEP = 25.0  # the sweep needs a looser per-step cap to swipe hard enough


def angry_cat_mode(arm: Arm):
    while True:
        clear()
        print(BANNER)
        labels = [p[0] for p in CAT_PRESETS] + ["Custom   choose rounds and speed"]
        pick = choose("ANGRY CAT MODE  -  stare... then swipe things off the table", labels)
        if pick is None:
            return
        if pick < len(CAT_PRESETS):
            _, rounds, speed = CAT_PRESETS[pick]
        else:
            print()
            rounds = ask_number("How many rounds? (0 = until Ctrl+C)", 5, 0, 100, integer=True)
            speed = ask_number("Speed (0.3 slow - 1.0 full)", 0.75, 0.3, 1.0)
        moves = load_moves()
        robot = arm.get()
        print(f"\n{BOLD}Mrrrow.{RESET} {DIM}Ctrl+C to stop.{RESET}\n")
        robot.config.max_relative_target = CAT_MAX_STEP
        try:
            angry_cat(robot, moves, rounds, speed)
        finally:
            robot.config.max_relative_target = 10.0
        pause()


# Per-tool drawing settings. height: 0 = the taught touch poses, 1 = hover height, higher = lighter.
# bottom_lift: extra height added towards the bottom of the paper, where the arm sits closer
# to it and presses harder. The brush needs a lighter touch: pressing spreads its bristles.
TOOLS = {
    "pen": {"height": 0.5, "bottom_lift": 0.0, "speed": 0.03},
    "brush": {"height": 0.6, "bottom_lift": 0.25, "speed": 0.025},
}
DRAW = {"tool": "brush"}


def tool() -> dict:
    return TOOLS[DRAW["tool"]]


def tool_summary() -> str:
    t = tool()
    return f"{DRAW['tool']}, height {t['height']:g}, +{t['bottom_lift']:g} at bottom"
SIMPLE_SHAPES = ["square", "heart", "star"]
# Size names -> fraction of the paper. Small and central keeps the pen from tilting.
SHAPE_SIZES = [("Small", 0.25), ("Medium", 0.35), ("Large", 0.5)]
WORD_SIZES = [("Small", 0.4), ("Medium", 0.55), ("Large", 0.7)]
MAX_WORD = 6


def pick_size(sizes: list) -> float | None:
    pick = choose("How big?", [name for name, _ in sizes])
    return None if pick is None else sizes[pick][1]


def open_file(path) -> None:
    """Open a file in the desktop's default viewer without blocking the menu."""
    subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def confirm_and_draw(arm: Arm, raw: list, size: float, title: str, preview=None):
    """Check the drawing against the paper, then draw it (optionally tracing in the air first)."""
    try:
        t = tool()
        plan = Plan(raw, size, t["speed"], t["height"], t["bottom_lift"])
    except ValueError as e:
        print(f"\n{RED}{e}{RESET}")
        pause()
        return
    while True:
        clear()
        print(BANNER)
        print(f"{BOLD}{title}{RESET}  {DIM}{plan.summary()}, {tool_summary()}{RESET}")
        if plan.tilt_warning():
            print(f"{YELLOW}{plan.tilt_warning()}{RESET}")
        print()
        options = ["Draw it", "Trace it in the air first (pen never touches)"]
        if preview:
            print(f"{DIM}Preview: {preview}{RESET}\n")
            options.append("Open the preview image")
        pick = choose("Ready?", options)
        if pick is None:
            return
        if pick == 2:
            open_file(preview)
            continue
        air = pick == 1
        print(f"\n{BOLD}{'Tracing in the air' if air else 'Drawing'}...{RESET} {DIM}Ctrl+C to stop and lift the pen.{RESET}\n")
        plan.run(arm.get(), air=air)
        if not air:
            pause()
            return
        pause()


def simple_drawing(arm: Arm):
    clear()
    print(BANNER)
    pick = choose("SIMPLE DRAWING", [s.capitalize() for s in SIMPLE_SHAPES])
    if pick is None:
        return
    print()
    size = pick_size(SHAPE_SIZES)
    if size is None:
        return
    name = SIMPLE_SHAPES[pick]
    confirm_and_draw(arm, SHAPES[name](), size, name.capitalize())


def write_word(arm: Arm):
    clear()
    print(BANNER)
    print(f"{BOLD}WRITE A WORD{RESET}  {DIM}up to {MAX_WORD} letters, A-Z and !  (empty = back){RESET}\n")
    while True:
        try:
            word = input("Word: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if not word:
            return
        bad = sorted(set(word) - set(FONT))
        if bad:
            print(f"{YELLOW}Can't write {''.join(bad)!r}. Use letters A-Z and !.{RESET}")
        elif len(word.replace(" ", "")) > MAX_WORD:
            print(f"{YELLOW}Too long - {MAX_WORD} letters max.{RESET}")
        else:
            break
    print()
    size = pick_size(WORD_SIZES)
    if size is None:
        return
    confirm_and_draw(arm, text_strokes(word), size, f'"{word}"')


IMAGE_SIZES = [("Small", 0.3), ("Medium", 0.45), ("Large", 0.6)]


def draw_image(arm: Arm):
    clear()
    print(BANNER)
    images = list_images()
    if not images:
        print(f"{BOLD}DRAW AN IMAGE{RESET}\n")
        print(f"No images yet. Put a .jpg or .png in:\n  {IMAGES_DIR}")
        pause()
        return
    pick = choose(f"DRAW AN IMAGE  {DIM}from {IMAGES_DIR}{RESET}", [p.name for p in images])
    if pick is None:
        return
    image = images[pick]

    ai_ok, ai_reason = ai_available()
    names = list(METHODS)
    labels = [METHODS[m] + ("" if m != "ai" or ai_ok else f"  {DIM}- not set up: {ai_reason}{RESET}") for m in names]
    print()
    pick = choose("How should it turn the image into lines?", labels)
    if pick is None:
        return
    method = names[pick]
    if method == "ai" and not ai_ok:
        print(f"\n{YELLOW}AI outline isn't set up: {ai_reason}.")
        print(f"Add OPENAI_API_KEY to lucas_repo/backend/.env, or pick another way.{RESET}")
        pause()
        return

    print()
    details = ["simple", "medium", "detailed"]
    pick = choose("How much detail?", [f"{d.capitalize():9s} up to {DETAIL[d][3]} lines" for d in details])
    if pick is None:
        return
    detail = details[pick]
    print()
    size = pick_size(IMAGE_SIZES)
    if size is None:
        return

    print(f"\n{DIM}Turning {image.name} into lines...{RESET}")
    try:
        strokes, preview = image_to_strokes(image, method, detail)
    except (ImageDrawError, RuntimeError, OSError) as e:
        print(f"\n{RED}{e}{RESET}")
        pause()
        return
    confirm_and_draw(arm, strokes, size, image.name, preview=preview)


LUCK_ENGINES = [
    ("claude", "Claude draws it    clean vector lines, about 10-20 s"),
    ("openai", "OpenAI paints it   then it gets vectorized, about 30-60 s"),
]


def try_your_luck(arm: Arm):
    clear()
    print(BANNER)
    status = engines()
    labels = [label + ("" if status[e][0] else f"  {DIM}- not set up: {status[e][1]}{RESET}") for e, label in LUCK_ENGINES]
    pick = choose("TRY YOUR LUCK!  -  who makes the picture?", labels)
    if pick is None:
        return
    engine = LUCK_ENGINES[pick][0]
    if not status[engine][0]:
        key = "ANTHROPIC_API_KEY" if engine == "claude" else "OPENAI_API_KEY"
        print(f"\n{YELLOW}{engine.capitalize()} isn't set up: {status[engine][1]}.")
        print(f"Export {key}, or add it to lucas_repo/backend/.env.{RESET}")
        pause()
        return

    print()
    try:
        subject = input(f"What should it draw? {DIM}(Enter = surprise me){RESET}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return
    if not subject:
        subject = lucky_subject()
        print(f"\n{BOLD}Your luck: {subject}!{RESET}")
    print()
    size = pick_size(IMAGE_SIZES)
    if size is None:
        return

    print()
    try:
        strokes, preview = prompt_to_strokes(subject, engine)
    except (LuckError, ImageDrawError, RuntimeError, OSError) as e:
        print(f"\n{RED}{e}{RESET}")
        pause()
        return
    confirm_and_draw(arm, strokes, size, subject, preview=preview)


def set_up_paper(arm: Arm):
    clear()
    print(BANNER)
    print(f"{BOLD}SET UP THE PAPER{RESET}\n")
    print("Do this whenever the paper or the pen has moved. You'll teach 9 points")
    print("(corners, edge middles, centre) with the pen tip lightly touching the paper,")
    print("then one pose about 2 cm above the centre.\n")
    if choose("Start?", ["Yes, turn the torque off - I'm holding the arm"]) is None:
        return
    robot = arm.get()
    try:
        teach(robot, 3)
    finally:
        robot.bus.enable_torque()  # hold the parking pose again
    pause()


def tool_and_pressure(arm: Arm):
    while True:
        clear()
        print(BANNER)
        t = tool()
        print("Height: 0 = the taught touch poses, 1 = hover height (in the air). Higher = lighter.")
        print("Faint or missing lines -> lower it. Thick or pressed lines -> raise it.")
        print("Bottom lift: extra height towards the bottom of the paper, where the arm presses harder.\n")
        pick = choose(f"TOOL & PRESSURE  {DIM}now: {tool_summary()}{RESET}", [
            "Use the pen" + ("    (selected)" if DRAW["tool"] == "pen" else ""),
            "Use the brush" + ("  (selected)" if DRAW["tool"] == "brush" else ""),
            f"Height           now {t['height']:g}",
            f"Bottom lift      now {t['bottom_lift']:g}",
        ])
        if pick is None:
            return
        if pick in (0, 1):
            DRAW["tool"] = ["pen", "brush"][pick]
        elif pick == 2:
            t["height"] = ask_number(f"{DRAW['tool'].capitalize()} height", t["height"], -0.3, 0.95)
        else:
            t["bottom_lift"] = ask_number("Bottom lift", t["bottom_lift"], 0.0, 0.6)


def drawing_mode(arm: Arm):
    options = [
        ("Simple drawing    square, heart or star", simple_drawing),
        (f"Write a word      up to {MAX_WORD} letters", write_word),
        ("Draw an image     from the images/ folder", draw_image),
        ("Try your luck!    AI draws whatever you ask", try_your_luck),
        ("Set up the paper  teach it where the paper is", set_up_paper),
        ("Tool & pressure", tool_and_pressure),
    ]
    while True:
        clear()
        print(BANNER)
        labels = [label for label, _ in options]
        labels[5] = f"Tool & pressure   now: {tool_summary()}"
        pick = choose("DRAWING MODE", labels)
        if pick is None:
            return
        options[pick][1](arm)


MODES = [
    ("Dance mode", dance_mode),
    ("Angry Cat mode", angry_cat_mode),
    ("Drawing mode", drawing_mode),
]


def main():
    sim = "--sim" in sys.argv
    if sim:
        global BANNER
        BANNER += f"{YELLOW}{BOLD}  SIMULATION - no arm connected{RESET}\n"
        # Paper setup in sim would save the simulated arm's poses as the paper: use a scratch copy.
        import draw
        sim_area = IMAGES_DIR / "processed" / "sim_draw_area.json"
        sim_area.parent.mkdir(parents=True, exist_ok=True)
        if draw.AREA_FILE.exists():  # fresh copy of the real paper each run
            shutil.copy(draw.AREA_FILE, sim_area)
        draw.AREA_FILE = sim_area
    arm = Arm(sim)
    try:
        while True:
            clear()
            print(BANNER)
            pick = choose("What should the arm do?", [m[0] for m in MODES], back="Quit", footer=CREDITS)
            if pick is None:
                break
            try:
                MODES[pick][1](arm)
            except (ConnectionError, ValueError) as e:
                print(f"\n{RED}{e}{RESET}")
                pause()
    finally:
        arm.close()
        print("Bye!")


if __name__ == "__main__":
    sys.exit(main())
