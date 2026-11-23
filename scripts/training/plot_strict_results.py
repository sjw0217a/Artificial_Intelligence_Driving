"""strict 세 모델 결과 그래프 (docs/training/strict/평가_계획.md).

    python scripts/training/plot_strict_results.py    # → docs/training/strict/strict_results.png

왼쪽: 최종 평가(시드 2026111721~32, 1,200 Episode)의 실패 유형별 Episode 수.
오른쪽: 검증 시드(441101~441112)와 최종 평가의 실패 합계. 검증에서 고른 순서가 최종 평가에서도 같은지 본다.
BC + PPO는 검증에서 후보가 된 3차 시도(strict_ppo3)다.
"""
import json
import os

import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(BASE, "docs", "training", "strict")
CONDS = ("normal", "xmas", "xmas13", "xmasbus3")
# (이름, 검증 폴더, 최종 평가 폴더, 색)
MODELS = [("BC", "bc", "bc", "#b4b2a9"),
          ("BC + DAgger (최종)", "bc_dagger", "bc_dagger", "#2a78d6"),
          ("BC + PPO (3차)", "bc_ppo3", "bc_ppo", "#eb6834")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(kind, name):
    return sum((json.load(open(os.path.join(ROOT, kind, name, f"{c}_s{s}.json")))
                for c in CONDS for s in (1, 2, 3)), [])


def counts(rows):
    return {"충돌": sum(r["outcome"] == "collided" for r in rows),
            "신호 위반": sum(r.get("red_light", 0) > 0 for r in rows),
            "경로 이탈·\n시간초과": sum(r["outcome"] in ("route_failed", "timeout") for r in rows),
            "fail": sum(r["outcome"] != "arrived" or r.get("red_light", 0) > 0 for r in rows)}


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="y", colors=INK2, length=0, labelsize=9.5)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_facecolor(SURF)


def grouped(ax, groups, values, ymax):
    w, gap = 0.26, 0.03
    for i, _ in enumerate(groups):
        for j, (_, _, _, color) in enumerate(MODELS):
            v = values[j][i]
            x = i + (j - 1) * (w + gap)
            ax.bar(x, v, width=w, color=color, edgecolor="none", zorder=2)
            ax.text(x, v + ymax * 0.012, str(v), ha="center", va="bottom", fontsize=10.5, color=INK,
                    fontweight="bold" if j == 1 else "normal")
    ax.set_xticks(range(len(groups)), groups, fontsize=10.5, color=INK)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, ymax)


if __name__ == "__main__":
    final = [counts(load("final_eval", f)) for _, _, f, _ in MODELS]
    val = [counts(load("val", v)) for _, v, _, _ in MODELS]
    kinds = ["충돌", "신호 위반", "경로 이탈·\n시간초과"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), facecolor=SURF, gridspec_kw={"width_ratios": [3, 2]})
    grouped(axes[0], kinds, [[c[k] for k in kinds] for c in final], 140)
    style(axes[0], "최종 평가: 실패 유형별 Episode 수")
    axes[0].set_ylabel("Episode 수 (1,200 중)", fontsize=10.5, color=INK2)
    grouped(axes[1], ["검증 시드", "최종 평가 시드"], [[v["fail"], f["fail"]] for v, f in zip(val, final)], 175)
    style(axes[1], "실패 합계: 검증 → 최종 평가")

    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for *_, c in MODELS]
    fig.legend(handles, [m[0] for m in MODELS], loc="upper right", ncol=3, frameon=False,
               fontsize=10.5, bbox_to_anchor=(0.985, 0.995))
    fig.suptitle("보조 규칙 없는 환경(strict)의 세 모델, 조건 4개 × 300 Episode", x=0.012, ha="left",
                 fontsize=14.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.012, 0.012, "실패 = 충돌·신호 위반·경로 이탈·시간초과 중 하나라도 있는 Episode  ·  "
             "수업 기준 충돌 5% = 60회  ·  낮을수록 좋음", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94), w_pad=3)
    out = os.path.join(ROOT, "strict_results.png")
    fig.savefig(out, dpi=200, facecolor=SURF)
    print(out)
