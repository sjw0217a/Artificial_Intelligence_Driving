"""선생(규칙)을 넘을 여지 그래프: 선생 설정을 바꾸면 얼마나 빨라지고, 대신 무엇을 잃는가 (학습 과정 기록 11.7절).

    python scripts/training/plot_teacher_headroom.py    # → docs/training/teacher_headroom.png

데이터: docs/training/teacher_headroom/confirm/ (새 시드, 조건마다 시드 3개 x 100 Episode, 모든 설정이 같은 교통)
왼쪽은 기본 선생과 같은 Episode끼리 뺀 복잡 구간 시간 차이(평균과 95% 구간), 오른쪽은 조건 4개를 합친 경로이탈·충돌 횟수.
"""
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(BASE, "docs", "training", "teacher_headroom", "confirm")
VARIANTS = [("base", "기본 선생 (차간 1.2초)", "#b4b2a9"),
            ("th08", "차간 시간 0.8초", "#2a78d6"),
            ("aggr_w5", "차간 0.9초 + 틈 기준 완화", "#1baf7a"),
            ("aggr", "위 + 대기 속도 8 m/s", "#eb6834")]
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스\n교통량 ×1.3"),
         ("xmasbus3", "크리스마스\n버스 ×3")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(cond, v):
    return sum((json.load(open(os.path.join(D, f"{cond}_{v}_s{s}.json"))) for s in (1, 2, 3)), [])


def ok(r):
    return r["outcome"] == "arrived" and r["section_s"] is not None


def mean_ci(x):
    x = np.asarray(x, float)
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def clean(ax):
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="y", colors=INK2, length=0, labelsize=9.5)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_facecolor(SURF)


def panel_diff(ax):
    step = 0.22
    for i, (cond, _) in enumerate(CONDS):
        base = load(cond, "base")
        for j, (v, _, color) in enumerate(VARIANTS[1:]):
            d = [b["section_s"] - a["section_s"] for a, b in zip(base, load(cond, v)) if ok(a) and ok(b)]
            m, c = mean_ci(d)
            x = i + (j - 1) * step
            ax.plot([x, x], [m - c, m + c], color=color, lw=2.2, zorder=3, solid_capstyle="round")
            ax.plot(x, m, "o", ms=8, color=color, mec=SURF, mew=2, zorder=4)
            ax.text(x, m - c - 0.12, f"{m:+.1f}", ha="center", va="top", fontsize=9, color=INK)
    ax.axhline(0, color=INK2, lw=1.2, zorder=2)
    clean(ax)
    ax.set_xticks(range(len(CONDS)), [c[1] for c in CONDS], fontsize=10, color=INK)
    ax.set_xlim(-0.5, len(CONDS) - 0.5)
    ax.set_ylim(-3.4, 0.8)
    ax.set_ylabel("기본 선생과 차이 (초, 같은 Episode)", fontsize=10.5, color=INK2)
    ax.text(-0.45, 0.7, "0선 아래: 기본 선생보다 빠름", fontsize=9, color=INK2, va="top")
    ax.set_title("복잡 구간 통과시간 단축", loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)


def panel_safety(ax):
    for j, (v, _, color) in enumerate(VARIANTS):
        rows = sum((load(c, v) for c, _ in CONDS), [])
        off = sum(r["outcome"] in ("route_failed", "timeout") for r in rows)
        col = sum(r["outcome"] == "collided" for r in rows)
        ax.bar(j, off, width=0.62, color=color, edgecolor="none", zorder=2)
        ax.text(j, off + 0.6, f"{off}회", ha="center", va="bottom", fontsize=10.5, color=INK, fontweight="bold")
        ax.text(j, -1.2, f"충돌 {col}", ha="center", va="top", fontsize=9, color=INK2)
    clean(ax)
    ax.set_xticks(range(len(VARIANTS)), ["기본", "0.8초", "완화", "완화+\n대기 8"], fontsize=10, color=INK)
    ax.tick_params(axis="x", pad=22)
    ax.set_xlim(-0.6, len(VARIANTS) - 0.4)
    ax.set_ylim(0, 34)
    ax.set_ylabel("경로이탈 횟수 (조건 4개 합계 1,200 Episode)", fontsize=10.5, color=INK2)
    ax.set_title("대신 잃는 것: 경로이탈", loc="left", fontsize=13, color=INK, fontweight="bold", pad=10)


if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), facecolor=SURF, gridspec_kw={"width_ratios": [1.6, 1]})
    panel_diff(axes[0])
    panel_safety(axes[1])
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for _, _, c in VARIANTS]
    fig.legend(handles, [v[1] for v in VARIANTS], loc="upper left", ncol=4, frameon=False,
               fontsize=10, bbox_to_anchor=(0.006, 0.935))
    fig.suptitle("선생 설정을 바꿔 잰 '넘을 여지': 새 시드, 조건마다 300 Episode, 같은 교통", x=0.012, ha="left",
                 fontsize=14.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.012, 0.012, "점: 평균  ·  세로선: 평균의 95% 구간  ·  전체 도착시간은 약 190초  ·  "
             "줄어든 시간은 앞차에 더 붙고 틈을 덜 따져서 생긴 것",
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.87), w_pad=3)
    out = os.path.join(BASE, "docs", "training", "teacher_headroom.png")
    fig.savefig(out, dpi=200, facecolor=SURF)
    print(out)
