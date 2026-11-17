#!/bin/zsh
# 센서 오차 강건성: 최종 모델 관측에 센서 오차를 넣고 같은 시드(같은 교통)로 평가한다 (학습 과정 기록 11.8절).
#   조건 2개(처음 보는 크리스마스 ×1.3, 충돌이 모인 버스 3배) x 시드 3개 x 100 Episode. 새 시드 888xxx, 889xxx.
#   zsh scripts/training/sensor_noise.sh     # → docs/training/sensor_noise/ (맥북 9병렬 약 1시간)
cd ~/Artificial_Intelligence_Driving
export SUMO_HOME=~/src/sumo-1.27.1-mesa
PY=~/miniforge3/envs/sumo-rl/bin/python
M=models/bc_v3_3.pt
O=docs/training/sensor_noise
mkdir -p $O
# 이름|--noise|--level|--smooth (eval_sensor_noise.py 참고. smooth: 거리 값을 최근 K스텝 평균으로 쓰는 필터)
SETTINGS=(
  "none|none|0|1"
  "dist05|dist|0.5|1"
  "dist1|dist|1|1"
  "dist2|dist|2|1"
  "side10|side|0.1|1"
  "side30|side|0.3|1"
  "sideoff|sideoff|0|1"
  "delay1|delay|1|1"
  "delay2|delay|2|1"
  "dist1avg4|dist|1|4"
  "dist2avg4|dist|2|4"
)
CONDS=(
  "xmas13|--christmas --traffic 1.3|888000"
  "xmasbus3|--christmas --bus-scale 3|889000"
)
echo "[$(date +%H:%M)] 시작" > $O/log.txt
jobs_file=$(mktemp); : > $jobs_file
for v in $SETTINGS; do
  IFS="|" read -r name kind lv sm <<< "$v"
  for c in $CONDS; do
    cname=${c%%|*}; crest=${c#*|}; sargs=${crest%%|*}; base=${crest##*|}
    for s in 1 2 3; do
      out=$O/${cname}_${name}_s$s
      [[ -f $out.json ]] && continue
      echo "$PY eval_sensor_noise.py $M --noise $kind --level $lv --smooth $sm --episodes 100 $sargs --eval-seed $((base+s)) --json $out.json > $out.txt 2>&1" >> $jobs_file
    done
  done
done
echo "작업 $(wc -l < $jobs_file)개" >> $O/log.txt
tr '\n' '\0' < $jobs_file | xargs -0 -P 9 -n 1 zsh -c 'eval "$1"' _
echo "[$(date +%H:%M)] 끝" >> $O/log.txt
