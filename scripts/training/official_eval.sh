#!/usr/bin/env bash
# 최종 모델 공식 평가 (11/12에 딱 한 번 실행).
#   시드 2026111201~12는 이 평가에 처음이자 마지막으로 썼다. 결과: docs/training/official_eval/
#   이미 결과를 본 시드이므로, 새 모델을 공정하게 평가하려면 다른 시드를 새로 정해야 한다.
#   11/13에 비교 대상(1단계 BC)만 같은 시드로 돌렸다 (모델 선택에는 안 씀):
#     BUS_STOP_FLAG=0 bash scripts/training/official_eval.sh models/bc_dag3_36dim.pt
#
# 실행 (저장소 루트에서):  bash scripts/training/official_eval.sh [모델] [결과 폴더]
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
M=${1:-models/bc_v3_3.pt}
O=${2:-results/official}
mkdir -p "$O"

i=0
for c in normal xmas xmas13 xmasbus3; do
  case $c in
    normal)   A=() ;;
    xmas)     A=(--christmas) ;;
    xmas13)   A=(--christmas --traffic 1.3) ;;     # 학습에 한 번도 안 쓴 조건
    xmasbus3) A=(--christmas --bus-scale 3) ;;     # 학습에 일부 쓴 조건 (스트레스 테스트)
  esac
  for s in 1 2 3; do
    i=$((i+1)); seed=$((2026111200+i))
    "$PY" eval_section_time.py "$M" --episodes 100 ${A[@]+"${A[@]}"} --eval-seed "$seed" \
      --json "$O/${c}_s$s.json" > "$O/${c}_s$s.txt" 2>&1 &
  done
done
wait
grep -h -E "에피소드 \||복잡 구간" "$O"/*_s?.txt
