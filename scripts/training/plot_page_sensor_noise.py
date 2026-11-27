"""프로젝트 페이지용 센서 오차 그래프: 대표 오차 설정의 실패율만, 페이지와 같은 어두운 배경으로.

    python scripts/training/plot_page_sensor_noise.py    # → docs/training/strict/page_sensor_noise.png

데이터와 집계는 plot_strict_sensor_noise.py와 같다. 두 조건(크리스마스 ×1.3, 크리스마스 + 버스 3배)을
합친 600 Episode에서 실패(충돌·신호 위반·경로 이탈·시간초과 중 하나라도 있는 Episode) 비율.
"""
import os
import sys

import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plot_strict_sensor_noise as P  # noqa: E402

SHOW = [("none", "오차 없음"), ("dist05", "앞뒤 차 거리 오차 0.5 m"), ("dist1", "앞뒤 차 거리 오차 1 m"),
        ("side10", "측면 레이더 경고 10% 놓침"), ("delay1", "관측 0.5초 지연"),
        ("stop2", "정지선 거리 오차 2 m"), ("red10", "적·황신호를 10% 녹색으로 읽음")]
BG, INK, INK2, GRID, BLUE, DIM = "#1b1f24", "#e8eaed", "#9aa1ab", "#2a2f36", "#5aa2f0", "#6b727c"

if __name__ == "__main__":
    rates = []
    for v, _ in SHOW:
        xs = [P.stats(c, v) for c, _ in P.CONDS]
        rates.append(100 * sum(x["fail"] for x in xs) / sum(x["n"] for x in xs))

    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=BG)
    ax.set_facecolor(BG)
    ys = list(range(len(SHOW)))[::-1]
    for y, r, (v, _) in zip(ys, rates, SHOW):
        ax.barh(y, r, height=0.6, color=BLUE if v == "none" else DIM, zorder=2)
        ax.text(r + 1, y, f"{r:.0f}%", va="center", fontsize=11, color=INK)
    ax.set_yticks(ys, [n for _, n in SHOW], fontsize=11, color=INK)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:g}%")
    ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="x", colors=INK2, length=0, labelsize=10)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xlabel("실패율 (충돌·신호 위반·경로 이탈, 600 Episode)", fontsize=10.5, color=INK2)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(P.D), "page_sensor_noise.png")
    fig.savefig(out, dpi=200, facecolor=BG)
    print(out, [f"{r:.1f}" for r in rates])
