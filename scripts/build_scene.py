"""Build the world from the configs, save the MJCF and preview images, or open the viewer.

    python scripts/build_scene.py                 # writes generated/scene.xml + preview_*.png
    python scripts/build_scene.py --view          # interactive MuJoCo viewer (drag the drawer!)
    python scripts/build_scene.py --set drawer.top_drawer.front_height=0.135
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import imageio  # noqa: E402
import mujoco  # noqa: E402

from drawer_rl.config import resolve_path  # noqa: E402
from drawer_rl.drawer_builder import drawer_geometry  # noqa: E402
from drawer_rl.env import DrawerEnv  # noqa: E402
from drawer_rl.scene_builder import save_scene_xml  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="generated")
    ap.add_argument("--view", action="store_true")
    ap.add_argument("--set", nargs="*", default=[])
    args = ap.parse_args()

    env = DrawerEnv(overrides=args.set)
    env.reset(seed=0)
    out = resolve_path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print("saved", save_scene_xml(env.cfg, out / "scene.xml"))

    s = env._task_state(env.last_action, env.last_action)
    geo = drawer_geometry(env.cfg["drawer"])
    print(f"start joint angles (rad): {env.q_start.round(3).tolist()}")
    print(f"TCP start (base frame):   {s['tcp_pos'].round(3).tolist()}")
    print(f"Handle (base frame):      {s['handle_pos'].round(3).tolist()}")
    print(f"Handle height above table: {geo['handle_center_closed'][2]:.3f} m")
    print(f"Drawer open axis (base):  {s['drawer_axis'].round(3).tolist()}")

    r = mujoco.Renderer(env.model, 600, 800)
    for cam in env.cfg["scene"].get("cameras", {}):
        r.update_scene(env.data, cam)
        imageio.imwrite(out / f"preview_{cam}.png", r.render())
        print("saved", out / f"preview_{cam}.png")
    r.close()

    if args.view:
        import mujoco.viewer as mj_viewer
        mj_viewer.launch(env.model, env.data)


if __name__ == "__main__":
    main()
