# 명동 소공로 자율주행 (SUMO)

한국은행 앞 교차로 → 소공로(신세계백화점 본점 앞) → 회현사거리, 남쪽 방향 약 187 m.

## 설치

```bash
pip install -r requirements.txt
```

SUMO 설치는 따로 (1.27.1 기준, `SUMO_HOME` 환경변수 설정).

## 실행

```bash
python view_road.py                           # 평시, sumo-gui로 보기 (창이 뜨면 ▶ 눌러서 재생)
python view_road.py --christmas               # 크리스마스
python view_road.py --christmas --speed 4     # 4배속
python view_road.py --nogui --seconds 600     # 화면 없이 10분 돌려 설정 검증 (Waiting 0이면 정상)
```

| 옵션                     | 설명                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------- |
| `--christmas`            | 크리스마스 시나리오 (구경꾼 30% 감속 + 일반 차량 교통량 1.5배)                        |
| `--traffic X`            | 일반 차량 교통량 배율 X (기본 1.0, 크리스마스 배율과 곱해짐, 버스는 실제 배차 그대로) |
| `--speed X`              | GUI 재생 X배속 (1 = 실시간, 기본 2배속)                                               |
| `--background`           | 영상용 배경 교통 (남대문로 숭례문↔을지로 직진). 학습·데이터에는 쓰지 않음             |
| `--nogui`, `--seconds N` | 화면 없이 N초 돌리고 차량 통계 출력                                                   |
| `--seed X`               | 실험 seed고정 (예: `--seed 23423`)                                                    |
| 그 밖의 옵션             | SUMO에 그대로 넘김( `--window-size x,y`등)                                            |

## 학습 · 평가 · 데이터 수집

ego(빨간 차)는 을지로 → 서울역 고정 경로를 달린다. 관측 33차원, 행동 2차원(가감속, 차선변경).
아래 스크립트 모두 `--christmas`, `--traffic X`를 붙일 수 있다 (`train_bc.py` 제외).

```bash
mkdir -p results
python train.py 2>&1 | tee results/train_$(date +%m%d_%H%M).log     # PPO 학습 → results/run_날짜_시각/model.pt
python test.py results/run_xxx/model.pt --episodes 100 --nogui       # 평가: 충돌·완주·경로 이탈·시간초과·Teleport
python collect_pomdp_data.py --policy keep-lane --episodes 3         # 학습 없이 환경만 점검
python collect_pomdp_data.py --model results/run_xxx/model.pt --episodes 200 --workers 8   # 데이터 수집 → data/
python train_bc.py --data data/pomdp_xxx.npz                         # Behavior Cloning (NPZ로 학습)
```

| 바꿀 것                                   | 파일                                        |
| ----------------------------------------- | ------------------------------------------- |
| 학습 하이퍼파라미터, 보상 실험값          | `train.py` (`HPARAMS`, `REWARD_OVERRIDES`)  |
| 보상 기본값, 관측·행동 정의, Episode 길이 | `env/mdp_config.py`                         |
| 도로, 신호, 교통량, 크리스마스 설정       | `env/road_config.py`                        |

`env/sumo/`는 실행할 때마다 다시 만들어지는 파일이라 직접 고치지 않는다. 설계와 근거는 `docs/myeongdong_sumo_design.md`.

## 규칙

- 관측 [0~30]의 계산식·순서·정규화와 데이터의 기존 키는 바꾸거나 지우지 않는다. 새 값은 뒤에만 덧붙인다 (수업 규칙).
- 보상은 `env/mdp_config.py`의 기본값을 `train.py`의 `REWARD_OVERRIDES`가 덮어쓴다. 바꿀 때 두 곳을 같이 본다.
- 평가 지표(충돌, 완주, 경로 이탈, 시간초과, Teleport)는 따로 집계한다.
- `sumo`를 직접 돌릴 때는 `--step-length 0.5`를 준다 (생성되는 `highway.sumocfg`에는 step 길이가 없다).


