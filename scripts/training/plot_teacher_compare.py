"""선생(규칙) vs 최종 모델 그래프: 같은 검증용 시드에서 복잡 구간 통과시간.

    python scripts/training/plot_teacher_compare.py    # → docs/training/teacher_compare.png

데이터: docs/training/teacher_eval/ (조건마다 시드 3개 x 100 Episode, 모델마다 같은 시드라 Episode마다 교통이 같다)
왼쪽은 도착한 Episode의 평균(세로선: 평균의 95% 구간), 오른쪽은 같은 Episode끼리 뺀 차이(최종 모델 − 선생)의 평균과 95% 구간.
"""
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(BASE, "docs", "training", "teacher_eval")
MODELS = [("1단계 BC (추월 모름)", "baseline_dag3", "#b4b2a9"),
          ("선생 (규칙, SUMO 내부 정보 사용)", "teacher", "#d9822b"),
          ("최종 모델 (관측 37칸만 사용)", "final_v3", "#2a78d6")]
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스\n교통량 ×1.3"),
         ("xmasbus3", "크리스마스\n버스 ×3")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(folder, cond):
    return sum((json.load(open(os.path.join(EVAL, folder, f"{cond}_s{s}.json"))) for s in (1, 2, 3)), [])


def ok(r):
    return r["outcome"] == "arrived" and r["section_s"] is not None


def mean_ci(x):
    x = np.asarray(x, float)
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def style(ax):
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="y", colors=INK2, length=0, labelsize=9.5)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_facecolor(SURF)
    ax.set_xticks(range(len(CONDS)), [c[1] for c in CONDS], fontsize=10, color=INK)
    ax.set_xlim(-0.6, len(CONDS) - 0.4)


def panel_time(ax):
    w, gap = 0.26, 0.03
    for i, (cond, _) in enumerate(CONDS):
        for j, (_, folder, color) in enumerate(MODELS):
            m, ci = mean_ci([r["section_s"] for r in load(folder, cond) if ok(r)])
            x = i + (j - 1) * (w + gap)
            ax.bar(x, m, width=w, color=color, edgecolor="none", zorder=2)
            ax.plot([x, x], [m - ci, m + ci], color=INK, lw=1.2, zorder=3, solid_capstyle="round")
            ax.text(x, m + ci + 0.6, f"{m:.1f}", ha="center", va="bottom", fontsize=9.5, color=INK,
                    fontweight="bold" if j > 0 else "normal")
    style(ax)
    ax.set_ylim(0, 38)
    ax.set_ylabel("복잡 구간(S1~S2) 통과시간 (초)", fontsize=10.5, color=INK2)
    ax.set_title("복잡 구간 통과시간 (도착한 Episode)", loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)


def panel_diff(ax):
    for i, (cond, _) in enumerate(CONDS):
        t, s = load("teacher", cond), load("final_v3", cond)
        d = [b["section_s"] - a["section_s"] for a, b in zip(t, s) if ok(a) and ok(b)]
        m, ci = mean_ci(d)
        ax.plot([i, i], [m - ci, m + ci], color=MODELS[2][2], lw=2.2, zorder=3, solid_capstyle="round")
        ax.plot(i, m, "o", ms=8, color=MODELS[2][2], mec=SURF, mew=2, zorder=4)
        ax.text(i + 0.1, m, f"{m:+.1f}초\n(±{ci:.1f})", ha="left", va="center", fontsize=9.5, color=INK)
    ax.axhline(0, color=INK2, lw=1.2, zorder=2)
    style(ax)
    ax.set_ylim(-3, 3)
    ax.set_ylabel("최종 모델 − 선생 (초)", fontsize=10.5, color=INK2)
    ax.text(-0.55, 2.75, "위: 최종 모델이 느림", fontsize=9, color=INK2, va="top")
    ax.text(-0.55, -2.75, "아래: 최종 모델이 빠름", fontsize=9, color=INK2, va="bottom")
    ax.set_title("같은 Episode끼리 뺀 차이", loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), facecolor=SURF, gridspec_kw={"width_ratios": [1.5, 1]})
    panel_time(axes[0])
    panel_diff(axes[1])
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for _, _, c in MODELS]
    fig.legend(handles, [m[0] for m in MODELS], loc="upper right", ncol=3, frameon=False,
               fontsize=10, bbox_to_anchor=(0.985, 0.995))
    fig.suptitle("선생(규칙)과 최종 모델: 검증용 시드, 조건마다 300 Episode, 같은 교통", x=0.012, ha="left",
                 fontsize=14.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.012, 0.012, "막대·점: 평균  ·  세로선: 평균의 95% 구간  ·  짧을수록 좋음  ·  오른쪽에서 0선에 걸치면 차이가 오차 범위 안",
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.92), w_pad=3)
    out = os.path.join(BASE, "docs", "training", "teacher_compare.png")
    fig.savefig(out, dpi=200, facecolor=SURF)
    print(out)
