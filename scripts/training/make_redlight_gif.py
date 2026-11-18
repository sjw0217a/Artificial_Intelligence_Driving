"""신호 위반 비교 GIF: record_episode.py로 녹화한 두 Episode의 신호 ① 부분을 잘라 나란히 붙인다.

    python scripts/training/record_episode.py results/strict_0/pretrained_model.pt --christmas --scene 25 --frames out/s25_bc
    python scripts/training/record_episode.py results/strict_3/pretrained_model.pt --christmas --scene 25 --frames out/s25_dagger
    python scripts/training/make_redlight_gif.py out/s25_bc out/s25_dagger docs/training/strict/video/redlight_strict.gif

정지선의 색(빨강·초록 선)이 그 차로의 신호다. 필요한 것: Pillow, ffmpeg.
"""
import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
BG, INK, INK2, BAD, GOOD = (24, 24, 23), (240, 239, 236), (170, 168, 160), (255, 92, 92), (120, 200, 255)


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=6 if bold else 0)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("left")
    p.add_argument("right")
    p.add_argument("out")
    p.add_argument("--start", type=int, default=112)
    p.add_argument("--end", type=int, default=142)
    p.add_argument("--crop", default="470,120,810,400", help="x0,y0,x1,y1 (녹화 프레임 픽셀)")
    p.add_argument("--scale", type=float, default=1.3)
    p.add_argument("--left-label", default="BC (strict)")
    p.add_argument("--right-label", default="BC + DAgger (strict 최종)")
    p.add_argument("--left-note", default="적신호에 정지선을 넘어 교차로로 들어감")
    p.add_argument("--right-note", default="정지선 앞에서 신호를 기다림")
    p.add_argument("--fps", type=float, default=4.0, help="1스텝 = 0.5초이므로 4는 2배속")
    a = p.parse_args()

    x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
    cw, ch = int((x1 - x0) * a.scale), int((y1 - y0) * a.scale)
    gap, top, side = 40, 150, 30
    W, H = side * 2 + cw * 2 + gap, top + ch + 60
    tmp = tempfile.mkdtemp()
    last = [None, None]
    for i, t in enumerate(range(a.start, a.end)):
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.text((side, 22), "신호 ① 앞, 같은 교통 · 크리스마스 장면 25", font=font(30, True), fill=INK)
        d.text((side, 64), f"{a.fps / 2:g}배속  ·  빨간 원: 자율주행차  ·  정지선의 빨간 선 = 적신호",
               font=font(20), fill=INK2)
        for k, (src, label, note, color) in enumerate(((a.left, a.left_label, a.left_note, BAD),
                                                       (a.right, a.right_label, a.right_note, GOOD))):
            f = os.path.join(src, f"{t:04d}.png")
            last[k] = f if os.path.exists(f) else last[k]
            fr = Image.open(last[k]).convert("RGB").crop((x0, y0, x1, y1)).resize((cw, ch), Image.LANCZOS)
            x = side + k * (cw + gap)
            im.paste(fr, (x, top))
            d.text((x + cw // 2, 112), label, font=font(26, True), fill=color, anchor="mm")
            d.text((x + cw // 2, top + ch + 30), note, font=font(22), fill=INK2, anchor="mm")
        im.save(os.path.join(tmp, f"{i:04d}.png"))
    for j in range(int(a.fps * 2)):   # 마지막 화면 2초 정지
        im.save(os.path.join(tmp, f"{a.end - a.start + j:04d}.png"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(a.fps), "-i",
                    os.path.join(tmp, "%04d.png"), "-vf",
                    "split[x][y];[x]palettegen=max_colors=64[p];[y][p]paletteuse=dither=none", a.out], check=True)
    print(a.out)
