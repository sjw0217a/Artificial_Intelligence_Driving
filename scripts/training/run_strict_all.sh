#!/usr/bin/env bash
# strict 세 모델 학습을 한 번에: BC → (DAgger 3라운드 ‖ PPO). docs/training/strict/평가_계획.md 2절.
#   BC 모델(strict_0)이 다 저장되면(model.pt까지) PPO를 시작하고, DAgger는 그대로 이어서 돈다.
# 실행 (저장소 루트에서): bash scripts/training/run_strict_all.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
export PY=${PY:-python}
LOG=docs/training/strict/train_log.txt
mkdir -p docs/training/strict results data
echo "[$(date +%H:%M)] 시작" >> $LOG
bash scripts/training/train_strict_model.sh > results/strict_dagger.log 2>&1 &
DAG=$!
until [ -f results/strict_0/model.pt ]; do
  kill -0 $DAG 2>/dev/null || { echo "[$(date +%H:%M)] BC 단계 실패 (results/strict_dagger.log)" >> $LOG; exit 1; }
  sleep 30
done
echo "[$(date +%H:%M)] BC(strict_0) 완료 → PPO 시작" >> $LOG
bash scripts/training/train_strict_ppo.sh > results/strict_ppo.log 2>&1 &
PPO=$!
wait $DAG && echo "[$(date +%H:%M)] BC+DAgger(strict_3) 완료" >> $LOG || echo "[$(date +%H:%M)] DAgger 실패" >> $LOG
wait $PPO && echo "[$(date +%H:%M)] BC+PPO(strict_ppo) 완료" >> $LOG || echo "[$(date +%H:%M)] PPO 실패" >> $LOG
