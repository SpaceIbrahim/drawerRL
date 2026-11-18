"""Hand-written (non-RL) controller that reaches, grasps and pulls the drawer.

Sanity check that the scene physics allow the task (gripper can hold the handle,
slide friction is reasonable, everything is reachable).  Uses drawer_rl.scripted.

    python scripts/scripted_demo.py --viewer                   # watch it live in the 3D viewer
    python scripts/scripted_demo.py --video generated/scripted_demo.mp4
    python scripts/scripted_demo.py --offset 0.08 0 0          # drawer 8 cm farther away
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drawer_rl.env import DrawerEnv  # noqa: E402
from drawer_rl.scripted import run_scripted  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=None)
    ap.add_argument("--viewer", action="store_true", help="watch it live in the MuJoCo viewer (real time)")
    ap.add_argument("--offset", type=float, nargs=3, default=None, help="drawer offset x y z (m)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--set", nargs="*", default=[], help="config overrides, e.g. drawer.top_drawer.slide.damping=12")
    args = ap.parse_args()
    if args.viewer and args.video:
        ap.error("use either --viewer or --video, not both")
    mode = "human" if args.viewer else ("rgb_array" if args.video else None)
    env = DrawerEnv(overrides=args.set, render_mode=mode)
    frames = []

    def on_step(e, info):
        if args.video:
            frames.append(e.render())
        elif args.viewer:
            e.render()                 # syncs the viewer window with the simulation
            time.sleep(e.dt)           # play back in real time (one 50 ms control step)

    opts = {"drawer_offset": args.offset, "drawer_yaw_deg": 0.0} if args.offset else None
    ret, info, log = run_scripted(env, seed=args.seed, options=opts,
                                  on_step=on_step if (args.video or args.viewer) else None)
    for t in range(0, len(log), 10):
        print(f"t={t:3d} {log[t]['phase']:8s} grasp={log[t]['grasped']!s:5} open={log[t]['opening']:.3f}")
    print(f"final opening={info['opening']:.3f} m  success={info.get('is_success')}  return={ret:.0f}")
    if args.video:
        import imageio
        imageio.mimsave(args.video, frames, fps=int(env.tc["control"]["frequency_hz"]))
        print("saved", args.video)
    if args.viewer and env._viewer is not None:
        print("Done. Close the viewer window to exit.")
        try:
            while env._viewer.is_running():
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
    env.close()


if __name__ == "__main__":
    main()
