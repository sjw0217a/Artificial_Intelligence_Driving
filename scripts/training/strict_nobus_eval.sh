#!/bin/zsh
# 관측 [37] 효과 비교 + 네 모델 비교 평가 (docs/training/strict/nobus_비교_계획.md). [37] 없는 모델 학습이 끝난 뒤 한 번만 돌린다.
#   시드 443001~443012 (한 번도 쓰지 않은 시드): 평시 01~03, 크리스마스 04~06, x1.3 07~09, 버스 3배 10~12.
#   결과: docs/training/strict/nobus_eval/<모델>/<조건>_s<1~3>.json
# 실행 (저장소 루트에서): zsh scripts/training/strict_nobus_eval.sh
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
P=${P:-10}
O=docs/training/strict/nobus_eval
typeset -A M F
M=(bc models/strict_bc.pt  bc_dagger models/strict_bc_dagger.pt  bc_dagger_beta models/strict_bc_dagger_beta.pt
   bc_ppo models/strict_bc_ppo3.pt  nobus models/strict_nobus_dagger.pt)
F=(bc 1  bc_dagger 1  bc_dagger_beta 1  bc_ppo 1  nobus 0)          # BUS_STOP_FLAG: [37]을 관측에 넣는가
for name mpath in ${(kv)M}; do [[ -f $mpath ]] || { echo "모델 없음: $mpath"; exit 1; }; done
[[ -e $O ]] && { echo "$O 가 이미 있다. 이 평가는 한 번만 돌린다"; exit 1; }
jobs_file=$(mktemp)
for name mpath in ${(kv)M}; do
  mkdir -p $O/$name
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
      echo "BUS_STOP_FLAG=${F[$name]} $PY eval_section_time.py $mpath --episodes 100 $A --eval-seed $((443000+i)) --json $O/$name/${c}_s$s.json > $O/$name/${c}_s$s.txt 2>&1" >> $jobs_file
    done
  done
done
tr '\n' '\0' < $jobs_file | xargs -0 -P $P -n 1 zsh -c 'eval "$1"' _
echo "끝: $O"
