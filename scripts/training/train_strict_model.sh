#!/usr/bin/env bash
# 보조 규칙을 뺀 모델(strict) 만들기: 규칙 기반 시연 → BC → DAgger 3라운드 (교수님 Q&A 반영).
#   최종 모델 v3_3(scripts/training/train_final_model.sh)과 Episode 수·조건 비율·학습 설정이 같고, 환경만 다르다.
#     - ego speed_mode 0: 적신호 정지·교차로 양보를 SUMO가 대신하지 않는다
#     - 관측 38차원: [33..34] 측면 레이더(SUMO 차선변경 판정 안 씀), [35..36] 다음 회전 방향·거리(차선 단위 안내 안 씀)
#   선생(utils/rule_policy.py)은 학습 정답을 만들 때만 쓴다. 주행은 신경망이 관측만 보고 한다.
#   결과: results/strict_3/pretrained_model.pt
#
# 실행 (저장소 루트에서):  bash scripts/training/train_strict_model.sh
#   PY=python 실행 파일, WORKERS=병렬 수 로 바꿀 수 있다.
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
col strict_rule_normal   141 --policy rule --episodes 400
col strict_rule_xmas     142 --policy rule --episodes 400 --christmas
col strict_rule_xmasbus3 143 --policy rule --episodes 200 --christmas --bus-scale 3
# 2) BC
"$PY" train.py --run-name strict_0 --timesteps 0 --pretrain "${DATA[@]}"
# 3) DAgger 3라운드: 직전 모델이 운전하고, 규칙이 매 순간의 정답을 붙인다 (라운드마다 400 Episode, β = 0)
for k in 1 2 3; do
  prev=results/strict_$((k-1))/pretrained_model.pt
  col "strict_dag${k}_normal"   $((150+k)) --policy ppo --model "$prev" --label rule --episodes 150
  col "strict_dag${k}_xmas"     $((160+k)) --policy ppo --model "$prev" --label rule --episodes 150 --christmas
  col "strict_dag${k}_xmasbus3" $((170+k)) --policy ppo --model "$prev" --label rule --episodes 100 --christmas --bus-scale 3
  "$PY" train.py --run-name "strict_$k" --timesteps 0 --pretrain "${DATA[@]}"
done
echo "strict 모델: results/strict_3/pretrained_model.pt"
