#!/bin/zsh
# 센서 오차 강건성 (새 모델): 최종 모델 관측에 센서 오차를 넣고 같은 시드(같은 교통)로 평가한다. 모델 선택에는 쓰지 않는다.
#   조건 2개(처음 보는 크리스마스 ×1.3, 충돌이 모인 버스 3배) x 시드 3개 x 100 Episode. 한 번도 안 쓴 시드 442001~3, 442011~3.
#   예전 모델 실험과 같은 설정 + 새 모델이 직접 신호를 보고 서므로 정지선 거리 오차(stop), 신호 인식 실패(red)를 더했다.
# 실행 (저장소 루트에서): zsh scripts/training/strict_sensor_noise.sh   → docs/training/strict/sensor_noise/
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
P=${P:-9}
M=models/strict_bc_dagger.pt
O=docs/training/strict/sensor_noise
mkdir -p $O
# 이름|--noise|--level|--smooth
SETTINGS=(
  "none|none|0|1"
  "dist05|dist|0.5|1"
  "dist1|dist|1|1"
  "dist2|dist|2|1"
  "dist1avg4|dist|1|4"
  "side10|side|0.1|1"
  "side30|side|0.3|1"
  "sideoff|sideoff|0|1"
  "delay1|delay|1|1"
  "delay2|delay|2|1"
  "stop1|stop|1|1"
  "stop2|stop|2|1"
  "red10|red|0.1|1"
)
CONDS=(
  "xmas13|--christmas --traffic 1.3|442000"
  "xmasbus3|--christmas --bus-scale 3|442010"
)
echo "[$(date +%H:%M)] 센서 오차 실험 시작 ($M)" >> docs/training/strict/train_log.txt
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
tr '\n' '\0' < $jobs_file | xargs -0 -P $P -n 1 zsh -c 'eval "$1"' _
rm -f $jobs_file
echo "[$(date +%H:%M)] 센서 오차 실험 끝" >> docs/training/strict/train_log.txt
