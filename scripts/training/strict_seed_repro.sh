#!/usr/bin/env bash
# 재현성 확인: 최종 모델(strict_3)과 같은 데이터(시연 + DAgger 3라운드, 840,864 step)로 학습 시드만 1, 2로 바꿔 다시 학습한다.
#   학습 시드에 따른 흔들림만 잰다 (DAgger 수집을 다시 하지는 않는다). 검증 시드로 평가하고, 모델 선택에는 쓰지 않는다.
#   결과: results/strict_3_seed{1,2}/pretrained_model.pt, docs/training/strict/val/bc_dagger_seed{1,2}/
# 실행 (저장소 루트에서): bash scripts/training/strict_seed_repro.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-python}
LOG=docs/training/strict/train_log.txt
DATA=$("$PY" -c "import json;print(' '.join(json.load(open('docs/training/strict/run_logs/strict_3_cli_args.json'))['pretrain']))")
for s in 1 2; do
  echo "[$(date +%H:%M)] 재현성: 학습 시드 $s로 다시 학습 시작" >> $LOG
  "$PY" train.py --run-name "strict_3_seed$s" --timesteps 0 --pretrain $DATA --hparam seed=$s > "results/strict_3_seed$s.log" 2>&1
done
PY=$PY zsh scripts/training/strict_val.sh bc_dagger_seed1 results/strict_3_seed1/pretrained_model.pt bc_dagger_seed2 results/strict_3_seed2/pretrained_model.pt
