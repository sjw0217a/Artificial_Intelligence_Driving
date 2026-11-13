"""공식 시드 결과 그래프: 1단계 BC(dag3) vs 최종 모델(v3_3)의 복잡 구간 통과시간.

    python scripts/training/plot_official_compare.py    # → docs/training/official_compare.png

왼쪽은 도착한 모든 Episode, 오른쪽은 정류장에 선 버스를 만난 Episode만. 막대는 평균, 선은 평균의 95% 구간.
"""
import glob
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(BASE, "docs", "training", "official_eval")
MODELS = [("1단계 BC (추월 모름)", os.path.join(EVAL, "baseline_dag3"), "#b4b2a9"),
          ("최종 모델 v3_3", EVAL, "#2a78d6")]
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스\n교통량 ×1.3"),
         ("xmasbus3", "크리스마스\n버스 ×3")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def stats(folder, cond, bus_only):
    rows = sum((json.load(open(f)) for f in sorted(glob.glob(f"{folder}/{cond}_s?.json"))), [])
    x = np.array([r["section_s"] for r in rows if r["outcome"] == "arrived" and r["section_s"] is not None
                  and (r["bus_seen"] or not bus_only)])
    return x.mean(), 1.96 * x.std() / np.sqrt(len(x)), len(x)


def bar(ax, x, h, w, color):
    ax.bar(x, h, width=w, color=color, edgecolor="none", zorder=2)


def panel(ax, bus_only, title):
    w, gap = 0.34, 0.03
    for i, (cond, _) in enumerate(CONDS):
        ns = []
        for j, (name, folder, color) in enumerate(MODELS):
            m, ci, n = stats(folder, cond, bus_only)
            ns.append(n)
            x = i + (j - 0.5) * (w + gap)
            bar(ax, x, m, w, color)
            ax.plot([x, x], [m - ci, m + ci], color=INK, lw=1.2, zorder=3, solid_capstyle="round")
            ax.text(x, m + ci + 0.8, f"{m:.1f}", ha="center", va="bottom", fontsize=10.5, color=INK,
                    fontweight="bold" if j == 1 else "normal")
        if bus_only:
            ax.text(i, -5.4, "n=" + (str(ns[0]) if ns[0] == ns[1] else f"{ns[0]} / {ns[1]}"), ha="center", va="top", fontsize=8.5, color=INK2)
    ax.set_xticks(range(len(CONDS)), [c[1] for c in CONDS], fontsize=10, color=INK)
    ax.set_xlim(-0.6, len(CONDS) - 0.4)
    ax.set_ylim(0, 46)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="y", colors=INK2, length=0, labelsize=9.5)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_facecolor(SURF)


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True, facecolor=SURF)
    panel(axes[0], False, "도착한 모든 Episode")
    panel(axes[1], True, "정류장에 선 버스를 만난 Episode")
    axes[0].set_ylabel("복잡 구간(S1~S2) 통과시간 (초)", fontsize=10.5, color=INK2)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for _, _, c in MODELS]
    fig.legend(handles, [m[0] for m in MODELS], loc="upper right", ncol=2, frameon=False,
               fontsize=10.5, bbox_to_anchor=(0.985, 0.995))
    fig.suptitle("공식 시드(조건마다 300 Episode, 같은 교통)에서 복잡 구간 통과시간", x=0.012, ha="left",
                 fontsize=14.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.012, 0.012, "막대: 평균  ·  세로선: 평균의 95% 구간  ·  짧을수록 좋음", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94), w_pad=3)
    out = os.path.join(BASE, "docs", "training", "official_compare.png")
    fig.savefig(out, dpi=200, facecolor=SURF)
    print(out)
