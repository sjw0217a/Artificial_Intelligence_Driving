# 명동 소공로 자율주행 (SUMO)

**[프로젝트 페이지](https://sjw0217a.github.io/Artificial_Intelligence_Driving/)** · [로컬 HTML](docs/index.html)

## 설치

SUMO 1.27.1을 설치하고 `SUMO_HOME`을 SUMO 설치 디렉터리로 설정합니다. 아래 명령은 저장소 루트에서 실행합니다.

```bash
export PATH="$SUMO_HOME/bin:$PATH"
python -m pip install -r requirements.txt
```

## 도로와 모델 실행

```bash
python view_road.py --nogui --seconds 600          # 도로 생성 및 10분 시뮬레이션 검증
python view_road.py --christmas --speed 4          # 크리스마스 교통을 GUI에서 4배속 재생
python test.py models/strict_bc_dagger.pt --christmas
```

평시는 `--christmas`를 생략합니다. 도로와 교통 설정은 [env/road_config.py](env/road_config.py)에서 변경합니다.

| 배포 체크포인트 | 모델 |
|---|---|
| `models/strict_bc.pt` | BC Only |
| `models/strict_bc_dagger.pt` | BC + DAgger (최종) |
| `models/strict_bc_ppo3.pt` | BC + PPO (3차) |

## 학습 재현

규칙 기반 운전자의 시연 1,000회로 BC를 학습한 뒤 DAgger를 400회씩 3라운드 수행합니다. BC 체크포인트는 `results/strict_0/pretrained_model.pt`, 최종 체크포인트는 `results/strict_3/pretrained_model.pt`에 저장됩니다.

```bash
WORKERS=8 bash scripts/training/train_strict_model.sh
```

비교용 PPO는 위에서 생성한 BC 체크포인트와 시연 데이터로 학습합니다. 다음 명령은 3차 실험 설정을 재현합니다.

```bash
RUN=strict_ppo3 EXTRA=--warmup-value-head-only REWARD_EXTRA=red_light_terminate=1 \
  bash scripts/training/train_strict_ppo.sh
```

## 평가 재현

아래는 공식 크리스마스 평가의 첫 번째 시드로 최종 모델을 100회 평가하는 예입니다. 같은 조건에서 체크포인트 경로만 바꾸면 세 모델을 비교할 수 있습니다.

```bash
python eval_section_time.py models/strict_bc_dagger.pt --christmas \
  --episodes 100 --eval-seed 2026111724 --json eval_xmas.json
```

공식 평가는 조건마다 아래 시드 3개를 각각 100회 사용합니다. 전체 실행 순서는 [평가 스크립트](scripts/training/strict_eval.sh), 에피소드별 원본은 [final_eval](docs/training/strict/final_eval/)에 있습니다.

| 조건 | 추가 옵션 | 평가 시드 |
|---|---|---|
| 평시 | 없음 | 2026111721–2026111723 |
| 크리스마스 | `--christmas` | 2026111724–2026111726 |
| 크리스마스 · 교통량 1.3배 | `--christmas --traffic 1.3` | 2026111727–2026111729 |
| 크리스마스 · 버스 3배 | `--christmas --bus-scale 3` | 2026111730–2026111732 |

## 주행 데이터 수집

```bash
python collect_pomdp_data.py --model models/strict_bc_dagger.pt \
  --episodes 1000 --workers 8 --seed 300 --name strict_normal
```

위 명령은 평시 데이터를 수집합니다. 크리스마스 데이터는 `--christmas`를 추가하고 `--name strict_xmas`로 구분합니다.
