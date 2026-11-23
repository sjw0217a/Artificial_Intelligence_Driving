#!/bin/zsh
# expert(규칙)를 검증 시드(441101~441112)로 평가한다. 학생이 expert를 얼마나 따라갔는지 보는 참고용이다.
#   모델 선택에는 쓰지 않는다 (선택은 val/에서 이미 끝남). 최종 평가 시드는 다시 쓰지 않는다.
#   결과: docs/training/strict/expert_val/<조건>_s<1~3>.json
# 실행 (저장소 루트에서): zsh scripts/training/strict_expert_val.sh
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
P=${P:-10}
O=docs/training/strict/expert_val
[[ -e $O ]] && { echo "$O 가 이미 있다"; exit 1; }
mkdir -p $O
jobs_file=$(mktemp)
i=0
for c in normal xmas xmas13 xmasbus3; do
  case $c in
    normal) A="";;
    xmas) A="--christmas";;
    xmas13) A="--christmas --traffic 1.3";;
    xmasbus3) A="--christmas --bus-scale 3";;
  esac
  for s in 1 2 3; do
    i=$((i+1))
    echo "$PY eval_section_time.py --algorithm rule --episodes 100 $A --eval-seed $((441100+i)) --json $O/${c}_s$s.json > $O/${c}_s$s.txt 2>&1" >> $jobs_file
  done
done
echo "[$(date +%H:%M)] expert 검증 시드 평가 시작 (참고용, 모델 선택에 안 씀)" >> docs/training/strict/train_log.txt
tr '\n' '\0' < $jobs_file | xargs -0 -P $P -n 1 zsh -c 'eval "$1"' _
echo "[$(date +%H:%M)] expert 검증 시드 평가 끝" >> docs/training/strict/train_log.txt
rm -f $jobs_file
