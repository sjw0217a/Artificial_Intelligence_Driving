"""선생(규칙)을 넘을 여지 분석 (학습 과정 기록 11.7절).

    python scripts/training/analyze_headroom.py            # 1차: 변형 15개, 크리스마스·버스 3배
    python scripts/training/analyze_headroom.py confirm    # 확인: 빨랐던 3개, 새 시드, 조건 4개

데이터: docs/training/teacher_headroom/{round1,confirm}/ (teacher_headroom.sh, teacher_headroom_confirm.sh 결과)
모든 변형이 같은 시드라 Episode마다 교통이 같으므로, 기본 선생과 같은 Episode끼리 뺀 차이로 비교한다.

1차에서는 "Episode마다 가장 빠른 변형을 고른 상한"도 계산한다. 여러 값 중 최솟값은 운만으로도 작아지므로
같은 크기의 착시를 따로 잰다: 변형마다 평균 차이를 빼서(실력 차이를 지우고) 교통 운에 의한 흔들림만 남긴 뒤
같은 방식으로 최솟값을 고른다. 두 값이 비슷하면 상한은 근거가 되지 않는다.
"""
import json
import math
import os
import statistics as st
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(BASE, "docs", "training", "teacher_headroom")

ROUNDS = {
    "round1": dict(conds=["xmas", "xmasbus3"], seeds=(1, 2),
                   variants=["base", "th08", "th16", "gap1", "wait3", "wait8", "accept2", "accept5",
                             "spawn30", "slow", "aggr", "null_a", "null_b", "null_c", "null_d"]),
    "confirm": dict(conds=["normal", "xmas", "xmas13", "xmasbus3"], seeds=(1, 2, 3),
                    variants=["base", "th08", "aggr_w5", "aggr"]),
}


def t(r):
    return r["section_s"] if r["outcome"] == "arrived" and r["section_s"] is not None else None


def ci(x):
    return 1.96 * st.stdev(x) / math.sqrt(len(x)) if len(x) > 1 else float("nan")


def load(d, cond, v, seeds):
    rows = []
    for s in seeds:
        p = os.path.join(d, f"{cond}_{v}_s{s}.json")
        if not os.path.exists(p):
            return None
        rows += json.load(open(p))
    return rows


def summary(data, base_t):
    """변형마다 (평균, p90, 충돌, 경로이탈, 차이 평균, 차이 95% 구간, Episode 수)."""
    out = {}
    for v, r in data.items():
        tt = sorted(t(x) for x in r if t(x) is not None)
        col = sum(x["outcome"] == "collided" for x in r)
        off = sum(x["outcome"] in ("route_failed", "timeout") for x in r)
        d = [t(a) - b for a, b in zip(r, base_t) if t(a) is not None and b is not None]
        out[v] = dict(mean=st.mean(tt), p90=tt[int(0.9 * (len(tt) - 1))], col=col, off=off,
                      diff=st.mean(d), ci=ci(d), n=len(r))
    return out


def oracle(data, base_t, names, center):
    """Episode마다 names 중 가장 빠른 값을 골랐을 때 기본 대비 평균 단축.
    center=True면 변형마다 평균 차이를 빼서 운에 의한 흔들림만 남긴다."""
    shift = {}
    for v in names:
        d = [t(a) - b for a, b in zip(data[v], base_t) if t(a) is not None and b is not None]
        shift[v] = st.mean(d) if center and v != "base" else 0.0
    gains = []
    for i, b in enumerate(base_t):
        if b is None:
            continue
        vals = [t(data[v][i]) - shift[v] for v in names if t(data[v][i]) is not None]
        gains.append(b - min(vals))
    return st.mean(gains)


def main():
    rnd = sys.argv[1] if len(sys.argv) > 1 else "round1"
    cfg = ROUNDS[rnd]
    d = os.path.join(ROOT, rnd)
    for cond in cfg["conds"]:
        data = {v: load(d, cond, v, cfg["seeds"]) for v in cfg["variants"]}
        data = {v: r for v, r in data.items() if r}
        base_t = [t(r) for r in data["base"]]
        s = summary(data, base_t)
        print(f"\n=== {cond} ({s['base']['n']} Episode) ===")
        print(f"{'변형':10s} {'평균':>7s} {'p90':>6s} {'충돌':>4s} {'이탈':>4s}  기본과 차이(같은 Episode)")
        for v in data:
            x = s[v]
            diff = "" if v == "base" else f"{x['diff']:+.2f} ±{x['ci']:.2f}"
            print(f"{v:10s} {x['mean']:7.2f} {x['p90']:6.1f} {x['col']:4d} {x['off']:4d}  {diff}")
        if rnd == "round1":
            real = [v for v in data if not v.startswith("null")]
            raw = oracle(data, base_t, real, center=False)
            noise = oracle(data, base_t, real, center=True)
            print(f"Episode마다 가장 빠른 변형을 고른 상한: {raw:.2f}초 단축 / 운만으로 생기는 착시: {noise:.2f}초")
            print(f"  → 상한 − 착시 = {raw - noise:+.2f}초 (0 근처면 상한은 근거가 되지 않는다)")


if __name__ == "__main__":
    main()
