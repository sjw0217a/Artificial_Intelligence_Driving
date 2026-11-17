"""충돌 장면 분석: 평가에서 충돌한 Episode 하나를 그대로 다시 돌려, 충돌 직전 몇 초를 스텝마다 기록한다 (학습 과정 기록 11.9절).

eval_section_time.py는 np.random.seed(--eval-seed) 뒤 Episode마다 SUMO 시드를 np.random에서 하나씩 뽑는다.
그래서 앞 Episode들을 돌리지 않고 난수만 같은 횟수 뽑으면 i번째 Episode의 교통을 그대로 재현할 수 있다.
결과(충돌 시각)가 평가 JSON과 같은지 확인해서 재현이 맞는지 검사한다.

    python scripts/training/diagnose_collision.py models/bc_v3_3.pt --christmas --bus-scale 3 \
        --eval-seed 993001 --episode 20 --out docs/training/collisions/val_bus3_s1_ep20.json
    # sumo-gui 화면을 PNG로 저장 (영상용): --frames 폴더 --from-s 140

기록: 스텝마다 ego 위치·속도·행동, 같은 순간 선생(규칙)이라면 낼 행동, 모델이 본 관측 일부, 20 m 안 주변 차. 충돌 순간 SUMO 충돌 정보(누가 누구를, 어느 차로에서).
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

W = float(OBSERVATION["visibility"])
VMAX = float(ROAD["speed_limit"])


def nearby(ego, radius=20.0):
    ex, ey = traci.vehicle.getPosition(ego)
    out = []
    for v in traci.vehicle.getIDList():
        if v == ego:
            continue
        x, y = traci.vehicle.getPosition(v)
        d = float(np.hypot(x - ex, y - ey))
        if d <= radius:
            out.append({"id": v, "type": traci.vehicle.getTypeID(v), "lane": traci.vehicle.getLaneID(v),
                        "pos": round(traci.vehicle.getLanePosition(v), 1),
                        "v": round(traci.vehicle.getSpeed(v), 2), "dist": round(d, 1),
                        "signals": traci.vehicle.getSignals(v)})
    return sorted(out, key=lambda r: r["dist"])


def obs_view(o):
    """모델이 본 관측 중 충돌 해석에 필요한 것만 사람이 읽는 단위로."""
    def lane(k):
        i = 1 + 4 * k
        return {"lead_gap": None if o[i] >= 1 else round(float(o[i]) * W, 1),
                "lead_dv": None if o[i] >= 1 else round(float(o[i + 1]) * VMAX, 2),
                "rear_gap": None if o[i + 2] <= -1 else round(float(-o[i + 2]) * W, 1),
                "rear_dv": None if o[i + 2] <= -1 else round(float(o[i + 3]) * VMAX, 2)}
    return {"left": lane(1), "cur": lane(2), "right": lane(3),
            "left_blocked": float(o[33]), "right_blocked": float(o[34]),
            "target_lane": round(float(o[35]) * OBSERVATION["target_lane_norm"], 2),
            "bus": float(o[36]) if len(o) > 36 else None,
            "signal": float(o[31]), "stopline_m": round(float(o[32]) * 200, 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("--eval-seed", type=int, required=True)
    p.add_argument("--episode", type=int, required=True, help="평가 JSON에서 몇 번째(0부터) Episode인가")
    p.add_argument("--out", required=True)
    p.add_argument("--keep-s", type=float, default=12.0, help="저장할 충돌 전 구간 (초)")
    p.add_argument("--frames", help="sumo-gui 화면을 저장할 폴더")
    p.add_argument("--from-s", type=float, default=0.0, help="--frames: 이 시각부터 저장")
    p.add_argument("--zoom", type=float, default=900.0)
    p.add_argument("--mark", help="--frames: 이 차(충돌 상대 id)를 노란 원으로 표시")
    p.add_argument("--no-teacher", action="store_true", help="선생(규칙)이 같은 순간에 낼 행동을 기록하지 않음")
    add_scenario_args(p)
    args = p.parse_args()
    traffic, sim = apply_scenario_args(args, TRAFFIC, SIMULATION)
    gui = args.frames is not None
    if gui:
        sim = {**sim, "gui_delay": 0.0, "gui_zoom": args.zoom, "gui_track_ego": True}
        _start = traci.start
        traci.start = lambda cmd, *a, **k: _start(cmd + ["--window-size", "1280,720", "--window-pos", "0,30"], *a, **k)
        os.makedirs(args.frames, exist_ok=True)
    cfg = road_builder.build(ROAD, EGO, traffic, private_sumo_dir(BASE))
    env = SumoHighwayEnv(cfg_path=cfg, road=ROAD, ego=EGO, mdp_sim=sim, mdp_obs=OBSERVATION,
                         action=ACTION, reward=REWARD, traffic=traffic, gui=gui)
    agent = load_agent(args.model, env.observation_space.shape[0], env.action_space.shape[0], "auto")
    teacher = None
    if not args.no_teacher:
        from utils.rule_policy import RulePolicy
        teacher = RulePolicy(env)    # DAgger 정답 붙이기와 같은 방식: 학생이 운전하는 상태에서 선생에게 묻기만 한다
    np.random.seed(args.eval_seed)
    for _ in range(args.episode):          # 앞 Episode들이 뽑았을 SUMO 시드를 건너뜀
        if env.cfg_choices:
            np.random.randint(len(env.cfg_choices))
        np.random.randint(0, 100000)
    try:
        obs, _ = env.reset()
        ego, dt = env.ego_id, env.step_length
        log, t, done, info, coll = [], 0, False, {}, []
        while not done:
            alive = ego in traci.vehicle.getIDList()
            act = np.asarray(agent.predict(obs, deterministic=True), dtype=float).ravel()
            if alive:
                log.append({"t_s": t * dt, "road": traci.vehicle.getRoadID(ego),
                            "lane": traci.vehicle.getLaneIndex(ego),
                            "pos": round(traci.vehicle.getLanePosition(ego), 1),
                            "v": round(traci.vehicle.getSpeed(ego), 2),
                            "accel_cmd": round(float(act[0]), 2), "lane_cmd": round(float(act[1]), 2),
                            **({} if teacher is None else dict(zip(
                                ("teacher_accel", "teacher_lane"),
                                (round(float(x), 2) for x in np.asarray(
                                    teacher.predict(obs, deterministic=True), dtype=float).ravel())))),
                            "obs": obs_view(obs), "near": nearby(ego)})
                if gui and t * dt >= args.from_s:
                    for v in traci.vehicle.getIDList():
                        if traci.vehicle.getTypeID(v) == "bus_type":
                            traci.vehicle.setColor(v, (255, 255, 255, 255))
                    traci.vehicle.highlight(ego, (255, 60, 60, 255), 6)
                    if args.mark and args.mark in traci.vehicle.getIDList():
                        traci.vehicle.highlight(args.mark, (255, 220, 0, 255), 5)
                    traci.gui.screenshot(traci.gui.getIDList()[0], os.path.join(args.frames, f"{t:04d}.png"))
            obs, _, term, trunc, info = env.step(act)
            if info.get("collided"):
                coll = [{"collider": c.collider, "victim": c.victim, "collider_type": c.colliderType,
                         "victim_type": c.victimType, "collider_v": round(c.colliderSpeed, 2),
                         "victim_v": round(c.victimSpeed, 2), "type": c.type, "lane": c.lane,
                         "pos": round(c.pos, 1)} for c in traci.simulation.getCollisions()]
            done = term or trunc
            t += 1
    finally:
        env.close()
    outcome = ("collided" if info.get("collided") else "arrived" if info.get("arrived")
               else "route_failed" if info.get("route_failed") else "timeout")
    res = {"model": args.model, "eval_seed": args.eval_seed, "episode": args.episode, "outcome": outcome,
           "total_s": t * dt, "collision": coll, "steps": [r for r in log if r["t_s"] >= t * dt - args.keep_s]}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("outcome", "total_s", "collision")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
