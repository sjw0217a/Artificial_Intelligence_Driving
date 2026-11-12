"""복잡 구간 통과시간 평가: 신호 ① 통과 후 S1 → S1m → S1b → S2를 빠져나오기까지 걸린 시간.

전체 도착시간(약 190초)의 2/3는 신호 ① 적신호 대기라 정책이 줄일 수 없다. 그래서
"복잡한 구간을 얼마나 빨리 지나가는가"는 이 구간 시간으로 따로 잰다.

    python eval_section_time.py models/bc_v3_3.pt --episodes 100 --christmas
    python eval_section_time.py --algorithm rule --episodes 100 --christmas --traffic 1.3

출력: 충돌·완주·경로이탈 비율, 도착한 에피소드의 구간 통과시간 평균·표준편차·중앙값, 전체 도착시간.
"""
import argparse
import json
import os

import numpy as np
import traci

from env.road_config import ROAD, EGO, TRAFFIC
from env.cli import add_scenario_args, apply_scenario_args, private_sumo_dir
from env.mdp_config import SIMULATION, OBSERVATION, ACTION
from env import road_builder
from env.sumo_env import SumoHighwayEnv
from train import REWARD
from test import load_agent

BASE = os.path.dirname(os.path.abspath(__file__))
SECTION = ("S1", "S1m", "S1b", "S2")   # 복잡 구간 (사이의 교차로 내부 차로 포함)


def run(agent, env, episodes):
    rows = []
    for _ in range(episodes):
        obs, _ = env.reset()
        done, t, t_in, t_out = False, 0, None, None
        bus_seen, bypass = False, False   # 버스 정차를 봤는가 / 정류장 옆을 왼쪽 차로로 지나갔는가
        info = {}
        while not done:
            if env.ego_id in traci.vehicle.getIDList():
                road = traci.vehicle.getRoadID(env.ego_id)
                if t_in is None and road == SECTION[0]:
                    t_in = t
                if t_in is not None and t_out is None and road not in SECTION and not road.startswith(":"):
                    t_out = t          # 구간 다음 엣지(W_out)에 들어선 순간
                if env._bus_stopped_ahead() > 0.5:
                    bus_seen = True
                    if road == "S1b" and traci.vehicle.getLaneIndex(env.ego_id) >= 1:
                        bypass = True
            obs, _, term, trunc, info = env.step(agent.predict(obs, deterministic=True))
            done = term or trunc
            t += 1
        dt = env.step_length
        rows.append({
            "outcome": ("collided" if info.get("collided") else "arrived" if info.get("arrived")
                        else "route_failed" if info.get("route_failed") else "timeout"),
            "section_s": None if t_in is None or t_out is None else (t_out - t_in) * dt,
            "total_s": t * dt,
            "bus_seen": bus_seen,
            "bypass": bypass,
        })
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="복잡 구간 통과시간 평가")
    p.add_argument("model", nargs="?", default=None)
    p.add_argument("--algorithm", choices=["auto", "ppo", "bc", "rule"], default="auto")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--eval-seed", type=int, default=777001)
    p.add_argument("--json", default=None, help="에피소드별 결과를 저장할 경로")
    p.add_argument("--rule-kw", nargs="*", default=[], metavar="KEY=VALUE",
                   help="--algorithm rule일 때 RulePolicy 인자 (예: overtake_bus=1)")
    add_scenario_args(p)
    args = p.parse_args()
    traffic, sim = apply_scenario_args(args, TRAFFIC, SIMULATION)
    cfg = road_builder.build(ROAD, EGO, traffic, private_sumo_dir(BASE))
    env = SumoHighwayEnv(cfg_path=cfg, road=ROAD, ego=EGO, mdp_sim=sim, mdp_obs=OBSERVATION,
                         action=ACTION, reward=REWARD, traffic=traffic, gui=False)
    try:
        if args.algorithm == "rule":
            from utils.rule_policy import RulePolicy
            agent = RulePolicy(env, **{k: float(v) for k, v in (kv.split("=") for kv in args.rule_kw)})
        else:
            agent = load_agent(args.model, env.observation_space.shape[0],
                               env.action_space.shape[0], args.algorithm)
        np.random.seed(args.eval_seed)       # 모델 로드 뒤에 (PPO 생성자가 시드를 덮어씀)
        rows = run(agent, env, args.episodes)
    finally:
        env.close()

    n = len(rows)
    rate = lambda k: sum(r["outcome"] == k for r in rows) / n   # noqa: E731
    sec = np.array([r["section_s"] for r in rows if r["outcome"] == "arrived" and r["section_s"] is not None])
    tot = np.array([r["total_s"] for r in rows if r["outcome"] == "arrived"])
    print(f"{args.model or 'rule'} | {n} 에피소드 | 충돌 {rate('collided'):.1%} 완주 {rate('arrived'):.1%} "
          f"경로이탈 {rate('route_failed'):.1%} 시간초과 {rate('timeout'):.1%}")
    if len(sec):
        print(f"  복잡 구간 통과시간: 평균 {sec.mean():.2f}초 (표준편차 {sec.std():.2f}, 중앙값 {np.median(sec):.2f}, "
              f"평균의 95% 구간 ±{1.96 * sec.std() / np.sqrt(len(sec)):.2f})")
        print(f"  전체 도착시간: 평균 {tot.mean():.1f}초")
    seen = [r for r in rows if r["bus_seen"]]
    if seen:
        print(f"  정차 버스를 본 에피소드 {len(seen)}회 중 왼쪽 차로로 지나감(추월) {sum(r['bypass'] for r in seen)}회")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(rows, f)
