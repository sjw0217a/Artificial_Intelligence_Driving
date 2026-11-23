#!/bin/zsh
# β 쿨다운(참고 비교)이 끝나면 재현성 확인 → 센서 오차 실험을 차례로 돌린다 (CPU를 나눠 쓰지 않도록 하나씩).
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
export PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
until [[ -f docs/training/strict/val/bc_dagger_beta/xmasbus3_s3.json ]] && ! pgrep -f "strict_val.sh" >/dev/null && ! pgrep -f "strict_dagger_beta.sh" >/dev/null; do sleep 30; done
bash scripts/training/strict_seed_repro.sh
zsh scripts/training/strict_sensor_noise.sh
