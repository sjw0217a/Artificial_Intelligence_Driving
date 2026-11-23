"""SUMO 도로망을 발표 자료와 같은 어두운 톤으로 그린다 (위성사진과 나란히 놓는 용도).

발표 자료의 위성사진(① 한국은행 앞 ~ ③ 회현사거리)과 같은 범위·축척으로 그려서
두 그림의 같은 위치에 같은 지점이 오게 한다. 차로 모양은 SUMO가 만든 net.xml 그대로다.

사용:
    # 1) SUMO 환경에서 도로망 생성
    python -c "from env import road_config as rc, road_builder as rb; rb.build(rc.ROAD, rc.EGO, rc.TRAFFIC, 'out/roadnet')"
    # 2) matplotlib이 있는 환경에서 그림
    python scripts/training/plot_road_network.py out/roadnet/highway.net.xml road_network_dark.png
"""
import math
import os
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, Circle
from matplotlib.offsetbox import AnnotationBbox, TextArea, VPacker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from env.road_config import ROAD, SCENERY  # noqa: E402

BG = "#131417"
ROAD_C = "#2c2e33"
LINE_C = "#61656c"
JUNC_C = "#26282c"
ACCENT = "#8fc1ca"
RED = "#ec8b7f"
TEXT = "#f2f3f5"
MUTED = "#a3a7ae"

# 발표 자료 위성사진(정사각형, ① 한국은행 앞 ~ ③ 회현사거리)과 같은 범위 (m, SUMO 좌표). ①이 (0, 0).
# 위성사진에서 ①→③ 475 px = 185.6 m (2.56 px/m)로 맞춘 값
XLIM = (-190.0, 166.0)
YLIM = (-248.0, 106.0)
COMPLEX = {"S1", "S1m", "S1b", "S2"}   # ①~③ 복잡 구간


def pick_font():
    for name in ("Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR"):
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            return name
    return "sans-serif"


def parse_shape(s):
    return [tuple(map(float, p.split(","))) for p in s.split()]


def offset_polygon(pts, half):
    """폴리라인을 좌우로 half만큼 벌린 다각형."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == n - 1:
            dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    return left + right[::-1]


def point_at(pts, dist):
    """폴리라인 시작에서 dist(m) 지점과 그 방향."""
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if acc + seg >= dist:
            t = (dist - acc) / seg
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), (x1 - x0) / seg, (y1 - y0) / seg
        acc += seg
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    seg = math.hypot(x1 - x0, y1 - y0)
    return pts[-1], (x1 - x0) / seg, (y1 - y0) / seg


def label(ax, x, y, title, sub=None, color=TEXT, dot=None):
    """위성사진 그림과 같은 모양의 라벨 상자 (제목 굵게 + 설명 회색). (x, y) = 상자 왼쪽 가운데.
    dot = 가리키는 지점이 있으면 점과 선을 그린다."""
    items = [TextArea(title, textprops=dict(color=color, fontsize=29, fontweight="bold"))]
    if sub:
        items.append(TextArea(sub, textprops=dict(color=MUTED, fontsize=23)))
    box = AnnotationBbox(VPacker(children=items, align="left", pad=0, sep=6), (x, y),
                         box_alignment=(0, 0.5), frameon=True, pad=0.55, zorder=10,
                         bboxprops=dict(boxstyle="round,pad=0.4,rounding_size=0.35",
                                        fc="#1c1d21", ec="#4b5058", lw=1.4))
    ax.add_artist(box)
    if dot is not None:
        ax.plot([dot[0], x], [dot[1], y], color=MUTED, lw=1.6, zorder=9)
        ax.add_patch(Circle(dot, 1.6, fc=TEXT, ec="none", zorder=9))


def main(net_path, out_path):
    plt.rcParams["font.family"] = pick_font()
    root = ET.parse(net_path).getroot()

    w_px = 1850
    aspect = (YLIM[1] - YLIM[0]) / (XLIM[1] - XLIM[0])
    fig = plt.figure(figsize=(w_px / 100, w_px * aspect / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_aspect("equal")
    ax.axis("off")

    # 교차로 면
    for j in root.iter("junction"):
        if j.get("type") == "internal" or not j.get("shape"):
            continue
        ax.add_patch(Polygon(parse_shape(j.get("shape")), closed=True, fc=JUNC_C, ec="none", zorder=1))

    # 차로: 바탕(구분선 색) 위에 조금 좁게 도로 색을 칠해 차선 구분선을 남긴다
    lanes = {}
    for e in root.iter("edge"):
        internal = e.get("function") == "internal"
        for ln in e.iter("lane"):
            pts = parse_shape(ln.get("shape"))
            w = float(ln.get("width", 3.2))
            lanes[ln.get("id")] = pts
            if internal:
                ax.add_patch(Polygon(offset_polygon(pts, w / 2), closed=True, fc=JUNC_C, ec="none", zorder=1))
                continue
            hi = e.get("id") in COMPLEX
            ax.add_patch(Polygon(offset_polygon(pts, w / 2 + 0.1), closed=True, fc=LINE_C, ec="none", zorder=2))
            ax.add_patch(Polygon(offset_polygon(pts, w / 2 - 0.2), closed=True,
                                 fc="#323a3d" if hi else ROAD_C, ec="none", zorder=3))

    # 미디어파사드
    ax.add_patch(Polygon(SCENERY["media_facade"]["shape"], closed=True, fc=RED, ec="none", zorder=5))

    # 버스정류장 (차로 위 구간)
    bs = ROAD["bus_stop"]
    pts = lanes[bs["lane"]]
    seg = [point_at(pts, d)[0] for d in (bs["start"], (bs["start"] + bs["end"]) / 2, bs["end"])]
    ax.add_patch(Polygon(offset_polygon(seg, 1.3), closed=True, fc=TEXT, ec="none", zorder=5))

    # 신호 ① ③
    for name, num in (("J1", "1"), ("J3", "3")):
        x, y, _ = ROAD["nodes"][name]
        ax.add_patch(Circle((x, y), 7.0, fc=ACCENT, ec=BG, lw=2, zorder=8))
        ax.text(x, y - 0.4, num, color=BG, fontsize=26, fontweight="bold", ha="center", va="center", zorder=9)

    # 라벨: 위성사진 그림과 같은 문구·같은 자리 (위성사진 픽셀을 이 축척으로 옮긴 위치)
    label(ax, -62, 5, "한국은행 앞", "신호교차로")
    label(ax, 40, -48, "4 → 5차로", "우회 도로 합류", dot=(19, -46))
    label(ax, 50, -80, "5 → 4차로", "차로 감소", dot=(31, -70))
    label(ax, 67, -123, "4 → 7차로", "좌3 · 직3 · 우1", dot=(50, -112))
    label(ax, 99, -178, "회현사거리", "신호교차로")
    label(ax, -128, -95, "미디어파사드", None, color=RED)
    label(ax, -89, -130, "버스정류장", "버스 20초 정차", dot=(seg[1][0] - 2.5, seg[1][1]))

    # 축척 막대와 출처
    x0, y0 = XLIM[0] + 12, YLIM[0] + 12
    ax.plot([x0, x0 + 50], [y0, y0], color=MUTED, lw=3, zorder=9)
    ax.text(x0 + 25, y0 + 4, "50 m", color=MUTED, fontsize=23, ha="center", va="bottom", zorder=9)
    ax.text(XLIM[1] - 8, YLIM[0] + 10, "SUMO 도로망 · 차로 모양은 net.xml 그대로", color=MUTED,
            fontsize=23, ha="right", va="bottom", zorder=9)

    fig.savefig(out_path, dpi=100, facecolor=BG)
    print(out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
