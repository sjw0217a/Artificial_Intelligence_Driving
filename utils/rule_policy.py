"""규칙 기반 운전 정책 — 학습 결과와 비교할 기준선이자 BC의 시연자.

    가감속: 같은 차로 앞차와의 간격·상대속도로 IDM 식을 계산한다 (관측 [0], [9], [10]).
    차선:   경로를 따라가려면 옮겨야 하는 방향으로, 그 차로의 앞뒤 틈이 충분할 때만 옮긴다.

관측에 없는 정보 두 가지를 SUMO에서 직접 읽는다 (그래서 "규칙 기반"은 관측만 쓰는 정책이 아니다).
  1) 옮겨야 하는 방향: getBestLanes. (학생 모델은 같은 정보를 관측 [35]로 받는다)
  2) 옆 차로의 실제 앞뒤 틈: 차로를 직접 훑는다. 관측 [5..8], [13..16]은 SUMO getNeighbors 값이라
     바로 옆에 겹쳐 있거나 앞뒤 약 2.5 m(minGap) 안에 있는 차가 "없음"으로 나온다. 관측만 믿고
     옮기면 그 차와 부딪힌다 (11/11 측정: 관측만 쓰면 충돌 7~13%, 충돌 순간 실제 틈 -4~2 m).

11/12 개선 (크리스마스 x1.3, 150 에피소드, 같은 시드): 충돌 9 → 0, 완주 139 → 146.
  - sumo_check: SUMO couldChangeLane으로 엣지 경계 너머(교차로 안·다음 엣지)의 차까지 확인.
    충돌의 대부분이 S1 끝(합류점 MP 직전)에서 차선을 바꾸다 교차로에 막 들어선 차를 옆에서 박은 것이었다.
  - wait_speed: 옮겨야 하는데 막혀 있으면 5 m/s까지 줄여 틈을 기다린다 (sumo_check만 켜면 경로 이탈 9%).
  - overtake_bus: 80 m 안 정류장에 버스가 서 있으면(관측 [36]과 같은 기준) 한 칸 왼쪽 줄로
    정류장을 지나간 뒤 S2에서 맨 오른쪽 차로로 돌아간다. 크리스마스에서 버스에 막힌 Episode가
    36초 → 23초. overtake_bus=0으로 끌 수 있다.
  - overtake_slow, always_bypass: 시도했지만 효과가 없어 기본값은 꺼져 있다 (학습 과정 기록 10.8절).

evaluate_policy와 데이터 수집기가 쓰는 predict(obs, deterministic) 인터페이스를 따른다.
"""
import numpy as np
import traci


class RulePolicy:
    def __init__(self, env, time_headway=1.2, min_gap=2.0,
                 front_gap=3.0, front_tau=0.3, rear_gap=3.0, rear_tau=0.5,
                 spawn_protect=60.0, sumo_check=True, wait_speed=5.0, overtake_bus=True,
                 overtake_slow=False, slow_speed=5.0, slow_lookahead=30.0, always_bypass=False):
        self.env = env
        self.vmax = float(env.vmax)
        self.W = float(env.visibility)
        self.a_max = float(env.max_accel)
        self.b_max = float(env.max_decel)
        self.T, self.s0 = time_headway, min_gap
        self.front_gap, self.front_tau = front_gap, front_tau
        self.rear_gap, self.rear_tau = rear_gap, rear_tau
        # 진입 엣지의 처음 이 거리(m)에서는 차선을 바꾸지 않는다. 입구에서 방금 생성된 차는
        # 다음 스텝까지 관측에 안 잡혀서, 여기서 옮기면 옆 차로에 새로 생긴 차와 부딪힌다
        # (규칙 기반 충돌의 대부분이 진입 0~40 m에서 났다).
        self.spawn_protect = spawn_protect
        # SUMO 차선변경 모델의 안전 판정(couldChangeLane)까지 통과해야 옮긴다. 엣지 경계를 넘어
        # 교차로 안·다음 엣지에 있는 차까지 본다 (_scan_ok는 지금 엣지의 차로만 훑는다).
        self.sumo_check = sumo_check
        # 옮겨야 하는데 옆이 막혀 있으면 이 속도(m/s)까지 천천히 줄여 틈을 기다린다 (None이면 끔).
        # 안 줄이면 틈을 못 찾은 채 차로 끝에 닿아 경로 이탈이 난다.
        self.wait_speed = wait_speed
        # 신세계 정류장(S1b 맨 오른쪽 차로)에 버스가 서 있으면 그 차로로 가지 않고 한 칸 왼쪽으로
        # 지나간 뒤 S2(7차로, 58 m)에서 맨 오른쪽(W_out 방향)으로 돌아온다. 경로상 필요한 차로를 잠깐 바꾸는 것.
        self.overtake_bus = overtake_bus
        # 복잡 구간에서 앞차가 slow_speed(m/s)보다 느리면(크리스마스 구경꾼 3 m/s 등) 옆 차로가 더 빠를 때
        # 옮긴다. 경로상 필요한 차로에서 한 칸까지만 벗어난다 (S2 확폭 구간에서 돌아올 수 있게).
        self.overtake_slow = overtake_slow
        self.slow_speed, self.slow_lookahead = slow_speed, slow_lookahead
        # (실험용) 버스가 없어도 항상 우회 줄(S1m 2번 → S1b 1번)로 가서 MG 합류 대기열을 건너뛴다.
        self.always_bypass = always_bypass

    # 관측에서 차로 블록의 시작 칸: 왼쪽(+1) 5, 현재 9, 오른쪽(-1) 13
    #   [k] 앞차 간격/W, [k+1] 앞차 상대속도/vmax, [k+2] -뒤차 간격/W, [k+3] 뒤차 상대속도/vmax
    _BLOCK = {+1: 5, -1: 13}
    # 연결성 칸: 왼쪽(+1) 22, 오른쪽(-1) 24. -1이면 그 차로가 없다
    _CONN = {+1: 22, -1: 24}

    def _accel(self, obs) -> float:
        v = float(obs[0]) * self.vmax
        free = 1.0 - (v / self.vmax) ** 4
        if obs[9] >= 1.0:                       # 시야 안에 앞차 없음
            a = self.a_max * free
        else:
            gap = max(float(obs[9]) * self.W, 0.1)
            closing = -float(obs[10]) * self.vmax          # 내가 더 빠르면 +
            s_star = self.s0 + v * self.T + v * closing / (2 * np.sqrt(self.a_max * self.b_max))
            a = self.a_max * (free - (max(s_star, self.s0) / gap) ** 2)
        return float(np.clip(a / self.a_max if a >= 0 else a / self.b_max, -1.0, 1.0))

    # 버스 추월 때 엣지별로 있을 차로: S1 1번 → S1m 2번 → S1b 1번 (모두 정류장 차로 S1b_0의 한 칸 왼쪽 줄)
    _BYPASS_LANE = {"S1": 1, "S1m": 2, "S1b": 1}
    _BUS_STOP_END = 27.0

    def _bus_at_stop(self) -> bool:
        # 학생 관측 [36]과 같은 기준: 시야(W) 안 앞쪽 정류장에 버스가 서 있을 때만 추월한다.
        #   (선생이 학생이 못 보는 먼 버스까지 보고 움직이면 학생이 따라 할 근거가 없다)
        return self.always_bypass or self.env._bus_stopped_ahead() > 0.5

    def _wanted_direction(self) -> int:
        """경로를 따라가려면 옮겨야 하는 방향: +1 왼쪽, -1 오른쪽, 0 유지."""
        ego = self.env.ego_id
        try:
            road = traci.vehicle.getRoadID(ego)
            if road.startswith(":"):
                return 0
            if (self.overtake_bus and road in self._BYPASS_LANE and self._bus_at_stop()
                    and not (road == "S1b" and traci.vehicle.getLanePosition(ego) > self._BUS_STOP_END)):
                return int(np.sign(self._BYPASS_LANE[road] - traci.vehicle.getLaneIndex(ego)))
            if (traci.vehicle.getRouteIndex(ego) == 0
                    and traci.vehicle.getLanePosition(ego) < self.spawn_protect):
                return 0
            lane = traci.vehicle.getLaneID(ego)
            for info in traci.vehicle.getBestLanes(ego):
                if info[0] == lane:
                    offset = int(info[3])
                    if self.overtake_slow and road in self._BYPASS_LANE:
                        d = self._speed_gain_direction(offset)
                        if d != 0:
                            return d
                    return int(np.sign(offset))
        except traci.TraCIException:
            pass
        return 0

    def _speed_gain_direction(self, offset: int) -> int:
        """앞차가 느리면 더 빠른 옆 차로 방향(+1/-1), 아니면 0. 경로 차로에서 한 칸까지만 벗어난다."""
        ego = self.env.ego_id
        lead = traci.vehicle.getLeader(ego, self.slow_lookahead)
        if not lead or lead[0] == "":
            return 0
        lead_v = traci.vehicle.getSpeed(lead[0])
        if lead_v >= self.slow_speed:
            return 0
        best, best_gain = 0, 0.0
        n = traci.edge.getLaneNumber(traci.vehicle.getRoadID(ego))
        cur = traci.vehicle.getLaneIndex(ego)
        for d in (+1, -1):
            if not 0 <= cur + d < n or abs(offset - d) > 1:
                continue
            front, _ = self.env._scan_lane_neighbors(d)
            if front is None:
                gain = 10.0
            elif front[0] > lead[1] + 5.0 and front[1] > lead_v + 2.0:
                gain = front[1] - lead_v
            else:
                continue
            if gain > best_gain:
                best, best_gain = d, gain
        return best

    def _gap_ok(self, obs, direction: int) -> bool:
        if obs[self._CONN[direction]] == -1.0:
            return False
        k = self._BLOCK[direction]
        v = float(obs[0]) * self.vmax
        if obs[k] < 1.0:                                   # 옮길 차로의 앞차
            if float(obs[k]) * self.W <= self.front_gap + self.front_tau * v:
                return False
        if obs[k + 2] > -1.0:                              # 옮길 차로의 뒤차
            rear = -float(obs[k + 2]) * self.W
            rear_closing = max(float(obs[k + 3]) * self.vmax, 0.0)   # 뒤차가 더 빠르면 +
            rear_v = v + float(obs[k + 3]) * self.vmax
            if rear <= self.rear_gap + self.rear_tau * rear_v + rear_closing:
                return False
        if not self._scan_ok(v, direction):
            return False
        if self.sumo_check:
            try:
                return bool(traci.vehicle.couldChangeLane(self.env.ego_id, direction))
            except traci.TraCIException:
                return False
        return True

    def _scan_ok(self, v, direction: int) -> bool:
        """옆 차로를 직접 훑어 실제 앞뒤 틈을 확인한다 (겹친 차는 틈이 음수로 나온다)."""
        front, rear = self.env._scan_lane_neighbors(direction)
        if front is not None:
            gap, lead_v = front
            if gap <= self.front_gap + self.front_tau * v + max(v - lead_v, 0.0):
                return False
        if rear is not None:
            gap, rear_v = rear
            if gap <= self.rear_gap + self.rear_tau * rear_v + max(rear_v - v, 0.0):
                return False
        return True

    def predict(self, obs, deterministic: bool = True):
        if self.env.ego_id not in traci.vehicle.getIDList():
            return np.zeros(2, dtype=np.float32)
        direction = self._wanted_direction()
        ok = direction != 0 and self._gap_ok(obs, direction)
        lane = float(direction) if ok else 0.0
        accel = self._accel(obs)
        if direction != 0 and not ok and self.wait_speed is not None:
            v = float(obs[0]) * self.vmax
            accel = min(accel, float(np.clip(0.5 * (self.wait_speed - v) / self.b_max, -1.0, 1.0)))
        return np.asarray([accel, lane], dtype=np.float32)
