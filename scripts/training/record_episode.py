"""발표 영상용: 교통을 고정한 한 Episode를 돌리고, sumo-gui 화면을 스텝마다 PNG로 저장한다.

같은 --scene 값이면 SUMO 시드와 초기 배경차 배치(prefill)가 같아서, 두 모델이 같은 교통에서
출발한다 (모델 행동이 달라지는 순간부터는 교통도 조금씩 달라진다).

    # 1) 화면 없이 장면 후보 찾기: 장면마다 결과를 한 줄 JSON으로 출력
    python scripts/training/record_episode.py models/bc_v3_3.pt --christmas --search 0 40
    BUS_STOP_FLAG=0 python scripts/training/record_episode.py models/bc_dag3_36dim.pt --christmas --search 0 40

    # 2) 고른 장면을 sumo-gui로 녹화 (frames/에 0000.png ... + steps.json)
    python scripts/training/record_episode.py models/bc_v3_3.pt --christmas --scene 17 --frames out/v3_3

모델 관측 차원은 import 시점에 정해지므로, 36차원 모델(dag3)은 BUS_STOP_FLAG=0으로 따로 실행한다.
"""
import argparse
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
os.chdir(BASE)

import traci  # noqa: E402

from env.road_config import ROAD, EGO, TRAFFIC  # noqa: E402
from env.cli import add_scenario_args, apply_scenario_args, private_sumo_dir  # noqa: E402
from env.mdp_config import SIMULATION, OBSERVATION, ACTION  # noqa: E402
from env import road_builder  # noqa: E402
from env.sumo_env import SumoHighwayEnv  # noqa: E402
from train import REWARD  # noqa: E402
from test import load_agent  # noqa: E402

SECTION = ("S1", "S1m", "S1b", "S2")
FIXED_VIEW = None   # --fixed M: 복잡 구간 주변 M 미터 여유를 두고 카메라 고정
_default_rng = np.random.default_rng


def fix_scene(scene):
    """SUMO 시드(np.random)와 prefill 배치(default_rng)를 scene으로 고정한다."""
    np.random.seed(10_000 + scene)
    np.random.default_rng = lambda *a, **k: _default_rng(20_000 + scene)


def run_episode(env, agent, frames_dir=None):
    obs, _ = env.reset()
    np.random.default_rng = _default_rng
    view = traci.gui.getIDList()[0] if frames_dir else None
    if view and FIXED_VIEW:
        # 복잡 구간(S1~S2)이 한 화면에 들어오게 카메라를 고정한다
        pts = [p for e in SECTION for i in range(traci.edge.getLaneNumber(e))
               for p in traci.lane.getShape(f"{e}_{i}")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        m = FIXED_VIEW
        traci.gui.setBoundary(view, min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
    if view:
        # 영상에서만 쓰는 표시 (주행에는 영향 없음): ego에 원, 버스는 흰색
        traci.vehicle.highlight(env.ego_id, (255, 60, 60, 255), 6)
    done, t, t_in, t_out, info = False, 0, None, None, {}
    bus_seen = bypass = False
    steps = []
    while not done:
        road, lane = "", -1
        if env.ego_id in traci.vehicle.getIDList():
            road = traci.vehicle.getRoadID(env.ego_id)
            lane = traci.vehicle.getLaneIndex(env.ego_id)
            if t_in is None and road == SECTION[0]:
                t_in = t
            if t_in is not None and t_out is None and road not in SECTION and not road.startswith(":"):
                t_out = t
        bus = env._bus_stopped_ahead() > 0.5 if road else False
        if bus:
            bus_seen = True
            bypass |= road == "S1b" and lane >= 1
        steps.append({"t": t, "road": road, "lane": lane, "bus": bool(bus),
                      "in_section": t_in is not None and t_out is None})
        if frames_dir:
            for v in traci.vehicle.getIDList():
                if traci.vehicle.getTypeID(v) == "bus_type":
                    traci.vehicle.setColor(v, (255, 255, 255, 255))
            traci.gui.screenshot(view, os.path.join(frames_dir, f"{t:04d}.png"))
        obs, _, term, trunc, info = env.step(agent.predict(obs, deterministic=True))
        done = term or trunc
        t += 1
    dt = env.step_length
    outcome = ("collided" if info.get("collided") else "arrived" if info.get("arrived")
               else "route_failed" if info.get("route_failed") else "timeout")
    return {"outcome": outcome, "bus_seen": bus_seen, "bypass": bypass, "total_s": t * dt,
            "section_s": None if t_in is None or t_out is None else (t_out - t_in) * dt,
            "t_in": t_in, "t_out": t_out, "steps": steps}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("--search", nargs=2, type=int, metavar=("FROM", "TO"))
    p.add_argument("--scene", type=int)
    p.add_argument("--frames", help="녹화 PNG를 저장할 폴더")
    p.add_argument("--zoom", type=float, default=450.0)
    p.add_argument("--window", default="1280,720")
    p.add_argument("--fixed", type=float, default=None, metavar="M",
                   help="ego를 따라가지 않고 복잡 구간을 고정 화면으로 (여유 M 미터)")
    add_scenario_args(p)
    args = p.parse_args()
    traffic, sim = apply_scenario_args(args, TRAFFIC, SIMULATION)
    gui = args.frames is not None
    FIXED_VIEW = args.fixed
    if gui:
        sim = {**sim, "gui_delay": 0.0, "gui_zoom": args.zoom, "gui_track_ego": args.fixed is None}
        _start = traci.start
        traci.start = lambda cmd, *a, **k: _start(
            cmd + ["--window-size", args.window, "--window-pos", "0,30"], *a, **k)
    cfg = road_builder.build(ROAD, EGO, traffic, private_sumo_dir(BASE))
    env = SumoHighwayEnv(cfg_path=cfg, road=ROAD, ego=EGO, mdp_sim=sim, mdp_obs=OBSERVATION,
                         action=ACTION, reward=REWARD, traffic=traffic, gui=gui)
    agent = load_agent(args.model, env.observation_space.shape[0], env.action_space.shape[0])
    try:
        if args.search:
            for scene in range(*args.search):
                fix_scene(scene)
                r = run_episode(env, agent)
                r.pop("steps")
                print(json.dumps({"scene": scene, **r}), flush=True)
        else:
            os.makedirs(args.frames, exist_ok=True)
            fix_scene(args.scene)
            r = run_episode(env, agent, args.frames)
            with open(os.path.join(args.frames, "steps.json"), "w") as f:
                json.dump({"model": args.model, "scene": args.scene, **r}, f)
            print({k: v for k, v in r.items() if k != "steps"})
    finally:
        env.close()
