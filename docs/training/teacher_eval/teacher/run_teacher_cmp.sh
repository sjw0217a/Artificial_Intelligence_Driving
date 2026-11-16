#!/bin/zsh
# 선생(규칙, 최종 시연과 같은 기본 설정: 버스 추월 80 m) vs 최종 모델 비교.
# 10.7절 검증용 시드(평시 99000x, 크리스마스 99100x, x1.3 99200x, 버스 3배 99300x)를 그대로 써서 Episode마다 교통이 같다.
cd ~/Artificial_Intelligence_Driving
export SUMO_HOME=~/src/sumo-1.27.1-mesa
PY=~/miniforge3/envs/sumo-rl/bin/python
O=docs/training/teacher_eval/teacher
echo "[$(date +%H:%M)] 시작" > $O/log.txt
for c in normal xmas xmas13 xmasbus3; do
  case $c in
    normal) A=(); b=990000;;
    xmas) A=(--christmas); b=991000;;
    xmas13) A=(--christmas --traffic 1.3); b=992000;;
    xmasbus3) A=(--christmas --bus-scale 3); b=993000;;
  esac
  for s in 1 2 3; do
    $PY eval_section_time.py --algorithm rule --episodes 100 $A --eval-seed $((b+s)) --json $O/${c}_s$s.json > $O/${c}_s$s.txt 2>&1 &
  done
done
wait
echo "[$(date +%H:%M)] 끝" >> $O/log.txt
