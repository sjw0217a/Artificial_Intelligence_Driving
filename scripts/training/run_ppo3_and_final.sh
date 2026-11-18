#!/bin/zsh
# PPO 3차 학습 → 검증 → 선정(평가 계획 3-1절) → 최종 평가 한 번. 사람이 중간에 고르지 않도록 한 번에 돌린다.
#   PPO 후보: 1·2·3차 중 검증 실패(충돌·신호 위반·경로 이탈·시간초과) Episode 합계가 가장 적은 것.
# 실행 (저장소 루트에서): zsh scripts/training/run_ppo3_and_final.sh
cd "$(dirname "$0")/../.."
export SUMO_HOME=${SUMO_HOME:-~/src/sumo-1.27.1-mesa}
export PY=${PY:-~/miniforge3/envs/sumo-rl/bin/python}
LOG=docs/training/strict/train_log.txt
set -e
echo "[$(date +%H:%M)] PPO 3차(strict_ppo3) 학습 시작: 2차 + 신호 위반 즉시 종료(학습만)" >> $LOG
RUN=strict_ppo3 EXTRA=--warmup-value-head-only REWARD_EXTRA=red_light_terminate=1 \
  bash scripts/training/train_strict_ppo.sh > results/strict_ppo3.log 2>&1
echo "[$(date +%H:%M)] PPO 3차 학습 완료" >> $LOG
zsh scripts/training/strict_val.sh bc_ppo3 results/strict_ppo3/model.pt
$PY scripts/training/strict_select.py > docs/training/strict/val/selection_after_ppo3.txt
# PPO 후보 고르기: 검증 실패 합계가 가장 적은 PPO 시도
PPO_MODEL=$($PY - <<'EOF'
import json, os
root = "docs/training/strict/val"
def fails(m):
    n = 0
    for c in ("normal", "xmas", "xmas13", "xmasbus3"):
        for s in (1, 2, 3):
            for r in json.load(open(f"{root}/{m}/{c}_s{s}.json")):
                n += r["outcome"] != "arrived" or r.get("red_light", 0) > 0
    return n
cands = {m: fails(m) for m in ("bc_ppo", "bc_ppo2", "bc_ppo3")}
best = min(cands, key=cands.get)
open(f"{root}/ppo_candidate.txt", "w").write(f"PPO 시도별 검증 실패: {cands} → 후보 {best}\n")
print(open(f"{root}/{best}/model_path.txt").read().strip())
EOF
)
echo "[$(date +%H:%M)] $(cat docs/training/strict/val/ppo_candidate.txt) ($PPO_MODEL)" >> $LOG
PPO_MODEL=$PPO_MODEL zsh scripts/training/strict_eval.sh
$PY scripts/training/strict_select.py --final > docs/training/strict/final_eval/summary.txt
echo "[$(date +%H:%M)] 최종 평가 요약: docs/training/strict/final_eval/summary.txt" >> $LOG
