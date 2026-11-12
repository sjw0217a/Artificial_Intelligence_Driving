#!/usr/bin/env bash
# 실험: 추월을 모르는 BC에서 출발해 PPO가 버스 추월을 스스로 찾는가 (결과: 찾지 못함).
#   관측은 최종 모델과 같은 37차원(버스 정차 [36] 포함). 시연하는 규칙만 추월을 끈다(overtake_bus=0).
#   기록: docs/training/학습_과정_기록.md 11.1절
#
# 실행 (저장소 루트에서):  bash scripts/training/ppo_overtake_experiment.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
WORKERS=${WORKERS:-6}
NO=(--rule-kw overtake_bus=0)
DATA=()

col() {  # $1 이름, $2 seed, 나머지: 추가 인자
  local n=$1 s=$2; shift 2
  "$PY" collect_pomdp_data.py --workers "$WORKERS" --seed "$s" --name "$n" "$@"
  DATA+=("data/$n.npz")
}

# 1) 추월하지 않는 규칙으로 시연 → BC → DAgger 1라운드
col noot_rule_normal   81 --policy rule --episodes 400 "${NO[@]}"
col noot_rule_xmas     82 --policy rule --episodes 400 --christmas "${NO[@]}"
col noot_rule_xmasbus3 83 --policy rule --episodes 200 --christmas --bus-scale 3 "${NO[@]}"
"$PY" train.py --run-name noot_0 --timesteps 0 --pretrain "${DATA[@]}"
col noot_dag1_normal   91 --policy ppo --model results/noot_0/pretrained_model.pt --label rule --episodes 150 "${NO[@]}"
col noot_dag1_xmas     92 --policy ppo --model results/noot_0/pretrained_model.pt --label rule --episodes 150 --christmas "${NO[@]}"
col noot_dag1_xmasbus3 93 --policy ppo --model results/noot_0/pretrained_model.pt --label rule --episodes 100 --christmas --bus-scale 3 "${NO[@]}"
"$PY" train.py --run-name noot_1 --timesteps 0 --pretrain "${DATA[@]}"

# 2) PPO: 버스 3배 + 평시·크리스마스 섞기, 신호 ① 통과 후에만 시간 벌점, 차선 탐험 강화.
#    BC 정규화 약하게(0.02) / 없음(0) 두 가지를 동시에 돌린다.
C=(--init results/noot_1/pretrained_model.pt --init-log-std -1.5 --critic-warmup 5 --mix-christmas --bus-scale 3
   --reward time_penalty_from_route_index=1 --eval-episodes 10 --timesteps 600000 --bc-data "${DATA[@]}")
"$PY" train.py --run-name noot_ppo_bc002 --bc-coef 0.02 --hparam lr=5e-5 lane_entropy_coef=0.03 "${C[@]}" &
"$PY" train.py --run-name noot_ppo_bc0               --hparam lr=5e-5 lane_entropy_coef=0.03 "${C[@]}" &
wait

# 3) 평가: "정차 버스를 본 Episode 중 추월 횟수"를 출발점(noot_1)과 비교
for m in results/noot_1/pretrained_model.pt results/noot_ppo_bc002/model.pt results/noot_ppo_bc0/model.pt; do
  echo "== $m"
  "$PY" eval_section_time.py "$m" --episodes 100 --christmas --bus-scale 3 --eval-seed 666001 | grep -E "에피소드 \||복잡|추월"
done
