#!/usr/bin/env bash
# BC + PPO (strict): BC 모델 results/strict_0에서 출발한 PPO 미세조정 (docs/training/strict/평가_계획.md 2절, 3-1절).
#   설정은 예전 PPO B(학습 과정 기록 11절)와 같다: 학습률 5e-5, 40만 step, 평시·크리스마스 섞기, 버스 3배,
#   시간 벌점은 신호 ① 통과 후부터, BC 정규화 0.1. BC 정규화 데이터는 expert 시연만 쓴다 (DAgger 데이터 안 씀).
#   평가에는 마지막 모델 results/<RUN>/model.pt를 쓴다 (best_model.pt는 쓰지 않는다).
#
#   시도 기록 (최대 3번, 평가 계획 3-1절):
#     1차 RUN=strict_ppo                     위 설정 그대로
#     2차 RUN=strict_ppo2 EXTRA=--warmup-value-head-only
#         1차 학습 로그에서 찾은 결함만 고침: critic warmup 5번 동안 가치 출력층만 바꾼다
#         (1차는 공유 앞단까지 바뀌어 정책이 흔들림: 첫 업데이트 approx_kl 0.47, 그 동안 BC 정규화도 꺼져 있었음)
#     3차 RUN=strict_ppo3 EXTRA=--warmup-value-head-only REWARD_EXTRA=red_light_terminate=1
#         2차 + 신호 위반을 충돌·경로 이탈처럼 즉시 종료(-5). 2차가 기준에서 떨어진 이유가 신호 위반 하나(1.9%)였다
#         (검증 시드 결과). 평가는 종전대로 종료 없이 끝까지 달리며 위반을 센다.
#
# 실행 (저장소 루트에서): RUN=strict_ppo2 EXTRA=--warmup-value-head-only bash scripts/training/train_strict_ppo.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
RUN=${RUN:-strict_ppo}
EXTRA=${EXTRA:-}
REWARD_EXTRA=${REWARD_EXTRA:-}   # --reward에 덧붙일 KEY=VALUE (--reward를 두 번 주면 앞의 것이 지워지므로 한 목록에 넣는다)
"$PY" train.py --run-name "$RUN" --timesteps 400000 --hparam lr=5e-5 --reward time_penalty_from_route_index=1 $REWARD_EXTRA \
  --mix-christmas --bus-scale 3 --eval-episodes 10 --init results/strict_0/pretrained_model.pt --init-log-std -1.5 \
  --bc-coef 0.1 --critic-warmup 5 $EXTRA \
  --bc-data data/strict_rule_normal.npz data/strict_rule_xmas.npz data/strict_rule_xmasbus3.npz
