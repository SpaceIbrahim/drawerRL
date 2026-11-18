# `model/`: the robot arm model

The 3D and physics model of the **Kinova Gen3 Lite** arm that the simulation is built on.

```
model/
└── kinova_gen3_lite/
    ├── gen3_lite.xml      ← the arm model the project loads
    ├── scene.xml          ← standalone demo scene (not used by the project)
    ├── assets/            ← 11 link meshes (.stl) + a picture
    ├── LICENSE            ← Kinova's BSD-3-Clause licence (must stay with the model)
    ├── README.md          ← where the model comes from
    └── CHANGELOG.md       ← upstream change history
```

> [!NOTE]
> There is **no drawer model file**. The cabinet, drawer and handle are generated in code by
> [`drawer_rl/drawer_builder.py`](../drawer_rl/README.md#drawer_builderpy) from the measurements in
> [`configs/drawer.yaml`](../configs/README.md#draweryaml-the-cabinet-drawer-and-handle).

## Where it comes from

The model is from **[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)**, Google DeepMind's
collection of robot models. It was converted from Kinova's official robot description. The upstream
[`kinova_gen3_lite/README.md`](kinova_gen3_lite/README.md) describes how, and that file is kept unchanged.

It has been checked against the real arm: in the lab on 2026-11-17, Kinova's own forward kinematics and this model
agreed to **0.00 mm** at 30 arm poses, and the tool frame, Home pose, speed limits and masses matched.

## Files

### `kinova_gen3_lite/gen3_lite.xml`: the arm (MJCF)

The file `configs/robot.yaml` points to (`mjcf_path`). It describes:

| Part | Details |
|---|---|
| **6 arm joints** | `joint_1` … `joint_6`, with their limits (e.g. joint 4 ±150°, which limits clockwise drawer rotations) |
| **Arm motors** | Position actuators `a_joint_1` … `a_joint_6` with gains and torque limits |
| **Gripper** | Two fingers, each with a base and tip link. A single motor (`a_gripper`) drives `right_finger_bottom_joint`; the other finger joints are coupled to it, so the gripper is under-actuated like the real one |
| **Tool frame** | `tool_frame` body and the `ee_site` at the gripper. The project's tool tip is `ee_site` + 8 mm forward (`robot.yaml` → `tcp.offset`) |
| **Geometry** | Visual meshes for looks, collision meshes for contacts, with contact softness and friction defaults |
| **Keyframes** | `home`, `retract`, `open`, `close`. `scene_builder.py` removes them, because adding the drawer joint makes them the wrong length |

The project **doesn't edit this file**. Changes it needs are applied when the world is built, from `robot.yaml`
(`actuator_overrides`: the gripper's damping and grip-force limit), so the original stays identical to upstream.

### `kinova_gen3_lite/assets/`

| File | Part of the arm |
|---|---|
| `base_link.stl` | Base (bolted to the mount) |
| `shoulder_link.stl` | Shoulder (turns with joint 1) |
| `arm_link.stl` | Upper arm (joint 2) |
| `forearm_link.stl` | Forearm (joint 3) |
| `lower_wrist_link.stl`, `upper_wrist_link.stl` | Wrist (joints 4–6) |
| `gripper_base_link.stl` | Gripper body |
| `left_finger_prox_link.stl`, `left_finger_dist_link.stl` | Left finger: base and tip |
| `right_finger_prox_link.stl`, `right_finger_dist_link.stl` | Right finger: base and tip |
| `gen3_lite.png` | Picture of the model, used by the upstream README |

`gen3_lite.xml` finds the meshes through `meshdir="assets/"`.

### `kinova_gen3_lite/scene.xml`

A minimal upstream scene (the arm on a floor with lights) for viewing the arm on its own in MuJoCo's viewer.
The project doesn't use it: `drawer_rl/scene_builder.py` builds its own world around `gen3_lite.xml`.

### `LICENSE`, `README.md`, `CHANGELOG.md`

Upstream files. The **licence is BSD-3-Clause, © Kinova inc.**, and requires the copyright notice to stay with the
model, so keep it whenever the model is copied or redistributed.

## Looking at it

The arm inside the full project world:

```bash
.venv/bin/python scripts/build_scene.py --view
```

The arm on its own:

```bash
.venv/bin/python -m mujoco.viewer --mjcf=model/kinova_gen3_lite/scene.xml
```
