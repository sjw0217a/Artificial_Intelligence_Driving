#!/bin/zsh
# strict 세 모델 최종 평가 (docs/training/strict/평가_계획.md 3절). 세 모델 학습이 모두 끝난 뒤 한 번만 돌린다.
#   시드 2026111721~32 (한 번도 쓰지 않은 시드): 평시 21~23, 크리스마스 24~26, x1.3 27~29, 버스 3배 30~32.
#   조건마다 시드 3개 x 100 Episode. 세 모델이 같은 시드라 Episode마다 교통이 같다.
#   결과: docs/training/strict/final_eval/<모델>/<조건>_s<1~3>.json
#   BC + PPO 후보는 PPO 시도 중 검증 실패 합계가 가장 적은 것 (PPO_MODEL로 넘긴다, 평가 계획 3-1절).
# 실행 (저장소 루트에서): PPO_MODEL=results/strict_ppo2/model.pt zsh scripts/training/strict_eval.sh
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
P=${P:-10}
O=docs/training/strict/final_eval
[[ -n $PPO_MODEL ]] || { echo "PPO_MODEL을 정해야 한다 (검증에서 고른 PPO 후보)"; exit 1; }
typeset -A M
M=(bc        results/strict_0/pretrained_model.pt
   bc_dagger results/strict_3/pretrained_model.pt
   bc_ppo    $PPO_MODEL)
for name mpath in ${(kv)M}; do
  [[ -f $mpath ]] || { echo "모델 없음: $mpath"; exit 1; }
done
[[ -e $O ]] && { echo "$O 가 이미 있다. 최종 평가는 한 번만 돌린다"; exit 1; }
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
      echo "$PY eval_section_time.py $mpath --episodes 100 $A --eval-seed $((2026111720+i)) --json $O/$name/${c}_s$s.json > $O/$name/${c}_s$s.txt 2>&1" >> $jobs_file
    done
  done
done
echo "[$(date +%H:%M)] 최종 평가 시작 ($(wc -l < $jobs_file)개 작업)" >> docs/training/strict/train_log.txt
tr '\n' '\0' < $jobs_file | xargs -0 -P $P -n 1 zsh -c 'eval "$1"' _
echo "[$(date +%H:%M)] 최종 평가 끝" >> docs/training/strict/train_log.txt
rm -f $jobs_file
