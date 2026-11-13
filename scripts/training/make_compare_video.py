"""record_episode.py로 녹화한 두 Episode를 나란히 붙여 발표 영상(mp4)을 만든다.

    python scripts/training/make_compare_video.py LEFT_FRAMES RIGHT_FRAMES OUT.mp4 [--start 296 --end 396 --speed 2 --zoom 307 332]

LEFT/RIGHT_FRAMES는 record_episode.py --frames 폴더 (0000.png ... + steps.json).
필요한 것: ffmpeg, Pillow. 한글 글꼴은 macOS의 Apple SD Gothic Neo를 쓴다.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
BG, INK, INK2, ACCENT, GOOD = (24, 24, 23), (240, 239, 236), (170, 168, 160), (255, 92, 92), (120, 200, 255)
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=6 if bold else 0)


def interpolate(src, start, end, speed, out):
    """스텝(0.5초) 프레임 → FPS 프레임으로 보간. 녹화가 일찍 끝났으면 마지막 프레임을 이어 붙인다."""
    tmp = tempfile.mkdtemp()
    last = None
    for i, t in enumerate(range(start, end)):
        p = os.path.join(src, f"{t:04d}.png")
        last = p if os.path.exists(p) else last
        shutil.copy(last, os.path.join(tmp, f"{i:04d}.png"))
    os.makedirs(out, exist_ok=True)
    src_fps = 2 * speed     # 1스텝 = 0.5초
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(src_fps), "-i",
                    os.path.join(tmp, "%04d.png"), "-vf",
                    f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                    os.path.join(out, "%05d.png")], check=True)
    shutil.rmtree(tmp)
    return sorted(os.listdir(out))


def card(lines, sub=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    y = H // 2 - 40 * len(lines)
    for text, size, color in lines:
        d.text((W // 2, y), text, font=font(size, size >= 50), fill=color, anchor="mm")
        y += int(size * 1.6)
    if sub:
        d.text((W // 2, H - 90), sub, font=font(26), fill=INK2, anchor="mm")
    return im


def panel_text(d, x0, pw, label, info, t_step, color):
    d.text((x0 + pw // 2, 150), label, font=font(36, True), fill=color, anchor="mm")
    t_in, t_out = info["t_in"], info["t_out"]
    if t_in is None or t_step < t_in:
        msg, c = "복잡 구간 진입 전", INK2
    elif t_out is None or t_step < t_out:
        msg, c = f"복잡 구간 {(t_step - t_in) * 0.5:4.1f}초", INK
    else:
        msg, c = f"통과 {(t_out - t_in) * 0.5:.1f}초", color
    d.text((x0 + pw // 2, 200), msg, font=font(34, True), fill=c, anchor="mm")
    step = next((s for s in info["steps"] if s["t"] == int(t_step)), None)
    if step and step["bus"] and (t_out is None or t_step < t_out):
        d.text((x0 + pw // 2, 1052), "앞쪽 정류장에 버스 정차 중", font=font(26), fill=INK2, anchor="mm")


def overtake_events(info):
    """steps.json에서 추월 장면의 주요 시점(스텝)을 찾는다. 못 찾은 사건은 뺀다."""
    st = info["steps"]
    ev = []

    def first(cond, after=0):
        return next((s["t"] for s in st if s["t"] >= after and cond(s)), None)

    t1 = first(lambda s: s["road"] == "S1")
    t2 = first(lambda s: s["road"] == "S1" and s["lane"] == 0, t1 or 0)
    t3 = first(lambda s: s["bus"], t1 or 0)
    t4 = first(lambda s: s["road"] == "S1m" and s["lane"] >= 2, t3 or 0) if t3 else None
    t5 = first(lambda s: s["road"] == "S1b" and s["lane"] >= 1, t3 or 0) if t3 else None
    t6 = first(lambda s: s["road"] == "S2" and s["lane"] == 0, t5 or 0) if t5 else None
    for t, text in ((t1, "신호 ① 통과, 복잡 구간(S1) 진입"),
                    (t2, "출구 쪽인 맨 오른쪽 차로로 이동"),
                    (t3, "80 m 앞 정류장에 선 버스 감지 (관측 [36] 켜짐)"),
                    (t4, "합류점 직후 왼쪽으로 한 칸 이동"),
                    (t5, "정류장 옆 차로로 버스 옆을 지나감"),
                    (t6, "넓어진 S2에서 맨 오른쪽으로 복귀 → 출구")):
        if t is not None:
            ev.append((t, text))
    return ev


def zoom_segment(src, info, crop, start, end, speed, put):
    ev = overtake_events(info)
    x0, y0, x1, y1 = crop
    zh = 880
    zw = int((x1 - x0) * zh / (y1 - y0))
    zx, zy = 110, 150
    tx = zx + zw + 90
    steps = {s["t"]: s for s in info["steps"]}
    hold = int(round(FPS / (2 * speed)))     # 보간하지 않고 스텝마다 선명한 화면을 이만큼 보여 준다
    last = None
    for t_step in range(start, end):
        p = os.path.join(src, f"{t_step:04d}.png")
        last = p if os.path.exists(p) else last
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        fr = Image.open(last).convert("RGB").crop(crop).resize((zw, zh), Image.LANCZOS)
        im.paste(fr, (zx, zy))
        d.text((40, 40), "확대: 최종 모델이 버스를 지나가는 순간", font=font(34, True), fill=INK)
        d.text((40, 88), f"{speed:g}배속  ·  빨간 원: 자율주행차  ·  흰색: 정류장에 선 버스", font=font(24), fill=INK2)
        cur = max((j for j, (t, _) in enumerate(ev) if t <= t_step), default=-1)
        y = 200
        for j, (t, text) in enumerate(ev):
            on = j == cur
            c = GOOD if on else (INK if j < cur else (90, 90, 88))
            d.text((tx, y), f"{j + 1}", font=font(34, True), fill=c)
            d.text((tx + 50, y), text, font=font(32 if on else 28, on), fill=c)
            d.text((tx + 50, y + 44), f"{(t - ev[0][0]) * 0.5:+.1f}초", font=font(22), fill=INK2)
            y += 112
        s = steps.get(t_step)
        if s:
            flag = "켜짐" if s["bus"] else "꺼짐"
            d.text((tx, y + 30), f"관측 [36] 버스 감지: {flag}", font=font(30, True),
                   fill=ACCENT if s["bus"] else INK2)
        put(im, hold)
    put(im, FPS * 2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("left")
    p.add_argument("right")
    p.add_argument("out")
    p.add_argument("--start", type=int, default=296)
    p.add_argument("--end", type=int, default=396)
    p.add_argument("--speed", type=float, default=2.0)
    p.add_argument("--left-label", default="1단계 BC (추월을 안 배움)")
    p.add_argument("--right-label", default="최종 모델 v3_3 (버스 추월을 배움)")
    p.add_argument("--intro", default="크리스마스 시나리오 · 같은 교통 · 같은 시드")
    p.add_argument("--zoom", nargs=2, type=int, default=None, metavar=("FROM", "TO"),
                   help="오른쪽 모델의 이 스텝 구간을 확대·느리게 다시 보여 준다")
    p.add_argument("--zoom-crop", default="40,0,470,590", help="확대할 영역 x0,y0,x1,y1 (녹화 프레임 픽셀)")
    p.add_argument("--zoom-speed", type=float, default=0.5)
    a = p.parse_args()

    work = tempfile.mkdtemp()
    infos = [json.load(open(os.path.join(f, "steps.json"))) for f in (a.left, a.right)]
    seqs = [interpolate(f, a.start, a.end, a.speed, os.path.join(work, n))
            for f, n in ((a.left, "L"), (a.right, "R"))]
    n = min(len(s) for s in seqs)
    frames = os.path.join(work, "out")
    os.makedirs(frames)
    k = 0

    def put(im, count):
        global k
        for _ in range(count):
            im.save(os.path.join(frames, f"{k:05d}.png"))
            k += 1

    put(card([("같은 교통에서 신세계 앞 정류장 지나가기", 60, INK),
              (a.intro, 34, INK2),
              (f"왼쪽: {a.left_label}", 34, INK2),
              (f"오른쪽: {a.right_label}", 34, GOOD)],
             "빨간 원: 자율주행차  ·  흰색: 정류장에 선 버스  ·  2배속"), FPS * 4)

    sample = Image.open(os.path.join(work, "L", seqs[0][0]))
    scale = 790 / sample.height
    pw, ph = int(sample.width * scale), 790
    gap = 120
    xs = [(W - 2 * pw - gap) // 2, (W + gap) // 2]
    for i in range(n):
        t_step = a.start + i / FPS * 2 * a.speed
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        for side in range(2):
            fr = Image.open(os.path.join(work, "LR"[side], seqs[side][i])).convert("RGB").resize((pw, ph))
            im.paste(fr, (xs[side], 235))
            panel_text(d, xs[side], pw, [a.left_label, a.right_label][side], infos[side], t_step,
                       [INK, GOOD][side])
        d.text((40, 40), "복잡 구간 S1 → S2 (신세계 앞 정류장 포함)", font=font(30, True), fill=INK)
        d.text((40, 82), f"{a.speed:g}배속  ·  빨간 원: 자율주행차  ·  흰색: 정류장 버스", font=font(24), fill=INK2)
        put(im, 1)
    put(im, FPS * 2)   # 마지막 화면 잠깐 정지
    if a.zoom:
        crop = tuple(int(v) for v in a.zoom_crop.split(","))
        zoom_segment(a.right, infos[1], crop, a.zoom[0], a.zoom[1], a.zoom_speed, put)

    L, R = [(i["t_out"] - i["t_in"]) * 0.5 for i in infos]
    put(card([(f"복잡 구간 통과시간  {L:.1f}초 → {R:.1f}초", 60, INK),
              ("정류장에 선 버스를 옆 차로로 지나감 (관측 [36] + 추월 시연으로 학습)", 32, INK2),
              ("공식 시드 300 Episode: 버스를 만나면 평균 37.7초 → 26.0초, 전체 평균 22.6초 → 21.3초", 30, INK2)]),
        FPS * 6)

    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i",
                    os.path.join(frames, "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "18", "-movflags", "+faststart", a.out], check=True)
    shutil.rmtree(work)
    print(a.out, f"{k / FPS:.1f}초")
