# Running the scripts

What each script in `scripts/` does and how to run it.

## Before you start

Run everything from the project folder with the project's Python:

```bash
cd /home/space/workspace/drawerRL
```

Every command below starts with `.venv/bin/python`.

* **`--help`** on any script lists all its options.
* **`--set key=value`** (most scripts) changes any config value for that one run, without editing the YAML files.
  Example: `--set drawer.top_drawer.slide.damping=12 task.reward.weights.grasp=2.0`.
* **Old runs (v1–v7) need two extra overrides.** Their saved configs point at `configs/placement_map.yaml`, which
  is now the v8 map, so they refuse to start. Add this to any script that loads an old run (`evaluate`,
  `policy_report`, `eval_distance`, `audit_policy`, `make_media`):

  ```
  --set task.randomization.placement_map=configs/placement_map_v6.yaml task.randomization.validate_reachability=false
  ```

## Typical order of use

1. `build_scene.py --view` and `scripted_demo.py`: check the world works.
2. `check_reachability.py --map`: only after changing the table, mount, drawer or robot.
3. `train.py`: train a policy.
4. `evaluate.py --viewer`, `policy_report.py`, `audit_policy.py`: check the policy.
5. `real/rehearse.py`: rehearse the real-robot loop in simulation.
6. `vision/` scripts ① → ⑥: set up the real camera.

---

## 1. Look at the simulated world

### `build_scene.py`: build the world and look at it

Builds the table, robot mount, arm and cabinet from the configs.

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/build_scene.py --view` | Opens the interactive 3D viewer. You can grab and drag the drawer with the mouse |
| `.venv/bin/python scripts/build_scene.py` | Saves `generated/scene.xml` and preview pictures (`generated/preview_*.png`) |
| `.venv/bin/python scripts/build_scene.py --view --set drawer.top_drawer.front_height=0.135` | Look at the world with a changed setting |

Use it to check that a config change (e.g. a re-measured drawer) looks right.

### `scripted_demo.py`: prove the task is physically possible

A hand-written controller (no AI) reaches the handle, grasps it and pulls the drawer open. If this fails, the
physics or the setup is broken, not the RL. It prints the phase, grasp and opening every 10 steps.

```bash
.venv/bin/python scripts/scripted_demo.py --viewer
```

| Option | What it does |
|---|---|
| `--viewer` | Watch it live in the 3D viewer, in real time. The window stays open at the end until you close it |
| `--video file.mp4` | Save a video of the attempt instead (can't be combined with `--viewer`) |
| `--offset 0.08 0 0` | Put the drawer 8 cm farther away (x y z in metres, from the nominal placement) |
| `--seed N` | A different random setup |
| `--set ...` | Change config values |

### `check_reachability.py`: where can the drawer be placed?

Checks which drawer placements the arm can physically open. Each placement is tested for IK along the whole pull,
joint-limit margins, singularities, collisions, table fit and a full-physics scripted pull.

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/check_reachability.py --map` | **Rebuilds `configs/placement_map.yaml`** (distance × rotation). Required after changing the table, mount, drawer or robot settings, or training refuses to start. Slow: hundreds of placements, each with a physics test |
| `.venv/bin/python scripts/check_reachability.py` | Sweeps distance only and plots the feasible band (default plot: `docs/media/reachability.png`; change with `--plot`) |
| `.venv/bin/python scripts/check_reachability.py --verify-range -0.06 0.09` | Checks every corner of a planned distance range |

Map options: `--yaw-min`, `--yaw-max`, `--yaw-step` (degrees), `--map-out` (output file).

### `render_real_table.py`: pictures of the lab-table setup

```bash
.venv/bin/python scripts/render_real_table.py
```

Writes `docs/media/real_table_overview.png` and `real_table_layout.png`. Documentation only, no options.

---

## 2. Train

### `train.py`: train a policy

```bash
.venv/bin/python scripts/train.py --name sac_real_v8
```

About 2 hours for 1M steps on the laptop. Everything is saved to `runs/<name>/`: the best model, final model,
checkpoints every 100k steps, TensorBoard logs and a frozen copy of every config. Ctrl+C (or `kill <pid>`) stops it
and saves.

| Option | What it does |
|---|---|
| `--name X` | Run folder name (default: `sac_<date>_<time>`) |
| `--set train.total_timesteps=300000` | Change any setting; `train.` keys go to `train.yaml`, the rest to the world configs |
| `--resume runs/X` | Continue a stopped run where it left off |
| `--init-from runs/X` | Start a new run from another run's weights. Only works if the observation and action haven't changed (v7 → v8 can't) |
| `--set train.seed=1` | A different random seed, to check the result repeats |
| `--env-dir runs/X/configs` | Train in exactly the world an older run used |

Watch training progress, then open the address it prints in a browser:

```bash
.venv/bin/tensorboard --logdir runs
```

---

## 3. Test a trained policy in simulation

### `evaluate.py`: run a policy and watch it

This is the script for **running a previous policy on the simulated robot**. It rebuilds the exact world the run was
trained in (from `runs/<run>/configs/`), loads the model and lets it control the arm.

```bash
.venv/bin/python scripts/evaluate.py runs/sac_real_v8 --which best --viewer
```

For an old run, add the overrides from "Before you start":

```bash
.venv/bin/python scripts/evaluate.py runs/sac_audit_fix_v7 --which best --viewer --set task.randomization.placement_map=configs/placement_map_v6.yaml task.randomization.validate_reachability=false
```

| Option | What it does |
|---|---|
| `--which best` / `final` | The best-scoring model, or the last one (default: `final`) |
| `--viewer` | Watch it live in the 3D viewer, in real time |
| `--video generated/eval.mp4` | Save the first 3 episodes as a video |
| `--episodes N` | How many attempts (default 20). Prints success and opening for each, then the success rate |
| `--stochastic` | Keep the training randomness on (normally off) |
| `--set ...` | Test the same policy in a changed world, e.g. a stiffer drawer |

### `policy_report.py`: behaviour statistics

Grasp rate, time to first grasp, time to open, final opening, collisions, sideways drift while pulling.

```bash
.venv/bin/python scripts/policy_report.py runs/sac_real_v8 --which best --episodes 50
```

### `eval_distance.py`: success rate across drawer positions

Runs the policy with the drawer pinned at each distance (and optionally rotation) and plots the success rate.
It can compare several runs.

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/eval_distance.py runs/sac_real_v8 --plot generated/distance.png` | Success vs distance (`--xmin`, `--xmax`, `--step` in metres) |
| `.venv/bin/python scripts/eval_distance.py runs/sac_real_v8 --grid --step 0.03 --yaws -15 -10 -5 0 5 10 15 --plot generated/grid.png` | Distance × rotation grid |
| `.venv/bin/python scripts/eval_distance.py runs/A runs/B --labels old new --plot generated/compare.png` | Compare two policies |

`--episodes N` sets attempts per position (default 10).

### `audit_policy.py`: check for cheating and unrealistic behaviour

Checks whether the results are physically realistic:
- speed against the real arm's limit;
- joint torques against their limits;
- sideways force on the handle;
- joint-limit margins;
- whether the policy really uses what it sees (it corrupts the inputs and checks success drops);
- stress tests (latency, friction, grip force, noise).

```bash
.venv/bin/python scripts/audit_policy.py runs/sac_real_v8 --which best
```

Slow: 200 nominal episodes plus 40 per scenario. `--scenarios nominal handle_bias_10mm` runs only some scenarios,
`--episodes N` and `--nominal-episodes N` change the counts, and `--out` sets the output folder (default
`docs/audit/`). v8 targets: handle side load < 8 N and joints at the torque limit < 5 % of steps.

### `make_media.py`: videos, GIFs and curves for reports

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/make_media.py runs/sac_real_v8 --offsets 0 -0.06 --yaws 0 10 --name v8` | Video (two camera views + status text), GIF and keyframes, one segment per drawer offset/rotation |
| `.venv/bin/python scripts/make_media.py --curves runs/sac_real_v8` | Training-curves plot from one or more runs |

Writes to `docs/media/`. `--steps N` sets how many steps each segment shows (default 70).

---

## 4. Rehearse the real-robot loop (in simulation)

### `real/rehearse.py`: dress rehearsal of deployment

Runs the actual deploy code (`drawer_deploy/`: kinematic twin, controller, safety monitor, finishing routine)
against a simulated arm. Only the connection to the real Kinova is replaced. Prints the outcome of each attempt and
a summary.

```bash
.venv/bin/python scripts/real/rehearse.py --agent runs/sac_real_v8 --episodes 20
```

| Option | What it does |
|---|---|
| `--agent scripted` / `probe` / `runs/X` | Hand-written vision-guided fallback, test motions, or a trained policy (default: `scripted`) |
| `--vision` | Get the drawer state from the simulated camera + the real vision pipeline, with a deliberately slightly-wrong calibration (`--calib-err-mm`, `--calib-err-deg`) |
| `--stage approach` / `grasp` / `full` / `probe` | Rehearse one stage of the staged real-arm test |
| `--speed-scale 0.3` | Slow everything down, as for first real tests |
| `--world-set ...` | Change only the simulated "real world", not what the agent believes, e.g. `task.randomization.slide_friction_scale=[3,3]` |
| `--deploy-set ...` | Change `configs/deploy.yaml` values (safety limits, stages) |
| `--latency-steps N` | Command delay of the simulated arm in 50 ms periods (default 1) |
| `--video file.mp4`, `--log-dir`, `--json` | Save a video, per-tick logs or a summary |

---

## 5. Vision pipeline (camera + ArUco tags)

All vision scripts accept:
- `--source mujoco` to run against the **simulated** ZED (no hardware needed). The default is the real ZED;
  `uvc` uses it as a plain webcam and `replay` plays back recordings.
- `--no-gui` to run without opening windows.
- `--set ...` to change vision config values, e.g. `markers.drawer.0.size=0.068`.

Listed in real-setup order.

### ① `vision/generate_markers.py`: make printable tags

```bash
.venv/bin/python scripts/vision/generate_markers.py
```

Writes PDFs and PNGs of every tag and the ChArUco board to `printables/` (`--out` to change, `--dpi 600` for higher
resolution). Print at 100 % ("actual size"), then measure the black square with a ruler and correct
`configs/vision/markers.yaml` if it differs.

### ② `vision/plan_camera.py`: choose where to put the camera stand

Tries many camera positions in simulation, with the arm grasping and pulling, and ranks them by how well the tags
are seen.

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/vision/plan_camera.py --top 5 --images` | Search positions around the drawer; save pictures of the best 5 |
| `.venv/bin/python scripts/vision/plan_camera.py --pos 0.0 -0.6 0.8 --lookat 0.5 0 0.35` | Score one specific position (robot base frame, metres) |

### ③ `vision/calibrate_intrinsics.py`: lens calibration

Only needed when the ZED is used as a plain USB webcam (`--source uvc`). The ZED SDK already has factory calibration.

```bash
.venv/bin/python scripts/vision/calibrate_intrinsics.py --source uvc
```

Hold the ChArUco board at different distances and angles: SPACE adds a view, `c` calibrates. `--auto N` adds a view
every N frames; `--from-folder <dir>` calibrates from saved images.

### ④ `vision/calibrate_extrinsics.py`: where the camera is relative to the robot

Redo it every time the camera stand moves. The script **never moves the robot**: you jog it with the Kinova app or
joystick.

| Command | Method |
|---|---|
| `.venv/bin/python scripts/vision/calibrate_extrinsics.py --method hand_eye` | A tag on the gripper; jog the arm to ~15 poses (most accurate) |
| `.venv/bin/python scripts/vision/calibrate_extrinsics.py --method base_markers` | Tags placed at measured spots on the table |
| `.venv/bin/python scripts/vision/calibrate_extrinsics.py --method touch_points` | Touch tag centres (or `--points corners`) with the gripper tip |
| `.venv/bin/python scripts/vision/calibrate_extrinsics.py --solve <dataset folder>` | Re-solve a saved dataset without the camera |
| `.venv/bin/python scripts/vision/calibrate_extrinsics.py --method base_markers --source mujoco` | Dry run in simulation |

The result is saved to `calibration/extrinsics.yaml` (`--out` to change, `--yes` to save without asking).

### ⑤ `vision/setup_scene.py`: the setup wizard

Run each session, or after moving the drawer. It:
- checks the camera, tag visibility and calibration;
- records the closed-drawer reference;
- checks the measured opening against a ruler;
- tells you whether the drawer is inside the region the policy was trained for.

| Command | What it does |
|---|---|
| `.venv/bin/python scripts/vision/setup_scene.py` | Interactive, on the real camera |
| `.venv/bin/python scripts/vision/setup_scene.py --source mujoco --sim-truth --auto` | Dry run in simulation, no questions |

### ⑥ `vision/live_view.py`: watch the pipeline work

Shows the camera image with detected tags, handle position and drawer opening, and prints the drawer state.

```bash
.venv/bin/python scripts/vision/live_view.py --source mujoco
```

Keys: `q` quit, `s` save snapshot, `o` / `c` open / close the drawer (simulation only).
`--video file.mp4 --frames 300` records 300 frames to a video.

### `vision/record.py`: record camera frames for offline testing

```bash
.venv/bin/python scripts/vision/record.py --name drawer_test --frames 200 --every 3
```

Saves frames (plus depth and intrinsics) so you can test later without the camera, using `--source replay`.
`--no-depth` skips depth.

### `vision/_common.py`

Not a script: shared setup (paths, the common options above) that the vision scripts import.

---

## 6. Other

### `export_sim2real_repo.sh`: update the standalone sim2real repo

```bash
scripts/export_sim2real_repo.sh ../gen3lite-sim2real
```

Copies `sim2real/` and everything it needs into the standalone repo used on the lab laptop. Re-run after changing
the simulation, then commit and push there.

### The sim2real mirror tool (not in `scripts/`)

Runs the real arm and the simulated arm side by side. It's a module, so it runs with `-m`. A dry run with a
simulated stand-in arm:

```bash
.venv/bin/python -m sim2real.mirror --real fake drive pull --start rl_start
```

See [sim2real/README.md](../sim2real/README.md).
