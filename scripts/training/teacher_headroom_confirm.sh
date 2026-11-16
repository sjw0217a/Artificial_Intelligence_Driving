#!/bin/zsh
# 1차(teacher_headroom.sh)에서 빨랐던 선생 설정을 새 시드에서 다시 확인한다 (10개 중 1등은 우연일 수 있으므로).
#   조건 4개 x 시드 3개 x 100 Episode, 기본 선생과 같은 시드라 Episode마다 교통이 같다.
#   zsh scripts/training/teacher_headroom_confirm.sh     # → docs/training/teacher_headroom/confirm/ (맥북 10병렬 약 1시간)
cd ~/Artificial_Intelligence_Driving
export SUMO_HOME=~/src/sumo-1.27.1-mesa
PY=~/miniforge3/envs/sumo-rl/bin/python
O=docs/training/teacher_headroom/confirm
mkdir -p $O
VARIANTS=(
  "base|"
  "th08|time_headway=0.8"
  "aggr|time_headway=0.9 min_gap=1.5 front_gap=2 rear_gap=2 wait_speed=8"
  "aggr_w5|time_headway=0.9 min_gap=1.5 front_gap=2 rear_gap=2"
)
CONDS=(
  "normal||884000"
  "xmas|--christmas|885000"
  "xmas13|--christmas --traffic 1.3|886000"
  "xmasbus3|--christmas --bus-scale 3|887000"
)
echo "[$(date +%H:%M)] 시작" > $O/log.txt
jobs_file=$(mktemp); : > $jobs_file
for v in $VARIANTS; do
  name=${v%%|*}; kw=${v#*|}
  for c in $CONDS; do
    cname=${c%%|*}; rest=${c#*|}; sargs=${rest%%|*}; base=${rest##*|}
    for s in 1 2 3; do
      out=$O/${cname}_${name}_s$s
      [[ -f $out.json ]] && continue
      rk=""; [[ -n $kw ]] && rk="--rule-kw $kw"
      echo "$PY eval_section_time.py --algorithm rule --episodes 100 $sargs --eval-seed $((base+s)) $rk --json $out.json > $out.txt 2>&1" >> $jobs_file
    done
  done
done
echo "작업 $(wc -l < $jobs_file)개" >> $O/log.txt
tr '\n' '\0' < $jobs_file | xargs -0 -P 10 -n 1 zsh -c 'eval "$1"' _
echo "[$(date +%H:%M)] 끝" >> $O/log.txt
