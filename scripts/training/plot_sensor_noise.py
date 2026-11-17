"""센서 오차 강건성 표와 그래프 (학습 과정 기록 11.8절).

    python scripts/training/plot_sensor_noise.py          # 표 출력 + docs/training/sensor_noise.png
    python scripts/training/plot_sensor_noise.py --table  # 표만 (matplotlib 없어도 됨)

데이터: docs/training/sensor_noise/ (scripts/training/sensor_noise.sh, 조건마다 시드 3개 x 100 Episode, 모든 설정이 같은 교통)
"""
import json
import math
import os
import statistics as st
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(BASE, "docs", "training", "sensor_noise")
SETTINGS = [("none", "오차 없음 (기준)"),
            ("dist05", "거리 오차 0.5 m"), ("dist1", "거리 오차 1 m"), ("dist2", "거리 오차 2 m"),
            ("dist1avg4", "거리 오차 1 m + 2초 평균"), ("dist2avg4", "거리 오차 2 m + 2초 평균"),
            ("side10", "사각지대 경고 10% 놓침"), ("side30", "사각지대 경고 30% 놓침"), ("sideoff", "사각지대 경고 없음"),
            ("delay1", "관측 0.5초 지연"), ("delay2", "관측 1초 지연")]
CONDS = [("xmas13", "크리스마스 ×1.3"), ("xmasbus3", "크리스마스 + 버스 3배")]


def load(cond, v):
    return sum((json.load(open(os.path.join(D, f"{cond}_{v}_s{s}.json"))) for s in (1, 2, 3)), [])


def t(r):
    return r["section_s"] if r["outcome"] == "arrived" and r["section_s"] is not None else None


def stats(cond, v):
    rows, base = load(cond, v), load(cond, "none")
    d = [t(a) - t(b) for a, b in zip(rows, base) if t(a) is not None and t(b) is not None]
    tt = [t(r) for r in rows if t(r) is not None]
    return dict(n=len(rows), col=sum(r["outcome"] == "collided" for r in rows),
                off=sum(r["outcome"] in ("route_failed", "timeout") for r in rows),
                mean=st.mean(tt), diff=st.mean(d), ci=1.96 * st.stdev(d) / math.sqrt(len(d)))


def table():
    out = {}
    for cond, cname in CONDS:
        print(f"\n=== {cname} ===")
        print(f"{'설정':24s} {'충돌':>4s} {'이탈':>4s} {'평균':>7s}  기준과 차이(같은 Episode)")
        for v, name in SETTINGS:
            x = stats(cond, v)
            out[(cond, v)] = x
            diff = "" if v == "none" else f"{x['diff']:+.2f} ±{x['ci']:.2f}"
            print(f"{name:24s} {x['col']:4d} {x['off']:4d} {x['mean']:7.2f}  {diff}")
    return out


def plot(out):
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    COLORS = {"xmas13": "#2a78d6", "xmasbus3": "#eb6834"}
    fig, ax = plt.subplots(figsize=(11.5, 7.2), facecolor=SURF)
    ys = list(range(len(SETTINGS)))[::-1]
    h = 0.38
    for j, (cond, _) in enumerate(CONDS):
        for y, (v, _) in zip(ys, SETTINGS):
            x = out[(cond, v)]
            rate = 100 * x["col"] / x["n"]
            yy = y + (0.5 - j) * h
            ax.barh(yy, rate, height=h - 0.05, color=COLORS[cond], edgecolor="none", zorder=2)
            ax.text(rate + 0.8, yy, f"{rate:.0f}%", va="center", fontsize=9.5, color=INK)
    ax.axvline(5, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(5.6, ys[0] + 0.62, "수업 기준 5%", fontsize=9, color=INK2, va="bottom")
    ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(axis="x", colors=INK2, length=0, labelsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.set_facecolor(SURF)
    ax.set_xlim(0, 100)
    ax.set_yticks(ys, [s[1] for s in SETTINGS], fontsize=10.5, color=INK)
    ax.set_xlabel("충돌률 (조건마다 300 Episode)", fontsize=10.5, color=INK2)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=COLORS[c], ec="none") for c, _ in CONDS]
    fig.legend(handles, [c[1] for c in CONDS], loc="upper left", ncol=2, frameon=False, fontsize=10.5,
               bbox_to_anchor=(0.006, 0.94))
    fig.suptitle("센서가 틀리면: 최종 모델 관측에 오차를 넣었을 때 충돌률", x=0.012, ha="left",
                 fontsize=14.5, fontweight="bold", color=INK, y=0.99)
    fig.text(0.012, 0.012, "새 시드, 모든 설정이 같은 교통  ·  시뮬레이터는 그대로이고 모델에 들어가는 관측만 바꿨다  ·  "
             "모델은 오차 없는 관측으로만 학습했다", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    path = os.path.join(BASE, "docs", "training", "sensor_noise.png")
    fig.savefig(path, dpi=200, facecolor=SURF)
    print(path)


if __name__ == "__main__":
    res = table()
    if "--table" not in sys.argv:
        plot(res)
