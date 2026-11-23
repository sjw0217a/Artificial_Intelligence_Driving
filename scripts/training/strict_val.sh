#!/bin/zsh
# strict 후보 검증 평가 (docs/training/strict/평가_계획.md 3-1절): 검증 시드 441101~441112로 모델을 고른다.
#   배정: 평시 01~03, 크리스마스 04~06, x1.3 07~09, 버스 3배 10~12 (앞에 4411을 붙인다). 조건마다 3 x 100 Episode.
#   결과: docs/training/strict/val/<이름>/<조건>_s<1~3>.json
# 실행 (저장소 루트에서): zsh scripts/training/strict_val.sh 이름 모델경로 [이름 모델경로 ...]
#   예: zsh scripts/training/strict_val.sh bc results/strict_0/pretrained_model.pt bc_dagger results/strict_3/pretrained_model.pt
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
P=${P:-10}
O=docs/training/strict/val
(( $# >= 2 && $# % 2 == 0 )) || { echo "사용법: $0 이름 모델경로 [이름 모델경로 ...]"; exit 1; }
jobs_file=$(mktemp)
while (( $# )); do
  name=$1 mpath=$2; shift 2
  [[ -f $mpath ]] || { echo "모델 없음: $mpath"; exit 1; }
  [[ -e $O/$name ]] && { echo "$O/$name 이 이미 있다 (같은 이름으로 다시 돌리지 않는다)"; exit 1; }
  mkdir -p $O/$name
  echo "$mpath" > $O/$name/model_path.txt
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
      echo "$PY eval_section_time.py $mpath --episodes 100 $A --eval-seed $((441100+i)) --json $O/$name/${c}_s$s.json > $O/$name/${c}_s$s.txt 2>&1" >> $jobs_file
    done
  done
done
echo "[$(date +%H:%M)] 검증 평가 시작: $(awk '{print $3}' $jobs_file | sort -u | tr '\n' ' ')" >> docs/training/strict/train_log.txt
tr '\n' '\0' < $jobs_file | xargs -0 -P $P -n 1 zsh -c 'eval "$1"' _
echo "[$(date +%H:%M)] 검증 평가 끝" >> docs/training/strict/train_log.txt
rm -f $jobs_file
