"""프로젝트 페이지용 결과 그래프: 최종 평가의 실패 유형별 Episode 비율(%)만, 페이지와 같은 어두운 배경으로.

    python scripts/training/plot_page_results.py    # → docs/training/strict/page_results.png

데이터와 집계는 plot_strict_results.py와 같다 (최종 평가 1,200 Episode).
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_strict_results import ROOT, load, counts  # noqa: E402

# (이름, 최종 평가 폴더, 색) — 색은 docs/index.html의 --dim, --blue, 주황
MODELS = [("BC", "bc", "#6b727c"), ("BC + DAgger (최종)", "bc_dagger", "#5aa2f0"), ("BC + PPO", "bc_ppo", "#e8955a")]
BG, INK, INK2, GRID = "#1b1f24", "#e8eaed", "#9aa1ab", "#2a2f36"

if __name__ == "__main__":
    kinds = ["충돌", "신호 위반", "경로 이탈·\n시간초과"]
    rows = [load("final_eval", f) for _, f, _ in MODELS]
    N = len(rows[0])   # 1,200
    final = [counts(r) for r in rows]

    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=BG)
    ax.set_facecolor(BG)
    w, gap = 0.26, 0.03
    for j, ((name, _, color), c) in enumerate(zip(MODELS, final)):
        for i, k in enumerate(kinds):
            x = i + (j - 1) * (w + gap)
            v = 100 * c[k] / N
            ax.bar(x, v, width=w, color=color, edgecolor="none", zorder=2, label=name if i == 0 else None)
            ax.text(x, v + 0.15, f"{v:.1f}%", ha="center", va="bottom", fontsize=11, color=INK,
                    fontweight="bold" if j == 1 else "normal")
    ax.set_xticks(range(len(kinds)), kinds, fontsize=11.5, color=INK)
    ax.set_ylim(0, 12)
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:g}%")
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="y", colors=INK2, length=0, labelsize=10)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.set_ylabel("Episode 비율 (1,200 Episode)", fontsize=10.5, color=INK2)
    ax.legend(loc="upper right", frameon=False, fontsize=11, labelcolor=INK)
    fig.tight_layout()
    out = os.path.join(ROOT, "page_results.png")
    fig.savefig(out, dpi=200, facecolor=BG)
    print(out)
