"""시드에 따른 흔들림을 평균 ± 표준편차로 정리한다 (새 실행 없이 저장된 Episode별 JSON만 읽음).

1) 평가 시드: 최종 평가는 조건마다 시드 3개(s1~s3) × 100 Episode다.
   - 조건별: 시드 3개의 100 Episode당 횟수 → 평균 ± 표준편차
   - 전체: s1, s2, s3를 각각 한 반복(4 조건 × 100 = 400 Episode)으로 보고 비율(%) → 평균 ± 표준편차
2) 학습 시드: BC + DAgger를 학습 시드 0, 1, 2로 학습한 세 모델의 검증 결과(각 1,200 Episode) → 평균 ± 표준편차.
   BC와 BC + PPO는 학습 시드가 하나뿐이라 이 표에 없다.

표준편차는 표본 표준편차(n − 1). 실패 = 충돌·신호 위반·경로 이탈·시간초과 중 하나라도 있는 Episode.

    python scripts/training/seed_stats.py            # 화면 출력
    python scripts/training/seed_stats.py --save     # docs/training/strict/seed_stats.txt에도 저장
"""
import json
import os
import statistics as st
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "training", "strict")
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스 ×1.3"), ("xmasbus3", "버스 3배")]
MODELS = [("bc", "BC"), ("bc_dagger", "BC + DAgger"), ("bc_ppo", "BC + PPO 3차")]
SEEDS = ["s1", "s2", "s3"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def counts(eps):
    col = sum(e["outcome"] == "collided" for e in eps)
    red = sum(e["red_light"] > 0 for e in eps)
    fail = sum(e["outcome"] != "arrived" or e["red_light"] > 0 for e in eps)
    return col, red, fail


def ms(xs, fmt="{:.1f}"):
    m = st.mean(xs)
    s = st.stdev(xs) if len(xs) > 1 else 0.0
    return f"{fmt.format(m)} ± {fmt.format(s)}"


def main():
    out = []
    p = out.append
    p("[시드 평균 ± 표준편차] docs/training/strict/seed_stats.txt  (scripts/training/seed_stats.py)")
    p("")
    p("=== 1. 평가 시드 (최종 평가 2026111721~32, 조건마다 시드 3개 × 100 Episode) ===")
    p("조건별: 100 Episode당 횟수, 시드 3개의 평균 ± 표준편차")
    p(f"{'조건':<14}{'모델':<14}{'충돌':>14}{'신호 위반':>14}{'실패':>14}")
    rep = {m: {s: [0, 0, 0, 0] for s in SEEDS} for m, _ in MODELS}   # 반복별 (충돌, 신호, 실패, Episode 수)
    for c, cname in CONDS:
        for m, mname in MODELS:
            cols, reds, fails = [], [], []
            for s in SEEDS:
                eps = load(os.path.join(ROOT, "final_eval", m, f"{c}_{s}.json"))
                col, red, fail = counts(eps)
                k = 100.0 / len(eps)
                cols.append(col * k); reds.append(red * k); fails.append(fail * k)
                r = rep[m][s]
                r[0] += col; r[1] += red; r[2] += fail; r[3] += len(eps)
            p(f"{cname:<14}{mname:<14}{ms(cols):>14}{ms(reds):>14}{ms(fails):>14}")
    p("")
    p("전체: 반복 3회(s1·s2·s3 각각 4 조건 × 100 = 400 Episode)의 비율(%), 평균 ± 표준편차")
    p(f"{'모델':<14}{'충돌 %':>16}{'신호 위반 %':>16}{'실패 %':>16}")
    for m, mname in MODELS:
        col = [100.0 * rep[m][s][0] / rep[m][s][3] for s in SEEDS]
        red = [100.0 * rep[m][s][1] / rep[m][s][3] for s in SEEDS]
        fail = [100.0 * rep[m][s][2] / rep[m][s][3] for s in SEEDS]
        p(f"{mname:<14}{ms(col, '{:.2f}'):>16}{ms(red, '{:.2f}'):>16}{ms(fail, '{:.2f}'):>16}")

    p("")
    p("=== 2. 학습 시드 (BC + DAgger, 학습 시드 0·1·2, 검증 시드 각 1,200 Episode) ===")
    runs = [("0 (최종 모델)", "bc_dagger"), ("1", "bc_dagger_seed1"), ("2", "bc_dagger_seed2")]
    per = []
    for name, d in runs:
        tot = [0, 0, 0, 0]
        for c, _ in CONDS:
            for s in SEEDS:
                eps = load(os.path.join(ROOT, "val", d, f"{c}_{s}.json"))
                col, red, fail = counts(eps)
                tot[0] += col; tot[1] += red; tot[2] += fail; tot[3] += len(eps)
        per.append(tot)
        p(f"학습 시드 {name:<14} 충돌 {tot[0]:>3} ({100 * tot[0] / tot[3]:.2f}%)  신호 위반 {tot[1]:>2}  실패 {tot[2]:>3} ({100 * tot[2] / tot[3]:.2f}%)")
    p("평균 ± 표준편차 (n = 3): "
      f"충돌 {ms([100 * t[0] / t[3] for t in per], '{:.2f}')}%  "
      f"신호 위반 {ms([100 * t[1] / t[3] for t in per], '{:.2f}')}%  "
      f"실패 {ms([100 * t[2] / t[3] for t in per], '{:.2f}')}%")
    p("BC와 BC + PPO는 학습 시드가 하나(0)뿐이라 학습 시드 평균 ± 표준편차가 없다.")

    text = "\n".join(out) + "\n"
    print(text, end="")
    if "--save" in sys.argv:
        with open(os.path.join(ROOT, "seed_stats.txt"), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
