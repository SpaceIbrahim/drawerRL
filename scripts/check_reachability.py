"""Find where the drawer can be placed so the arm can still physically open it.

    python scripts/check_reachability.py                       # sweep distance (x), plot + recommended range
    python scripts/check_reachability.py --xmin -0.15 --xmax 0.3 --step 0.01
    python scripts/check_reachability.py --verify-range -0.06 0.09   # check a planned randomisation box

x is the drawer offset AWAY from the robot (+) / TOWARDS it (-), relative to
scene.yaml -> drawer_placement.  Each placement is checked for IK reachability
along the whole pull, joint-limit margin, singularity, collisions, table/workspace
layout, and with a scripted grasp-and-pull in full physics (drawer_rl/reachability.py).
"""
import argparse
import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drawer_rl.config import PROJECT_ROOT  # noqa: E402
from drawer_rl.env import DrawerEnv  # noqa: E402
from drawer_rl.reachability import ReachabilityChecker  # noqa: E402

DET = ["task.observation.noise={}", "task.randomization.action_delay_steps=[0,0]", "robot.start_qpos_noise=0"]


def plot_map(pm, path, rcfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    img = pm.feasible.astype(int) + pm.safe.astype(int)          # 0 impossible, 1 feasible, 2 safe
    fig, ax = plt.subplots(figsize=(8, 4.8))
    dx, dy = pm.xs[1] - pm.xs[0], pm.yaws[1] - pm.yaws[0]
    ax.imshow(img.T, origin="lower", aspect="auto", cmap=ListedColormap(["#f3c9c9", "#cfe8cf", "#6fbf73"]),
              extent=[pm.xs[0] - dx / 2, pm.xs[-1] + dx / 2, pm.yaws[0] - dy / 2, pm.yaws[-1] + dy / 2], vmin=0, vmax=2)
    xr = rcfg.get("drawer_offset_x")
    yr = rcfg.get("drawer_yaw_range_deg")
    if xr and yr:
        ax.add_patch(plt.Rectangle((xr[0], yr[0]), xr[1] - xr[0], yr[1] - yr[0], fill=False, ec="k", lw=1.5, ls="--",
                                   label="training ranges (only dark-green cells are sampled)"))
        ax.legend(loc="upper left", fontsize=8)
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("drawer offset from nominal (m)   <- closer | farther ->")
    ax.set_ylabel("drawer yaw (deg)\n+ = counter-clockwise seen from above")
    ax.set_title("Where can the arm open the drawer?  red: no | light green: yes | dark green: yes with margin", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print("saved", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xmin", type=float, default=-0.15)
    ap.add_argument("--xmax", type=float, default=0.25)
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--margin", type=float, default=0.02, help="safety margin inside the feasible band (m)")
    ap.add_argument("--verify-range", type=float, nargs=2, default=None, metavar=("XMIN", "XMAX"))
    ap.add_argument("--y", type=float, nargs="*", default=None, help="lateral offsets to include in --verify-range")
    ap.add_argument("--z", type=float, nargs="*", default=None, help="height offsets to include in --verify-range")
    ap.add_argument("--plot", default=str(PROJECT_ROOT / "docs/media/reachability.png"))
    ap.add_argument("--map", action="store_true", help="build the 2-D distance x yaw placement map")
    ap.add_argument("--yaw-min", type=float, default=-20.0)
    ap.add_argument("--yaw-max", type=float, default=20.0)
    ap.add_argument("--yaw-step", type=float, default=2.5)
    ap.add_argument("--map-out", default="configs/placement_map.yaml")
    ap.add_argument("--set", nargs="*", default=[])
    args = ap.parse_args()
    env = DrawerEnv(overrides=DET + ["task.randomization.validate_reachability=false"] + args.set)
    ch = ReachabilityChecker(env)

    if args.map:
        from drawer_rl.placement_map import PlacementMap, build_map
        xs = np.round(np.arange(args.xmin, args.xmax + 1e-9, args.step), 4)
        yaws = np.round(np.arange(args.yaw_min, args.yaw_max + 1e-9, args.yaw_step), 3)
        print(f"building {len(xs)} x {len(yaws)} placement map (each cell: 4 corner checks + physics run)...")
        feas, marg = build_map(ch, xs, yaws, progress=lambda i, x, row: print(
            f"  x {x:+.3f}: " + "".join("#" if f else "." for f in row), flush=True))
        pm = PlacementMap(xs, yaws, feas, marg, erode=1)
        pm.save(args.map_out, env.cfg)
        print(f"saved {args.map_out}: {feas.sum()}/{feas.size} feasible cells, {pm.safe.sum()} safe after 1-cell margin")
        plot_map(pm, args.plot.replace(".png", "_map.png"), env.tc["randomization"])
        return

    if args.verify_range:
        r = env.tc["randomization"]
        ys = args.y if args.y is not None else [-r["drawer_xy"][1], 0.0, r["drawer_xy"][1]]
        zs = args.z if args.z is not None else [-r["drawer_z"], r["drawer_z"]]
        xs = np.round(np.arange(args.verify_range[0], args.verify_range[1] + 1e-9, args.step), 4)
        bad = []
        for x, y, z in itertools.product(xs, ys, zs):
            c = ch.check([x, y, z])
            if not c.feasible:
                bad.append(c)
        n = len(xs) * len(ys) * len(zs)
        print(f"checked {n} placements in x[{xs[0]:+.3f},{xs[-1]:+.3f}] y{ys} z{zs}: {n - len(bad)} feasible")
        for c in bad:
            print("  " + c.summary())
        sys.exit(1 if bad else 0)

    xs = np.round(np.arange(args.xmin, args.xmax + 1e-9, args.step), 4)
    interval, checks = ch.feasible_interval(xs)
    for c in checks:
        print(c.summary())
    nom = env.cfg["scene"]["drawer_placement"]["x"]
    if interval is None:
        print("no feasible placement found")
        return
    lo, hi = interval
    rec = (round(lo + args.margin, 3), round(hi - args.margin, 3))
    print(f"\nfeasible distance band (offset from nominal x={nom:.2f} m): [{lo:+.3f}, {hi:+.3f}] m  "
          f"-> cabinet front {nom + lo:.2f}-{nom + hi:.2f} m from the robot base")
    print(f"recommended randomisation (with {args.margin * 100:.0f} cm margin): "
          f"task.randomization.drawer_offset_x=[{rec[0]}, {rec[1]}]")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
    feas = np.array([c.feasible for c in checks])
    for a in ax:
        for x, f in zip(xs, feas):
            a.axvspan(x - args.step / 2, x + args.step / 2, color="#d9f2d9" if f else "#f6d5d5", lw=0)
        a.axvspan(rec[0], rec[1], color="none", ec="#1b7f3a", hatch="//", lw=1.2, label="training range")
        a.axvline(0, color="k", lw=0.8, ls="--")
    ax[0].plot(xs, [c.min_joint_margin_deg for c in checks], "o-", ms=3, color="#2b5d9b")
    ax[0].axhline(ch.min_margin, color="#a33", lw=0.8)
    ax[0].set_ylabel("min joint-limit\nmargin (deg)")
    ax[1].plot(xs, [c.min_sigma for c in checks], "o-", ms=3, color="#2b5d9b")
    ax[1].axhline(ch.min_sigma, color="#a33", lw=0.8)
    ax[1].set_ylabel("min Jacobian\nsingular value")
    ax[1].set_xlabel("drawer offset from nominal (m)   <- closer to robot | farther ->")
    ax[0].set_title("Can the arm open the drawer?  green = yes (IK + clearance + physics), red = no")
    ax[0].legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    Path(args.plot).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.plot, dpi=130)
    print("saved", args.plot)


if __name__ == "__main__":
    main()
