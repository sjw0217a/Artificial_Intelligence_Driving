"""충돌 장면 GIF: diagnose_collision.py --frames로 저장한 sumo-gui 화면에 학생·선생 행동을 적어 GIF로 만든다.

    python scripts/training/make_collision_gif.py 프레임폴더 docs/training/collisions/official_bus3_s3_ep67.json \
        docs/training/collisions/official_bus3_s3_ep67.gif "공식 평가 · 버스 3배: 학생의 모방 실수"

빨간 원: 최종 모델(ego), 노란 원: 충돌 상대. 1프레임 = 0.5초, 실제 속도로 재생하고 마지막 장면에서 멈춘다.
필요한 것: ffmpeg, Pillow, macOS 한글 글꼴(Apple SD Gothic Neo).
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
CROP_W = 640


def lane_word(x):
    return "왼쪽으로" if x > 0.5 else "오른쪽으로" if x < -0.5 else "유지"


def main(frames, log_path, out, title):
    log = json.load(open(log_path))
    by_t = {round(s["t_s"] * 2): s for s in log["steps"]}
    names = sorted(f for f in os.listdir(frames) if f.endswith(".png"))
    f_big = ImageFont.truetype(FONT, 22, index=6)
    f_small = ImageFont.truetype(FONT, 18, index=0)
    tmp = tempfile.mkdtemp()
    k = 0
    for i, name in enumerate(names):
        t = int(name[:4])
        im = Image.open(os.path.join(frames, name)).convert("RGB")
        x0 = (im.width - CROP_W) // 2
        im = im.crop((x0, 0, x0 + CROP_W, im.height))
        canvas = Image.new("RGB", (CROP_W, im.height + 124), (252, 252, 251))
        canvas.paste(im, (0, 124))
        d = ImageDraw.Draw(canvas)
        d.text((14, 10), title, font=f_big, fill=(11, 11, 11))
        s = by_t.get(t)
        if s:
            l1 = f"{s['t_s']:.1f}초 · 속도 {s['v']:.1f} m/s · 학생: 차로 {lane_word(s['lane_cmd'])}, 가속 {s['accel_cmd']:+.2f}"
            l2 = f"같은 순간 선생이라면: 차로 {lane_word(s['teacher_lane'])}, 가속 {s['teacher_accel']:+.2f}"
        else:
            l1, l2 = "충돌", ""
        d.text((14, 44), l1, font=f_small, fill=(11, 11, 11))
        d.text((14, 68), l2, font=f_small, fill=(82, 81, 78))
        d.text((14, 94), "빨간 원: 최종 모델   노란 원: 충돌 상대   (가속 -1 = 최대 감속)", font=f_small, fill=(82, 81, 78))
        reps = 6 if i == len(names) - 1 else 1          # 마지막 장면은 3초 멈춤
        for _ in range(reps):
            canvas.save(os.path.join(tmp, f"{k:04d}.png"))
            k += 1
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "2", "-i", os.path.join(tmp, "%04d.png"),
                    "-vf", "split[a][b];[a]palettegen[p];[b][p]paletteuse", out], check=True)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:5])
