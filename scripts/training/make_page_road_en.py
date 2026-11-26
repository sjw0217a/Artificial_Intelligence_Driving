"""영어 페이지(docs/en.html)용 도로 그림: 한국어 라벨 상자를 영어로 다시 그린다.

    python scripts/training/make_page_road_en.py
    # → docs/assets/en/satellite_annotated.jpg, docs/assets/en/sumo_road.gif

원본(docs/assets/satellite_annotated.jpg, sumo_road.gif)은 라벨이 이미지에 박혀 있고 만든 스크립트가 없어서,
라벨 상자를 색으로 찾아(flood fill) 같은 모양의 상자를 덮고 영어로 다시 쓴다. 지도 자체의 상호명은 그대로다.
필요한 것: Pillow, ffmpeg. 글꼴은 macOS의 Apple SD Gothic Neo.
"""
import os
import subprocess
import tempfile
from collections import deque

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(BASE, "docs", "assets")
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
WHITE, MUTED, RED = (242, 243, 245), (163, 167, 174), (236, 139, 127)


def font(size, bold=False):
    return ImageFont.truetype(FONT, round(size), index=6 if bold else 0)


def find_box(px, size, seed, tol=7):
    """seed가 있는 단색 상자 안쪽의 경계 (x0, y0, x1, y1)."""
    W, H = size
    bg = px[seed]
    seen, q = {seed}, deque([seed])
    x0 = x1 = seed[0]
    y0 = y1 = seed[1]
    while q:
        x, y = q.popleft()
        x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in seen or not (0 <= n[0] < W and 0 <= n[1] < H):
                continue
            if abs(n[0] - seed[0]) > 300 or abs(n[1] - seed[1]) > 120:
                continue
            if max(abs(a - b) for a, b in zip(px[n], bg)) <= tol:
                seen.add(n)
                q.append(n)
    return (x0, y0, x1, y1), bg


def plan(im, labels):
    """라벨마다 새 상자 위치와 글자를 정한다 (모든 GIF 프레임에 같은 값을 쓰려고 첫 프레임에서 한 번만)."""
    px = im.load()
    out = []
    for seed, grow, title, sub, tcolor in labels:
        (x0, y0, x1, y1), bg = find_box(px, im.size, seed)
        border = px[x0 - 1, (y0 + y1) // 2]
        h = y1 - y0
        ft, fs = font(h * 0.36, True), font(h * 0.26)
        pad = h * 0.235
        need = pad * 2 + max(ft.getlength(title), fs.getlength(sub) if sub else 0)
        w = max(x1 - x0, need)
        nx0, nx1 = (x0, x0 + w) if grow == "right" else (x1 - w, x1)
        out.append(((nx0, y0, nx1, y1), bg, border, ft, fs, pad, title, sub, tcolor))
    return out


def draw(im, planned):
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1), bg, border, ft, fs, pad, title, sub, tcolor in planned:
        h = y1 - y0
        d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), radius=h * 0.1, fill=bg, outline=border, width=2)
        if sub:
            d.text((x0 + pad, y0 + h * 0.33), title, font=ft, fill=tcolor, anchor="lm")
            d.text((x0 + pad, y0 + h * 0.72), sub, font=fs, fill=MUTED, anchor="lm")
        else:
            d.text((x0 + pad, y0 + h / 2), title, font=ft, fill=tcolor, anchor="lm")


def satellite():
    im = Image.open(os.path.join(A, "satellite_annotated.jpg")).convert("RGB")
    labels = [((530, 395), "left", "Bank of Korea", "Signalized intersection", WHITE),
              ((918, 582), "right", "4 → 5 lanes", "Bypass road merges", WHITE),
              ((955, 703), "right", "5 → 4 lanes", "Lane drop", WHITE),
              ((262, 762), "left", "Media facade", "Shinsegae main building", RED),
              ((410, 902), "left", "Bus stop", "02144", WHITE),
              ((1020, 872), "right", "4 → 7 lanes", "L3 · S3 · R1", WHITE),
              ((1058, 1068), "right", "Hoehyeon", "Signalized intersection", WHITE)]
    draw(im, plan(im, labels))
    d = ImageDraw.Draw(im)
    bg, border, teal = (25, 26, 30), (59, 60, 64), (143, 193, 202)
    # 왼쪽 아래 범례: 원래 글자 위에 같은 모양의 상자를 깔고 다시 쓴다
    d.rounded_rectangle((28, 1232, 400, 1346), radius=9, fill=bg, outline=border, width=2)
    d.text((48, 1268), "① → ③  ≈ 187 m", font=font(36, True), fill=teal, anchor="lm")
    d.line((48, 1320, 70, 1320), fill=(225, 226, 228), width=3)
    d.text((78, 1320), "3 entries", font=font(22), fill=MUTED, anchor="lm")
    d.line((200, 1320, 222, 1320), fill=teal, width=3)
    d.text((230, 1320), "3 exits", font=font(22), fill=MUTED, anchor="lm")
    # 오른쪽 아래 출처
    d.rounded_rectangle((1128, 1348, 1392, 1386), radius=7, fill=bg)
    d.text((1382, 1367), "Map: Naver Map satellite", font=font(20), fill=MUTED, anchor="rm")
    os.makedirs(os.path.join(A, "en"), exist_ok=True)
    out = os.path.join(A, "en", "satellite_annotated.jpg")
    im.save(out, quality=90)
    print(out)


def sumo_gif():
    src = Image.open(os.path.join(A, "sumo_road.gif"))
    duration = src.info.get("duration", 130)
    first = src.convert("RGB")
    labels = [((462, 69), "right", "Bank of Korea", "Signalized intersection", WHITE),
              ((34, 76), "right", "4 → 5 lanes", "Bypass merges", WHITE),
              ((494, 180), "right", "5 → 4 lanes", "Lane drop", WHITE),
              ((165, 360), "right", "Media facade", "Shinsegae main bldg.", RED),
              ((333, 420), "right", "Bus stop", "02144", WHITE),
              ((264, 475), "right", "4 → 7 lanes", "L3 · S3 · R1", WHITE),
              ((384, 572), "right", "Hoehyeon", "Signalized intersection", WHITE)]
    planned = plan(first, labels)
    tmp = tempfile.mkdtemp()
    for i in range(src.n_frames):
        src.seek(i)
        fr = src.convert("RGB")
        draw(fr, planned)
        fr.save(os.path.join(tmp, f"{i:04d}.png"))
    out = os.path.join(A, "en", "sumo_road.gif")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", f"1000/{duration}", "-i",
                    os.path.join(tmp, "%04d.png"), "-vf",
                    "split[x][y];[x]palettegen=max_colors=128[p];[y][p]paletteuse=dither=none", out], check=True)
    print(out, src.n_frames, "frames")


if __name__ == "__main__":
    satellite()
    sumo_gif()
