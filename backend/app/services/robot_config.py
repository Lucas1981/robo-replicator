import os

FPS = int(os.getenv("ROBOT_FPS", "30"))

HOME_POSE = {
    "shoulder_pan": float(os.getenv("ROBOT_HOME_SHOULDER_PAN", "0.0")),
    "shoulder_lift": float(os.getenv("ROBOT_HOME_SHOULDER_LIFT", "15.0")),
    "elbow_flex": float(os.getenv("ROBOT_HOME_ELBOW_FLEX", "50.0")),
    "wrist_flex": float(os.getenv("ROBOT_HOME_WRIST_FLEX", "-50.0")),
    "wrist_roll": float(os.getenv("ROBOT_HOME_WRIST_ROLL", "0.0")),
}

# Portrait A4 canvas (210 × 297 mm) staged vertically in front of the arm.
# Pan maps the short axis (width); lift maps the long axis (height).
CANVAS_WIDTH_MM = float(os.getenv("ROBOT_CANVAS_WIDTH_MM", "210.0"))
CANVAS_HEIGHT_MM = float(os.getenv("ROBOT_CANVAS_HEIGHT_MM", "297.0"))
CANVAS_ASPECT = CANVAS_WIDTH_MM / CANVAS_HEIGHT_MM

CANVAS_HALF_EXTENT_PAN = float(os.getenv("ROBOT_CANVAS_HALF_EXTENT_PAN", "12.0"))
CANVAS_HALF_EXTENT_LIFT = float(os.getenv("ROBOT_CANVAS_HALF_EXTENT_LIFT", "10.0"))

PEN_UP = float(os.getenv("ROBOT_PEN_UP", "10.0"))
PEN_DOWN = float(os.getenv("ROBOT_PEN_DOWN", "85.0"))

FRAMES_PEN_SETTLE = int(os.getenv("ROBOT_FRAMES_PEN_SETTLE", "5"))
MIN_DRAW_FRAMES = int(os.getenv("ROBOT_MIN_DRAW_FRAMES", "2"))
MIN_TRAVEL_FRAMES = int(os.getenv("ROBOT_MIN_TRAVEL_FRAMES", "2"))

# Constant end-effector speeds on the canvas (mm/s). Draw speed is arm-sketch pace;
# travel (pen up) is faster so repositioning does not dominate total time.
DRAW_SPEED_MM_S = float(os.getenv("ROBOT_DRAW_SPEED_MM_S", "60.0"))
TRAVEL_SPEED_MM_S = float(os.getenv("ROBOT_TRAVEL_SPEED_MM_S", "150.0"))
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
