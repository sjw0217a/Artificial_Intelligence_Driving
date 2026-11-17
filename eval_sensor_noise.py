"""센서 오차 강건성 평가: 관측에 센서 오차를 넣고 eval_section_time.py와 같은 방식으로 평가한다.

관측 [33]~[36]과 앞뒤 차 거리·속도는 "센서가 항상 정확하다"는 가정 위에 있다 (학습 과정 기록 12.1절 약점 4).
실제 센서처럼 틀리면 최종 모델이 얼마나 나빠지는지 잰다. 모델에 들어가는 관측만 바꾸고, 시뮬레이터는 그대로다.
선생(규칙)은 SUMO 내부 정보를 직접 읽어서 이 실험을 할 수 없다.

    python eval_sensor_noise.py models/bc_v3_3.pt --noise dist --level 2 --christmas --eval-seed 888001 --episodes 100

--noise 종류 (--level 뜻)
  none   오차 없음 (기준)
  dist   앞뒤 차 거리·상대속도 [1..20]에 가우시안 잡음. level = 거리 표준편차(m), 속도는 그 절반(m/s).
         차가 있을 때만 넣는다 (없음 표시는 그대로)
  side   옆 차로 막힘 경고 [33][34]가 켜져야 할 때 level 확률로 꺼짐 (경고 놓침, 스텝마다 독립)
  sideoff 옆 차로 막힘 경고를 아예 끔 (항상 "비어 있음"). 차로가 없는 쪽은 그대로
  delay  관측 전체가 level 스텝(1스텝 = 0.5초) 늦게 들어옴
  bus    정류장 버스 표시 [36]가 켜져야 할 때 level 확률로 꺼짐

--smooth K (dist에만): 오차가 섞인 앞뒤 차 거리·상대속도를 최근 K스텝 평균으로 쓴다 (실제 센서의 추적 필터에 해당).
         최근 K스텝 내내 그 차가 보였을 때만 평균 내고, 아니면 이번 값을 그대로 쓴다. 기본 1 = 평균 안 냄
"""
import argparse
import collections
import json
import os

import numpy as np

import eval_section_time as est
from env.road_config import ROAD, EGO, TRAFFIC
from env.cli import add_scenario_args, apply_scenario_args, private_sumo_dir
from env.mdp_config import SIMULATION, OBSERVATION, ACTION
from env import road_builder
from env.sumo_env import SumoHighwayEnv
from train import REWARD
from test import load_agent

W = float(OBSERVATION["visibility"])
VMAX = float(ROAD["speed_limit"])
LEFT_CONN, RIGHT_CONN = 22, 24      # 좌1·우1 차로 연결성 (-1이면 차로 없음)


class NoisyAgent:
    """agent.predict 앞에서 관측을 바꾼다. 난수는 시뮬레이터 난수(np.random)와 따로 써서 교통은 기준과 같게 시작한다."""

    def __init__(self, agent, kind, level, seed, smooth=1):
        self.agent, self.kind, self.level = agent, kind, level
        self.rng = np.random.default_rng(seed)
        self.buf = collections.deque()
        self.smooth = int(smooth)
        self.hist = collections.deque(maxlen=self.smooth)

    def reset(self):
        self.buf.clear()
        self.hist.clear()

    def _smoothed(self, o):
        self.hist.append(o.copy())
        if self.smooth <= 1 or len(self.hist) < self.smooth:
            return o
        h = np.stack(self.hist)
        for b in range(5):
            i = 1 + 4 * b
            if np.all(h[:, i] < 1.0):                # 앞차가 K스텝 내내 보임
                o[i:i + 2] = h[:, i:i + 2].mean(axis=0)
            if np.all(h[:, i + 2] > -1.0):           # 뒤차가 K스텝 내내 보임
                o[i + 2:i + 4] = h[:, i + 2:i + 4].mean(axis=0)
        return o

    def perturb(self, obs):
        o = np.array(obs, dtype=np.float32, copy=True)
        k, lv = self.kind, self.level
        if k == "dist":
            sd, sv = lv / W, 0.5 * lv / VMAX
            for b in range(5):
                i = 1 + 4 * b
                if o[i] < 1.0:                       # 앞차 있음
                    o[i] = np.clip(o[i] + self.rng.normal(0, sd), 0.0, 1.0)
                    o[i + 1] = np.clip(o[i + 1] + self.rng.normal(0, sv), -1.0, 1.0)
                if o[i + 2] > -1.0:                  # 뒤차 있음
                    o[i + 2] = np.clip(o[i + 2] + self.rng.normal(0, sd), -1.0, 0.0)
                    o[i + 3] = np.clip(o[i + 3] + self.rng.normal(0, sv), -1.0, 1.0)
            o = self._smoothed(o)
        elif k in ("side", "sideoff"):
            for idx, conn in ((33, LEFT_CONN), (34, RIGHT_CONN)):
                if o[idx] > 0.5 and o[conn] > -1.0 and (k == "sideoff" or self.rng.random() < lv):
                    o[idx] = 0.0
        elif k == "bus":
            if len(o) > 36 and o[36] > 0.5 and self.rng.random() < lv:
                o[36] = 0.0
        elif k == "delay":
            self.buf.append(o)
            if len(self.buf) > int(lv) + 1:
                self.buf.popleft()
            o = self.buf[0]                          # 에피소드 처음에는 가장 오래된 관측(첫 관측)을 쓴다
        return o

    def predict(self, obs, deterministic=True):
        return self.agent.predict(self.perturb(obs), deterministic=deterministic)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="센서 오차 강건성 평가")
    p.add_argument("model")
    p.add_argument("--noise", choices=["none", "dist", "side", "sideoff", "delay", "bus"], default="none")
    p.add_argument("--level", type=float, default=0.0)
    p.add_argument("--smooth", type=int, default=1, help="dist: 최근 K스텝 평균 (1 = 안 함)")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--eval-seed", type=int, required=True)
    p.add_argument("--json", default=None)
    add_scenario_args(p)
    args = p.parse_args()
    traffic, sim = apply_scenario_args(args, TRAFFIC, SIMULATION)
    cfg = road_builder.build(ROAD, EGO, traffic, private_sumo_dir(est.BASE))
    env = SumoHighwayEnv(cfg_path=cfg, road=ROAD, ego=EGO, mdp_sim=sim, mdp_obs=OBSERVATION,
                         action=ACTION, reward=REWARD, traffic=traffic, gui=False)
    try:
        base = load_agent(args.model, env.observation_space.shape[0], env.action_space.shape[0], "auto")
        agent = NoisyAgent(base, args.noise, args.level, seed=args.eval_seed + 7, smooth=args.smooth)
        _reset = env.reset
        env.reset = lambda *a, **k: (agent.reset(), _reset(*a, **k))[1]   # delay 버퍼를 에피소드마다 비움
        np.random.seed(args.eval_seed)
        rows = est.run(agent, env, args.episodes)
    finally:
        env.close()

    n = len(rows)
    cnt = collections.Counter(r["outcome"] for r in rows)
    sec = np.array([r["section_s"] for r in rows if r["outcome"] == "arrived" and r["section_s"] is not None])
    print(f"{args.noise} {args.level:g} 평균{args.smooth} | {n} 에피소드 | 충돌 {cnt['collided']} 도착 {cnt['arrived']} "
          f"경로이탈 {cnt['route_failed']} 시간초과 {cnt['timeout']}")
    if len(sec):
        print(f"  복잡 구간 통과시간: 평균 {sec.mean():.2f}초 (±{1.96 * sec.std() / np.sqrt(len(sec)):.2f})")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(rows, f)
