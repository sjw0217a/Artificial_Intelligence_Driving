"""명동 소공로 도로 구간 설명 그림: 전체 경로 + 복잡 구간 확대 (차로·버스정류장·구경 구간·추월 경로)."""
import sys
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.patches import Polygon, FancyArrowPatch

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

NET, OUT = sys.argv[1], sys.argv[2]
root = ET.parse(NET).getroot()
lanes, edges_lanes = {}, {}
for e in root.iter("edge"):
    eid = e.get("id")
    for ln in e.iter("lane"):
        pts = [tuple(map(float, p.split(","))) for p in ln.get("shape").split()]
        lanes[ln.get("id")] = (eid, pts, float(ln.get("width", 3.2)))
        edges_lanes.setdefault(eid, []).append(ln.get("id"))
junc = {j.get("id"): (float(j.get("x")), float(j.get("y"))) for j in root.iter("junction") if not j.get("id").startswith(":")}

ROUTE = ["NE_in", "S1", "S1m", "S1b", "S2", "W_out"]
COMPLEX = {"S1": "#4C78A8", "S1m": "#F58518", "S1b": "#E45756", "S2": "#54A24B"}
OTHER = "#B8B8B8"
halo = [pe.withStroke(linewidth=3, foreground="white")]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9.5), gridspec_kw={"width_ratios": [1, 1.25]})


def draw_lanes(ax, lw_scale, internal=True):
    for lid, (eid, pts, w) in lanes.items():
        xs, ys = zip(*pts)
        if eid.startswith(":"):
            if internal:
                ax.plot(xs, ys, color="#DDDDDD", lw=0.6, zorder=1)
            continue
        if eid in COMPLEX:
            c, z = COMPLEX[eid], 3
        elif eid in ROUTE:
            c, z = "#7F7F7F", 2
        else:
            c, z = OTHER, 1
        ax.plot(xs, ys, color=c, lw=w * lw_scale, solid_capstyle="butt", zorder=z, alpha=0.9)


# ── (가) 전체 경로 ──
draw_lanes(ax1, 0.9, internal=False)
ax1.set_title("(가) ego 전체 경로 659 m", fontsize=15, pad=10)
labels1 = {
    "NE_in": ("NE_in  253 m\n을지로 → ① 진입\n(① 적신호 대기 약 125초)", (95, 150)),
    "W_out": ("W_out  256 m\n퇴계로 서울역 방향 출구", (-160, -245)),
    "N_in": ("N_in (시청 쪽 진입)", (-150, 150)),
    "W_in": ("W_in (우회 도로)", (-150, -55)),
    "S_out": ("S_out (남산3호터널)", (120, -290)),
    "E_out": ("E_out (명동)", (250, -110)),
}
for k, (txt, xy) in labels1.items():
    bold = k in ROUTE
    ax1.text(*xy, txt, fontsize=11 if bold else 9, color="black" if bold else "#777777",
             weight="bold" if bold else "normal", path_effects=halo, zorder=6)
for j, name in (("J1", "① 한국은행 앞\n(신호)"), ("J3", "③ 회현사거리\n(신호)")):
    x, y = junc[j]
    ax1.plot(x, y, "o", ms=16, mfc="#FFD43B", mec="black", zorder=7)
    ax1.text(x + 14, y - 14 if j == "J1" else y + 4, name, fontsize=11, weight="bold", path_effects=halo, zorder=7)
# 복잡 구간 상자
ax1.add_patch(Polygon([(-25, 15), (95, 15), (95, -185), (-25, -185)], closed=True, fill=False,
                      ls="--", lw=1.5, ec="black", zorder=5))
ax1.text(100, -60, "점선 상자 =\n복잡 구간\n→ (나)에서 확대", fontsize=11, weight="bold", path_effects=halo)
# 진행 방향 화살표
for a, b in (((80, 230), (55, 150)), ((20, -230), (-50, -280))):
    ax1.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=22, color="black", lw=2, zorder=8))
ax1.set_aspect("equal"); ax1.axis("off")
ax1.set_xlim(-175, 320); ax1.set_ylim(-340, 270)

# ── (나) 복잡 구간 확대 ──
draw_lanes(ax2, 3.2)
ax2.set_title("(나) 복잡 구간 S1 → S1m → S1b → S2 (약 150 m)", fontsize=15, pad=10)

# 구경 구간 (크리스마스): S1m, S1b 전체
facade = [(-26.2, -86.9), (18.5, -82.1), (28.1, -104.1), (25.4, -105.3), (15.8, -83.3), (-26.2, -89.9)]
ax2.add_patch(Polygon(facade, closed=True, color="#E040C0", alpha=0.85, zorder=4))
ax2.text(-24, -97, "신세계 미디어파사드\n(크리스마스: 구경꾼 30%가\nS1m·S1b를 3 m/s로 통과)", fontsize=10,
         color="#A0108A", weight="bold", path_effects=halo, zorder=6)

# 버스정류장: S1b_0의 7~27 m
eid, pts, w = lanes["S1b_0"]
(x0, y0), (x1, y1) = pts[0], pts[-1]
L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
p = lambda s: (x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L)  # noqa: E731
(bx0, by0), (bx1, by1) = p(7), p(min(27, L))
ax2.plot([bx0, bx1], [by0, by1], color="#2F9E44", lw=w * 3.2 * 0.8, solid_capstyle="butt", zorder=6)
ax2.text(bx1 + 6, by1 - 4, "버스정류장 (신세계)\n버스 20초 정차", fontsize=10, color="#1B7A30", weight="bold",
         path_effects=halo, zorder=7)

seg = {
    "S1": "S1  31 m · 4차로\n① 통과 직후",
    "S1m": "S1m  33 m · 5차로\n우회 도로(W_in) 합류",
    "S1b": "S1b  28 m · 4차로\n오른쪽 두 차로가 한 차로로 합쳐짐",
    "S2": "S2  59 m · 7차로 확폭\n맨 오른쪽 차로만 서울역(W_out)",
}
offs = {"S1": (22, 6), "S1m": (24, 2), "S1b": (24, -2), "S2": (24, -8)}
for e, txt in seg.items():
    _, pts, _ = lanes[f"{e}_0"]
    mx = sum(x for x, _ in pts) / len(pts); my = sum(y for _, y in pts) / len(pts)
    ax2.text(mx + offs[e][0], my + offs[e][1], txt, fontsize=11, color=COMPLEX[e], weight="bold",
             path_effects=halo, zorder=7)

for j, name in (("J1", "①"), ("J3", "③")):
    x, y = junc[j]
    ax2.plot(x, y, "o", ms=16, mfc="#FFD43B", mec="black", zorder=7)
    ax2.text(x - 14, y + 2, name, fontsize=13, weight="bold", path_effects=halo, zorder=7)
for j, name in (("MP", "MP 합류점"), ("MG", "MG 5→4 합류")):
    x, y = junc[j]
    ax2.text(x - 34, y, name, fontsize=9, color="#555555", path_effects=halo, zorder=7)


def along(lid, frac):
    _, pts, _ = lanes[lid]
    i = min(int(frac * (len(pts) - 1)), len(pts) - 2)
    (ax_, ay), (bx, by) = pts[i], pts[i + 1]
    return ax_ + (bx - ax_) * 0.5, ay + (by - ay) * 0.5


# 평소 경로(검은 실선)와 버스 추월 경로(파란 점선)
normal = [lanes["S1_2"][1][0], along("S1_1", 0.5), lanes["S1_0"][1][-1], along("S1m_1", 0.5),
          lanes["S1b_0"][1][0], (bx0, by0), lanes["S1b_0"][1][-1], along("S2_0", 0.5), lanes["S2_0"][1][-1]]
over = [lanes["S1_2"][1][0], along("S1_1", 0.6), lanes["S1_1"][1][-1], along("S1m_2", 0.5),
        lanes["S1b_1"][1][0], along("S1b_1", 0.5), lanes["S1b_1"][1][-1], along("S2_1", 0.3), along("S2_0", 0.8),
        lanes["S2_0"][1][-1]]
xs, ys = zip(*normal)
ax2.plot(xs, ys, color="black", lw=2.2, zorder=8, label="지금 모델(BC): 맨 오른쪽 차로 → 버스가 서 있으면 뒤에서 대기")
xs, ys = zip(*over)
ax2.plot(xs, ys, color="#1C7ED6", lw=2.5, ls=(0, (4, 2)), zorder=8,
         label="버스 추월: 한 칸 왼쪽으로 지나간 뒤 S2에서 맨 오른쪽으로 복귀")
ax2.legend(loc="lower left", fontsize=10.5, frameon=True)
ax2.set_aspect("equal"); ax2.axis("off")
ax2.set_xlim(-45, 140); ax2.set_ylim(-178, 20)

fig.text(0.5, 0.015, "SUMO 도로망(김준민 제작, env/road_config.py)에서 차로 모양을 그대로 그림. "
         "색 = 복잡 구간 각 엣지, 회색 = 그 밖의 경로, 연회색 = 경로 밖 도로. 선 굵기 ∝ 차로 폭.",
         ha="center", fontsize=9.5, color="#555555")
plt.tight_layout(rect=(0, 0.03, 1, 0.95))
plt.savefig(OUT, dpi=150)
print("saved", OUT)
