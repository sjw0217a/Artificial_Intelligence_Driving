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

## AV 모델 학습

최종 모델은 `models/bc_v3_3.pt`다 (관측 37차원). 규칙 기반 운전자의 시연으로 BC를 학습하고 DAgger 3라운드를 거쳤다.

- 학습 과정 전체 (무엇을 왜 했고 무엇이 실패했는지): [docs/training/학습_과정_기록.md](docs/training/학습_과정_기록.md)
- 모델 인계, 성능, 데이터 수집 명령: [docs/training/모델_인계.md](docs/training/모델_인계.md)

```bash
python test.py models/bc_v3_3.pt --christmas                                 # sumo-gui로 주행 보기
python eval_section_time.py models/bc_v3_3.pt --episodes 100 --christmas      # 충돌률, 복잡 구간 통과시간
python collect_pomdp_data.py --model models/bc_v3_3.pt --episodes 1000 --workers 8 --seed 100 --name final_normal
bash scripts/training/train_final_model.sh                                    # 최종 모델을 처음부터 다시 학습
```

### 결과

![버스 추월 비교](docs/training/video/bus_overtake_compare.gif)

크리스마스, 같은 교통에서 왼쪽은 1단계 BC(추월을 안 배움), 오른쪽은 최종 모델이다 (2배속, 빨간 원이 자율주행차, 흰색이 정류장에 선 버스).
최종 모델은 정류장에 선 버스를 보면(관측 [36]) 합류점 앞에서 왼쪽으로 한 칸 옮겨 정류장 옆 차로로 지나가고, 넓어지는 S2에서 맨 오른쪽 출구 차로로 돌아간다. 이 장면에서 복잡 구간을 37.5초 → 14.0초에 통과했다.
버스를 만난 장면 중 차이가 큰 편인 장면이고, 평균은 아래 표와 같다. 원본 영상(64초, 확대 장면과 결과 화면 포함): [bus_overtake_compare.mp4](docs/training/video/bus_overtake_compare.mp4)

![추월 순간 확대](docs/training/video/bus_overtake_zoom.gif)

같은 장면의 최종 모델만 0.5배속으로 확대했다. 출구 때문에 맨 오른쪽 차로로 갔다가, 80 m 앞 정류장에 선 버스를 감지하면(관측 [36]) 합류점 직후 왼쪽으로 한 칸 옮겨 정류장 옆을 지나가고, 넓어진 S2에서 맨 오른쪽으로 돌아간다.

공식 평가: 최종 모델을 정한 뒤, 한 번도 쓰지 않은 시드로 조건마다 300 Episode를 한 번만 평가했다.
비교 대상(1단계 BC)도 같은 시드로 돌려서 Episode마다 교통이 같다.

| 조건 | 충돌 (최종) | 복잡 구간 평균 (1단계 BC → 최종) | 버스를 만난 Episode (1단계 BC → 최종) |
|---|---|---|---|
| 평시 | 0 / 300 | 15.6 → 15.2초 | 25.3 → 16.1초 |
| 크리스마스 | 0 / 300 | 22.6 → 21.3초 | 37.7 → 26.0초 |
| 크리스마스 + 교통량 1.3배 (학습에 안 쓴 조건) | 0 / 300 | 25.0 → 23.4초 | 37.9 → 27.5초 |
| 크리스마스 + 버스 3배 | 1 / 300 | 30.0 → 22.7초 | 39.9 → 24.3초 |

![공식 시드 비교](docs/training/official_compare.png)

- 정류장에 선 버스를 만나는 Episode는 평시 4%, 크리스마스 9%라서 전체 평균은 조금만 줄고, 버스를 만났을 때 10초 안팎이 줄어든다.
- 시간 단축은 PPO가 아니라 관측 [36](정류장 버스 정차)과 추월을 보여 준 시연(모방학습)에서 나왔다. PPO 미세조정은 시간을 유의하게 줄이지 못하고 충돌만 늘렸다. 줄일 수 있는 시간이 드문 버스 장면에만 있고, 추월은 여러 단계 행동이라 무작위 탐험으로 찾기 어렵기 때문이다 (학습 과정 기록 11.4~11.5절).
- 전체 도착시간 약 190초 중 약 125초는 신호 ① 적신호 대기라 운전으로 줄일 수 없어서, 시간은 복잡 구간(S1~S2)으로 비교한다.
