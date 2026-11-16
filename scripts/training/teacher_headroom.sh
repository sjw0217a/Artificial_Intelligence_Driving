#!/bin/zsh
# 선생(규칙)을 넘을 여지 측정: 선생 설정을 여러 개로 바꿔 같은 시드(같은 교통)에서 돌린다.
#   Episode마다 가장 빠른 설정을 고르면 "매 장면 최선의 판단"의 상한처럼 보인다 (학습 과정 기록 11.7절).
#   미세 변형(null_*)은 대조군으로 넣었지만 교통이 거의 안 바뀌어 착시 측정에는 쓰지 못했다.
#   다만 여러 결과 중 최솟값은 운만으로도 작아지므로, analyze_headroom.py가 그 착시 크기를 함께 잰다.
#
#   zsh scripts/training/teacher_headroom.sh        # → docs/training/teacher_headroom/round1/ (맥북 10병렬 약 1시간)
cd ~/Artificial_Intelligence_Driving
export SUMO_HOME=~/src/sumo-1.27.1-mesa
PY=~/miniforge3/envs/sumo-rl/bin/python
O=docs/training/teacher_headroom/round1
mkdir -p $O

# 이름|RulePolicy 인자 (기본값: time_headway 1.2, min_gap 2.0, front/rear_gap 3.0, wait_speed 5.0, spawn_protect 60)
VARIANTS=(
  "base|"
  "th08|time_headway=0.8"
  "th16|time_headway=1.6"
  "gap1|min_gap=1.0"
  "wait3|wait_speed=3"
  "wait8|wait_speed=8"
  "accept2|front_gap=2 rear_gap=2"
  "accept5|front_gap=5 rear_gap=5"
  "spawn30|spawn_protect=30"
  "slow|overtake_slow=1"
  "aggr|time_headway=0.9 min_gap=1.5 front_gap=2 rear_gap=2 wait_speed=8"
  "null_a|time_headway=1.201"
  "null_b|time_headway=1.199"
  "null_c|min_gap=2.001"
  "null_d|min_gap=1.999"
)
# 조건|시나리오 인자|시드 기준 (새 시드: 지금까지 학습·평가에 쓰지 않은 값)
CONDS=(
  "xmas|--christmas|881000"
  "xmasbus3|--christmas --bus-scale 3|883000"
)

echo "[$(date +%H:%M)] 시작" > $O/log.txt
jobs_file=$(mktemp); : > $jobs_file
for v in $VARIANTS; do
  name=${v%%|*}; kw=${v#*|}
  for c in $CONDS; do
    cname=${c%%|*}; rest=${c#*|}; sargs=${rest%%|*}; base=${rest##*|}
    for s in 1 2; do
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
