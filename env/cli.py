"""실행 스크립트 공통 옵션 — road_config/mdp_config 파일은 그대로 두고 이번 실행에서만 바꾼다.

    --christmas    TRAFFIC["christmas"]["enabled"]를 켠다 (교통량 traffic_scale배 + 구경 감속)
    --traffic X    일반 차량 교통량 배율. 진입로 entries에 곱한다 (크리스마스 배율과 곱해짐, 버스는 그대로)
    --background   (GUI 스크립트만) 영상용 배경 교통(남대문로 직진)을 켠다
    --speed X      (GUI 스크립트만) 재생 배속. 1 = 실시간, 2 = 2배속. 생략하면 mdp_config의 gui_delay
"""
import atexit
import os
import shutil
import tempfile


def private_sumo_dir(base):
    """이번 실행만 쓰는 도로 파일 폴더(env/sumo/tmp_xxx)를 만들고, 끝나면 지운다.

    도로 파일은 실행할 때마다 다시 만들고 에피소드마다 SUMO가 다시 읽는다. 여러 실행이
    env/sumo 한 폴더를 같이 쓰면, 평시 학습 중에 크리스마스 평가를 돌리는 순간 학습 쪽
    도로까지 크리스마스로 바뀐다. 그래서 학습·평가·수집은 실행마다 폴더를 나눈다.
    """
    root = os.path.join(base, "env", "sumo")
    os.makedirs(root, exist_ok=True)
    path = tempfile.mkdtemp(prefix="tmp_", dir=root)
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def add_scenario_args(parser, gui=False):
    parser.add_argument("--christmas", action="store_true",
                        help="크리스마스 시나리오로 실행 (road_config 파일은 그대로)")
    parser.add_argument("--traffic", type=float, default=1.0,
                        help="일반 차량 교통량 배율 (기본 1.0, 크리스마스 배율과 곱해짐, 버스 제외)")
    parser.add_argument("--bus-scale", type=float, default=1.0,
                        help="버스 배차 빈도 배율 (기본 1.0). 학습에서 '정차 버스 뒤에 막힘' 상황을 자주 겪게 할 때 사용")
    if gui:
        parser.add_argument("--background", action="store_true",
                            help="영상용 배경 교통(남대문로 숭례문↔을지로 직진)을 켠다")
        parser.add_argument("--speed", type=float, default=None,
                            help="GUI 재생 배속 (1 = 실시간). 생략하면 mdp_config의 gui_delay")


def apply_scenario_args(args, traffic, sim):
    """args를 반영한 (traffic, sim) 사본을 돌려준다. 원본 dict는 바꾸지 않는다."""
    if args.traffic < 0:
        raise ValueError("--traffic은 0 이상이어야 합니다.")
    traffic = {**traffic, "entries": {k: v * args.traffic for k, v in traffic["entries"].items()}}
    if args.christmas:
        traffic["christmas"] = {**traffic["christmas"], "enabled": True}
    bus_scale = float(getattr(args, "bus_scale", 1.0))
    if bus_scale <= 0:
        raise ValueError("--bus-scale은 0보다 커야 합니다.")
    if bus_scale != 1.0 and traffic.get("bus"):
        traffic["bus"] = {**traffic["bus"], "lines": {k: (e, x, h / bus_scale)
                                                      for k, (e, x, h) in traffic["bus"]["lines"].items()}}
    if getattr(args, "background", False):
        traffic["background"] = {**traffic["background"], "enabled": True}
    speed = getattr(args, "speed", None)
    if speed is not None:
        if speed <= 0:
            raise ValueError("--speed는 0보다 커야 합니다.")
        # 스텝 하나(step_length 초)를 1/배속 만큼의 실제 시간에 보여준다
        sim = {**sim, "gui_delay": sim["step_length"] * 1000.0 / speed}

    xmas = traffic["christmas"]
    print(f"시나리오: {'크리스마스' if xmas['enabled'] else '평시'}"
          f" | 교통량 x{args.traffic * (xmas['traffic_scale'] if xmas['enabled'] else 1.0):g}"
          + (f" | 버스 x{bus_scale:g}" if bus_scale != 1.0 else "")
          + (" | 배경 교통 켬" if traffic.get("background", {}).get("enabled") else "")
          + (f" | {speed:g}배속 (delay {sim['gui_delay']:.0f} ms)" if speed else ""))
    return traffic, sim
