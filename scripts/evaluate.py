"""Evaluate a trained policy (success rate, opening, video, live viewer).

    python scripts/evaluate.py runs/<run_name>                       # final model, 20 episodes
    python scripts/evaluate.py runs/<run_name> --which best --video generated/eval.mp4
    python scripts/evaluate.py runs/<run_name> --viewer               # watch it live
    python scripts/evaluate.py runs/<run_name> --set task.randomization.drawer_xy=[0.03,0.03]

The environment is rebuilt from the run's frozen configs; ``--set`` lets you test
the same policy on a modified world (e.g. a re-measured drawer).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize  # noqa: E402

from drawer_rl.config import load_env_config, load_yaml  # noqa: E402
from drawer_rl.env import DrawerEnv  # noqa: E402
from train import ALGOS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--which", default="final", choices=["final", "best"], help="model to load")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--video", default=None)
    ap.add_argument("--viewer", action="store_true")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--set", nargs="*", default=[])
    args = ap.parse_args()

    run = Path(args.run_dir)
    tcfg = load_yaml(run / "configs/train.yaml")
    env_cfg = load_env_config({k: run / f"configs/{k}.yaml" for k in ("robot", "drawer", "scene", "task")}, args.set)
    mode = "human" if args.viewer else ("rgb_array" if args.video else None)
    raw = DrawerEnv(cfg=env_cfg, render_mode=mode)
    venv = DummyVecEnv([lambda: raw])
    model_path = run / ("final_model.zip" if args.which == "final" else "best/best_model.zip")
    vn_path = run / ("vecnormalize.pkl" if args.which == "final" else "best/vecnormalize.pkl")
    if vn_path.exists():
        venv = VecNormalize.load(str(vn_path), venv)
        venv.training, venv.norm_reward = False, False
    model = ALGOS[tcfg["algorithm"]].load(str(model_path), device="cpu", custom_objects={"buffer_size": 1})

    frames, successes, openings, lengths = [], [], [], []
    for ep in range(args.episodes):
        obs = venv.reset()
        done, steps, max_open = False, 0, 0.0
        while not done:
            act, _ = model.predict(obs, deterministic=not args.stochastic)
            obs, r, dones, infos = venv.step(act)
            done, info = dones[0], infos[0]
            steps += 1
            max_open = max(max_open, info["opening"])
            if args.video and ep < 3:
                frames.append(raw.render())
            if args.viewer:
                raw.render()
                time.sleep(raw.dt)
        successes.append(info.get("is_success", False))
        openings.append(max_open)
        lengths.append(steps)
        print(f"episode {ep:3d}: success={successes[-1]!s:5}  max_opening={max_open:.3f} m  steps={steps}")
    print(f"\nSuccess rate: {np.mean(successes) * 100:.1f}%   mean max opening: {np.mean(openings):.3f} m   "
          f"mean length: {np.mean(lengths):.1f} steps")
    if args.video:
        import imageio
        imageio.mimsave(args.video, frames, fps=int(env_cfg["task"]["control"]["frequency_hz"]))
        print("saved", args.video)


if __name__ == "__main__":
    main()
