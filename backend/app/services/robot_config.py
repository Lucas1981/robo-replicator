import os

FPS = int(os.getenv("ROBOT_FPS", "30"))

HOME_POSE = {
    "shoulder_pan": float(os.getenv("ROBOT_HOME_SHOULDER_PAN", "0.0")),
    "shoulder_lift": float(os.getenv("ROBOT_HOME_SHOULDER_LIFT", "15.0")),
    "elbow_flex": float(os.getenv("ROBOT_HOME_ELBOW_FLEX", "50.0")),
    "wrist_flex": float(os.getenv("ROBOT_HOME_WRIST_FLEX", "-50.0")),
    "wrist_roll": float(os.getenv("ROBOT_HOME_WRIST_ROLL", "0.0")),
}

CANVAS_HALF_EXTENT_PAN = float(os.getenv("ROBOT_CANVAS_HALF_EXTENT_PAN", "12.0"))
CANVAS_HALF_EXTENT_LIFT = float(os.getenv("ROBOT_CANVAS_HALF_EXTENT_LIFT", "10.0"))

PEN_UP = float(os.getenv("ROBOT_PEN_UP", "10.0"))
PEN_DOWN = float(os.getenv("ROBOT_PEN_DOWN", "85.0"))

FRAMES_TRAVEL = int(os.getenv("ROBOT_FRAMES_TRAVEL", "15"))
FRAMES_PEN_SETTLE = int(os.getenv("ROBOT_FRAMES_PEN_SETTLE", "5"))
FRAMES_PER_UNIT = float(os.getenv("ROBOT_FRAMES_PER_UNIT", "15.0"))
MIN_DRAW_FRAMES = int(os.getenv("ROBOT_MIN_DRAW_FRAMES", "2"))
CANVAS_MARGIN = float(os.getenv("ROBOT_CANVAS_MARGIN", "0.05"))
BEZIER_SAMPLES = int(os.getenv("ROBOT_BEZIER_SAMPLES", "12"))

JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

DATASET_FEATURES = {
    "action": {
        "dtype": "float32",
        "shape": (6,),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
    "observation.state": {
        "dtype": "float32",
        "shape": (6,),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
}
