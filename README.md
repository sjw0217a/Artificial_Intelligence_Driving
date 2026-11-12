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

공식 수치 (새 시드, 조건마다 300 Episode): 충돌은 평시 0, 크리스마스 0, 크리스마스 + 교통량 1.3배 0, 크리스마스 + 버스 3배 1회.
복잡 구간(S1~S2) 통과시간은 평시 15.2초, 크리스마스 21.3초다.


