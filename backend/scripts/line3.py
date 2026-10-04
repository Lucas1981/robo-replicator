import time
import urllib.request
from pathlib import Path

import numpy as np
from ikpy.chain import Chain

from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig


PORT = "COM5"
ROBOT_ID = "follower"

RATE = 50
DT = 1 / RATE
SPEED = 0.04  # m/s


# ============================================================
# ROBOT + URDF
# ============================================================

urdf = Path("so101_new_calib.urdf")

if not urdf.exists():
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/TheRobotStudio/"
        "SO-ARM100/main/Simulation/SO101/so101_new_calib.urdf",
        urdf,
    )

chain = Chain.from_urdf_file(
    str(urdf),
    base_elements=[
        "base_link",
        "shoulder_pan", "shoulder_link",
        "shoulder_lift", "upper_arm_link",
        "elbow_flex", "lower_arm_link",
        "wrist_flex", "wrist_link",
        "wrist_roll", "gripper_link",
        "gripper_frame_joint", "gripper_frame_link",
    ],
)

JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
]

chain.active_links_mask = np.array([
    link.name in JOINTS for link in chain.links
])

joint_indices = {
    joint: next(
        i for i, link in enumerate(chain.links)
        if link.name == joint
    )
    for joint in JOINTS
}


robot = SO101Follower(
    SO101FollowerConfig(
        port=PORT,
        id=ROBOT_ID,
        use_degrees=True,
    )
)

robot.connect()


# ============================================================
# FK
# ============================================================

def get_q():
    obs = robot.get_observation()

    q = np.zeros(len(chain.links))

    for joint in JOINTS:
        q[joint_indices[joint]] = np.deg2rad(
            obs[f"{joint}.pos"]
        )

    return q


def get_xyz():
    q = get_q()
    pose = chain.forward_kinematics(q)
    return pose[:3, 3].copy()


# ============================================================
# 1. APPRENTISSAGE DE LA FEUILLE
# ============================================================

robot.bus.disable_torque()

print("\n=== Calibration de la feuille ===")
print("Tu peux déplacer le bras à la main.\n")

input("Pointe sur HAUT GAUCHE puis Entrée")
TL = get_xyz()
print("TL =", TL)

input("Pointe sur HAUT DROITE puis Entrée")
TR = get_xyz()
print("TR =", TR)

input("Pointe sur BAS DROITE puis Entrée")
BR = get_xyz()
print("BR =", BR)

input("Pointe sur BAS GAUCHE puis Entrée")
BL = get_xyz()
print("BL =", BL)


# ============================================================
# REPERE DE LA FEUILLE
# ============================================================

def paper_point(u, v):
    """
    u = 0 -> gauche
    u = 1 -> droite

    v = 0 -> haut
    v = 1 -> bas
    """

    return (
        (1-u)*(1-v)*TL
        + u*(1-v)*TR
        + u*v*BR
        + (1-u)*v*BL
    )


# ============================================================
# Réactiver le robot sans saut brutal
# ============================================================

obs = robot.get_observation()

hold = {
    f"{joint}.pos": obs[f"{joint}.pos"]
    for joint in JOINTS
}

hold["gripper.pos"] = obs["gripper.pos"]

robot.send_action(hold)
robot.bus.enable_torque()

time.sleep(1)

q = get_q()


# ============================================================
# MOUVEMENT CARTESIEN SMOOTH
# ============================================================

def smoothstep(t):
    return 10*t**3 - 15*t**4 + 6*t**5


def move_xyz(start, end):
    global q

    distance = np.linalg.norm(end - start)

    duration = distance / SPEED

    steps = max(
        20,
        int(duration * RATE)
    )

    for t in np.linspace(0, 1, steps):

        a = smoothstep(t)

        xyz = start + a * (end - start)

        q = chain.inverse_kinematics(
            target_position=xyz,
            initial_position=q,
        )

        action = {
            f"{joint}.pos":
                float(np.rad2deg(q[joint_indices[joint]]))
            for joint in JOINTS
        }

        action["gripper.pos"] = obs["gripper.pos"]

        robot.send_action(action)

        time.sleep(DT)


# ============================================================
# 2. DESSIN TEST
# ============================================================

try:

    # Ligne horizontale au milieu de la feuille
    A = paper_point(0.2, 0.5)
    B = paper_point(0.8, 0.5)

    print("\nDébut dans 2 secondes...")
    time.sleep(2)

    move_xyz(A, B)

    print("Terminé")


except KeyboardInterrupt:
    print("Stop")


finally:
    robot.disconnect()