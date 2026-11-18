#!/usr/bin/env bash
# BC + DAgger, β 쿨다운 (참고 비교, 평가 계획 3-1절 "β를 바꾼 것은 후보가 아니라 참고 비교로만 돌린다").
#   β = 0인 최종 모델(train_strict_model.sh)과 같은 BC(strict_0)에서 출발하고, 수집 시드·Episode 수·조건 비율·학습 설정이 같다.
#   다른 것은 β 하나: 라운드 1·2·3에서 β = 0.5, 0.25, 0.125 (스텝마다 이 확률로 expert가 대신 운전, 정답은 항상 expert).
#   예전 환경에서 계획했던 쿨다운 설정과 같다 (Ross, Gordon, Bagnell 2011의 β_i = p^(i) 꼴, p = 0.5).
#   결과: results/strict_beta_3/pretrained_model.pt. 검증 시드로만 평가한다 (최종 평가 시드는 다시 쓰지 않는다).
# 실행 (저장소 루트에서): bash scripts/training/strict_dagger_beta.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
WORKERS=${WORKERS:-8}
LOG=docs/training/strict/train_log.txt
DATA=(data/strict_rule_normal.npz data/strict_rule_xmas.npz data/strict_rule_xmasbus3.npz)
for f in "${DATA[@]}" results/strict_0/pretrained_model.pt; do [[ -f $f ]] || { echo "없음: $f"; exit 1; }; done
col() {
  local n=$1 s=$2; shift 2
  "$PY" collect_pomdp_data.py --workers "$WORKERS" --seed "$s" --name "$n" "$@"
  DATA+=("data/$n.npz")
}
prev=results/strict_0/pretrained_model.pt
for k in 1 2 3; do
  b=$(python3 -c "print(0.5 ** $k)")
  echo "[$(date +%H:%M)] β 쿨다운 라운드 $k (β = $b) 시작" >> $LOG
  col "strict_beta${k}_normal"   $((150+k)) --policy ppo --model "$prev" --label rule --beta "$b" --episodes 150
  col "strict_beta${k}_xmas"     $((160+k)) --policy ppo --model "$prev" --label rule --beta "$b" --episodes 150 --christmas
  col "strict_beta${k}_xmasbus3" $((170+k)) --policy ppo --model "$prev" --label rule --beta "$b" --episodes 100 --christmas --bus-scale 3
  "$PY" train.py --run-name "strict_beta_$k" --timesteps 0 --pretrain "${DATA[@]}"
  prev=results/strict_beta_$k/pretrained_model.pt
done
echo "[$(date +%H:%M)] β 쿨다운 끝: $prev" >> $LOG
