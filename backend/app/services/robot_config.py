import os

FPS = int(os.getenv("ROBOT_FPS", "30"))

HOME_POSE = {
    "shoulder_pan": float(os.getenv("ROBOT_HOME_SHOULDER_PAN", "0.0")),
    "shoulder_lift": float(os.getenv("ROBOT_HOME_SHOULDER_LIFT", "15.0")),
    "elbow_flex": float(os.getenv("ROBOT_HOME_ELBOW_FLEX", "50.0")),
    "wrist_flex": float(os.getenv("ROBOT_HOME_WRIST_FLEX", "-50.0")),
    "wrist_roll": float(os.getenv("ROBOT_HOME_WRIST_ROLL", "0.0")),
}

# Extended seed for IK — arm reaches forward over the canvas instead of folding back.
REACH_POSE = {
    "shoulder_pan": float(os.getenv("ROBOT_REACH_SHOULDER_PAN", "0.0")),
    "shoulder_lift": float(os.getenv("ROBOT_REACH_SHOULDER_LIFT", "15.0")),
    "elbow_flex": float(os.getenv("ROBOT_REACH_ELBOW_FLEX", "50.0")),
    "wrist_flex": float(os.getenv("ROBOT_REACH_WRIST_FLEX", "-55.0")),
    "wrist_roll": float(os.getenv("ROBOT_REACH_WRIST_ROLL", "0.0")),
}

# Portrait A4 pad laid flat (horizontal) in front of the arm.
# u: left → right. v: near → far (SVG top → bottom).
CANVAS_ORIENTATION = "horizontal"
CANVAS_WIDTH_MM = float(os.getenv("ROBOT_CANVAS_WIDTH_MM", "210.0"))
CANVAS_HEIGHT_MM = float(os.getenv("ROBOT_CANVAS_HEIGHT_MM", "297.0"))
CANVAS_ASPECT = CANVAS_WIDTH_MM / CANVAS_HEIGHT_MM

# Near edge of the pad is offset from the robot base by this fraction of A4 length.
CANVAS_NEAR_OFFSET_FRACTION = float(os.getenv("ROBOT_CANVAS_NEAR_OFFSET_FRACTION", "0.8"))
# Extra clearance (mm) added beyond the fraction above — keeps strokes away from the folded workspace.
CANVAS_BASE_CLEARANCE_MM = float(os.getenv("ROBOT_CANVAS_BASE_CLEARANCE_MM", "25.0"))
# Skip the closest strip of the canvas (0–1 on the near→far axis) to avoid base-proximal poses.
CANVAS_V_NEAR_FRACTION = float(os.getenv("ROBOT_CANVAS_V_NEAR_FRACTION", "0.12"))
CANVAS_PLANE_Z_MM = float(os.getenv("ROBOT_CANVAS_PLANE_Z_MM", "35.0"))
# Weight for gripper-down orientation after the position-only IK pass.
IK_ORIENTATION_WEIGHT = float(os.getenv("ROBOT_IK_ORIENTATION_WEIGHT", "0.05"))

FRAMES_PATH_SETTLE = int(os.getenv("ROBOT_FRAMES_PATH_SETTLE", "5"))
MIN_DRAW_FRAMES = int(os.getenv("ROBOT_MIN_DRAW_FRAMES", "2"))
MIN_TRAVEL_FRAMES = int(os.getenv("ROBOT_MIN_TRAVEL_FRAMES", "2"))

DRAW_SPEED_MM_S = float(os.getenv("ROBOT_DRAW_SPEED_MM_S", "60.0"))
TRAVEL_SPEED_MM_S = float(os.getenv("ROBOT_TRAVEL_SPEED_MM_S", "150.0"))
# Raise the pen this far above the canvas plane during inter-stroke travel (mm, via arm IK — not gripper).
TRAVEL_LIFT_MM = float(os.getenv("ROBOT_TRAVEL_LIFT_MM", "15.0"))
CANVAS_MARGIN = float(os.getenv("ROBOT_CANVAS_MARGIN", "0.05"))
BEZIER_SAMPLES = int(os.getenv("ROBOT_BEZIER_SAMPLES", "12"))

ARM_JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]

JOINT_NAMES = list(ARM_JOINT_NAMES)

DATASET_FEATURES = {
    "action": {
        "dtype": "float32",
        "shape": (len(JOINT_NAMES),),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
    "observation.state": {
        "dtype": "float32",
        "shape": (len(JOINT_NAMES),),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
}
