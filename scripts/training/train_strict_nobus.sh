#!/usr/bin/env bash
# 비교용: 관측 [37](정류장 버스 정차)만 뺀 모델. 최종 모델(train_strict_model.sh)과 다른 것은 BUS_STOP_FLAG=0 하나다.
#   expert 시연 Episode 수·조건 비율·수집 시드(141~173)·BC 설정·DAgger 3라운드가 모두 같다.
#   expert는 버스 정차를 SUMO에서 직접 보므로(utils/rule_policy.py) 시연에는 추월이 그대로 들어간다.
#   학생만 관측 37칸이라 "앞에 선 차가 정류장 버스인지"를 모른다.
#   결과: results/strict_nobus_3/pretrained_model.pt (models/strict_nobus_dagger.pt로 복사)
#
# 실행 (저장소 루트에서):  bash scripts/training/train_strict_nobus.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
export BUS_STOP_FLAG=0
PY=${PY:-python}
WORKERS=${WORKERS:-8}
DATA=()
col() {
  local n=$1 s=$2; shift 2
  "$PY" collect_pomdp_data.py --workers "$WORKERS" --seed "$s" --name "$n" "$@"
  DATA+=("data/$n.npz")
}
col strict_nobus_rule_normal   141 --policy rule --episodes 400
col strict_nobus_rule_xmas     142 --policy rule --episodes 400 --christmas
col strict_nobus_rule_xmasbus3 143 --policy rule --episodes 200 --christmas --bus-scale 3
"$PY" train.py --run-name strict_nobus_0 --timesteps 0 --pretrain "${DATA[@]}"
for k in 1 2 3; do
  prev=results/strict_nobus_$((k-1))/pretrained_model.pt
  col "strict_nobus_dag${k}_normal"   $((150+k)) --policy ppo --model "$prev" --label rule --episodes 150
  col "strict_nobus_dag${k}_xmas"     $((160+k)) --policy ppo --model "$prev" --label rule --episodes 150 --christmas
  col "strict_nobus_dag${k}_xmasbus3" $((170+k)) --policy ppo --model "$prev" --label rule --episodes 100 --christmas --bus-scale 3
  "$PY" train.py --run-name "strict_nobus_$k" --timesteps 0 --pretrain "${DATA[@]}"
done
cp results/strict_nobus_3/pretrained_model.pt models/strict_nobus_dagger.pt
echo "[37] 없는 모델: models/strict_nobus_dagger.pt"
