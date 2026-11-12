#!/usr/bin/env bash
# 최종 모델(v3_3) 만들기: 규칙 기반 시연 → BC → DAgger 3라운드.
#   관측 37차원 (env/mdp_config.py 기본값). 규칙은 정류장 버스를 추월한다.
#   결과: results/dagv3_3/pretrained_model.pt  (= models/bc_v3_3.pt)
#
# 실행 (저장소 루트에서):  bash scripts/training/train_final_model.sh
#   PY=python 실행 파일, WORKERS=병렬 수 로 바꿀 수 있다. 맥북 8병렬 기준 약 4~5시간.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
WORKERS=${WORKERS:-8}
DATA=()

col() {  # $1 이름, $2 seed, 나머지: 추가 인자
  local n=$1 s=$2; shift 2
  "$PY" collect_pomdp_data.py --workers "$WORKERS" --seed "$s" --name "$n" "$@"
  DATA+=("data/$n.npz")
}

# 1) 규칙 기반 시연: 평시 400 + 크리스마스 400 + 크리스마스·버스 3배 200 Episode
col v3_rule_normal   41 --policy rule --episodes 400
col v3_rule_xmas     42 --policy rule --episodes 400 --christmas
col v3_rule_xmasbus3 43 --policy rule --episodes 200 --christmas --bus-scale 3

# 2) BC: PPO 네트워크를 시연에 지도학습 (--timesteps 0 이면 PPO는 돌리지 않는다)
"$PY" train.py --run-name dagv3_0 --timesteps 0 --pretrain "${DATA[@]}"

# 3) DAgger 3라운드: 직전 모델이 운전하고, 규칙이 매 순간의 정답을 붙인다 (라운드마다 400 Episode)
for k in 1 2 3; do
  prev=results/dagv3_$((k-1))/pretrained_model.pt
  col "v3_dag${k}_normal"   $((50+k)) --policy ppo --model "$prev" --label rule --episodes 150
  col "v3_dag${k}_xmas"     $((60+k)) --policy ppo --model "$prev" --label rule --episodes 150 --christmas
  col "v3_dag${k}_xmasbus3" $((70+k)) --policy ppo --model "$prev" --label rule --episodes 100 --christmas --bus-scale 3
  "$PY" train.py --run-name "dagv3_$k" --timesteps 0 --pretrain "${DATA[@]}"
done

echo "최종 모델: results/dagv3_3/pretrained_model.pt"
