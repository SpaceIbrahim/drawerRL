# `runs/`: trained policies

`scripts/train.py` writes each training run into its own folder here. Full runs are large (checkpoints and replay
buffers reach several GB), so **the repository includes only what's needed to run one policy**:

```
runs/
└── sac_audit_fix_v7/
    ├── best/
    │   ├── best_model.zip     ← the trained neural network (6.1 MB)
    │   └── vecnormalize.pkl   ← its input scaling (required to run it)
    └── configs/
        ├── robot.yaml   drawer.yaml   scene.yaml   task.yaml   ← the world it was trained in
        └── train.yaml                                          ← how it was trained (SAC)
```

## `sac_audit_fix_v7`: the included policy

| | |
|---|---|
| What it does | Reaches the handle, grasps it and pulls the drawer at least 15 cm open, with the drawer at different distances and rotated up to ±15° |
| Algorithm | SAC (Stable-Baselines3), network 3 × 256 |
| Training | Continued from the v6 policy for another 300k steps |
| Result | 100 % success in its final evaluations. It handles half the assumed grip force, and keeps the sideways load on the handle at ~21 N (v6: ~33 N) |
| Inputs / outputs | 37 numbers in (joints, gripper, handle and drawer state, last action); 5 out (move x/y/z, turn, open/close) |

> [!WARNING]
> v7 was trained for the **older setup**: a 1.4 × 1.0 m table, the drawer straight ahead, no 5 cm robot mount, a
> fast 0.67 s gripper and no joint acceleration limits. It runs correctly in its own world (from its `configs/`),
> but it is **not meant for the real arm**. The current `configs/` (v8) match the real lab setup instead.

### Run it

```bash
.venv/bin/python scripts/evaluate.py runs/sac_audit_fix_v7 --which best --viewer \
  --set task.randomization.placement_map=configs/placement_map_v6.yaml task.randomization.validate_reachability=false
```

Its saved `task.yaml` points at `configs/placement_map.yaml`, which is now the v8 map. The two overrides point it at
the matching older map, [`configs/placement_map_v6.yaml`](../configs/README.md#placement_map_v6yaml-the-map-for-the-older-policies),
and skip the start-up check that map can't pass.

## The files

| File | What it is |
|---|---|
| `best/best_model.zip` | The policy, as saved by Stable-Baselines3: the actor network (what controls the robot), the two critic networks used during training, and the optimiser state. Load with `SAC.load(...)` |
| `best/vecnormalize.pkl` | The running mean and spread of each input, recorded during training. The network only understands inputs scaled the same way, so it can't run without this |
| `configs/robot.yaml`, `drawer.yaml`, `scene.yaml`, `task.yaml` | Frozen copies of the world settings at training time. `evaluate.py` rebuilds the environment from these, not from the current `configs/` |
| `configs/train.yaml` | The training settings; `evaluate.py` reads the algorithm name (`SAC`) from it |

## Training your own

```bash
.venv/bin/python scripts/train.py --name my_run
```

New runs appear here as `runs/my_run/`. The repository's `.gitignore` excludes them, so they stay on your machine.
