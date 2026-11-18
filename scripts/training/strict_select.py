"""strict 후보 비교와 최종 모델 선정 (docs/training/strict/평가_계획.md 3-1절의 규칙을 그대로 코드로 옮긴 것).

    python scripts/training/strict_select.py                 # 검증 결과(docs/training/strict/val/)로 표 + 선정
    python scripts/training/strict_select.py --final         # 최종 평가 결과(docs/training/strict/final_eval/)로 표만 (선정 안 함)

규칙: 충돌률 5% 미만이고 신호 위반 Episode 1% 이하인 후보만 남김 → 실패(충돌·신호 위반·경로 이탈·시간초과) Episode
합계가 가장 적은 것 → 실패 차이가 6회 이하이면 복잡 구간 평균 시간이 짧은 것.
"""
import json
import math
import os
import statistics as st
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스 x1.3"), ("xmasbus3", "버스 3배")]
ORDER = ["bc", "bc_dagger", "bc_ppo"]
NAMES = {"bc": "BC", "bc_dagger": "BC + DAgger", "bc_ppo": "BC + PPO"}


def load(d, cond):
    return sum((json.load(open(os.path.join(d, f"{cond}_s{s}.json"))) for s in (1, 2, 3)), [])


def failed(r):
    return r["outcome"] != "arrived" or r.get("red_light", 0) > 0


def sec(r):
    return None if failed(r) or r["section_s"] is None else r["section_s"]


def summary(rows):
    n = len(rows)
    out = {k: sum(r["outcome"] == k for r in rows) for k in ("collided", "route_failed", "timeout")}
    out["red_ep"] = sum(r.get("red_light", 0) > 0 for r in rows)
    out["fail"] = sum(failed(r) for r in rows)
    tt = [sec(r) for r in rows if sec(r) is not None]
    out.update(n=n, mean=st.mean(tt) if tt else float("nan"),
               ci=1.96 * st.stdev(tt) / math.sqrt(len(tt)) if len(tt) > 1 else float("nan"))
    return out


def main():
    final = "--final" in sys.argv
    root = os.path.join(BASE, "docs", "training", "strict", "final_eval" if final else "val")
    models = [m for m in ORDER if os.path.isdir(os.path.join(root, m))]
    models += sorted(m for m in os.listdir(root) if os.path.isdir(os.path.join(root, m)) and m not in models)
    data = {m: {c: load(os.path.join(root, m), c) for c, _ in CONDS} for m in models}
    print(f"[{'최종 평가' if final else '검증'}] {os.path.relpath(root, BASE)}")
    for c, cname in CONDS:
        print(f"\n=== {cname} (조건마다 300 Episode) ===")
        print(f"{'모델':14s} {'충돌':>4s} {'신호위반':>6s} {'이탈':>4s} {'시간초과':>6s} {'실패':>4s}  복잡 구간 (성공 Episode)")
        for m in models:
            x = summary(data[m][c])
            print(f"{NAMES.get(m, m):14s} {x['collided']:4d} {x['red_ep']:6d} {x['route_failed']:4d} {x['timeout']:6d} "
                  f"{x['fail']:4d}  {x['mean']:.2f} ±{x['ci']:.2f}초")
    print("\n=== 네 조건 합계 (1,200 Episode) ===")
    tot = {}
    for m in models:
        x = summary(sum(data[m].values(), []))
        tot[m] = x
        print(f"{NAMES.get(m, m):14s} 충돌 {x['collided']:3d} ({100 * x['collided'] / x['n']:.1f}%)  신호 위반 Episode {x['red_ep']:3d} "
              f"({100 * x['red_ep'] / x['n']:.1f}%)  경로 이탈 {x['route_failed']:3d}  시간초과 {x['timeout']:3d}  "
              f"실패 {x['fail']:3d}  복잡 구간 {x['mean']:.2f}초")
    # 같은 Episode끼리 짝지은 시간 차이 (둘 다 성공한 Episode)
    print("\n=== 같은 Episode 짝 비교: 복잡 구간 시간 차이 (뒤 모델 - 앞 모델, 둘 다 성공한 Episode) ===")
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            A, B = sum(data[a].values(), []), sum(data[b].values(), [])
            d = [sec(y) - sec(x) for x, y in zip(A, B) if sec(x) is not None and sec(y) is not None]
            if len(d) > 1:
                print(f"{NAMES.get(b, b)} - {NAMES.get(a, a)}: {st.mean(d):+.2f} ±{1.96 * st.stdev(d) / math.sqrt(len(d)):.2f}초 "
                      f"({len(d)}쌍)")
    if final:
        return
    print("\n=== 선정 (평가 계획 3-1절) ===")
    ok = [m for m in models if tot[m]["collided"] / tot[m]["n"] < 0.05 and tot[m]["red_ep"] / tot[m]["n"] <= 0.01]
    for m in models:
        print(f"  {NAMES.get(m, m)}: 충돌 5% 미만 {'O' if tot[m]['collided'] / tot[m]['n'] < 0.05 else 'X'}, "
              f"신호 위반 1% 이하 {'O' if tot[m]['red_ep'] / tot[m]['n'] <= 0.01 else 'X'}")
    if not ok:
        print("  기준을 넘은 후보가 없다 → 선정하지 않는다")
        return
    best_fail = min(tot[m]["fail"] for m in ok)
    near = [m for m in ok if tot[m]["fail"] - best_fail <= 6]
    pick = min(near, key=lambda m: tot[m]["mean"])
    print(f"  기준 통과: {[NAMES.get(m, m) for m in ok]}")
    print(f"  실패 최소 {best_fail}회, 6회 이내: {[NAMES.get(m, m) for m in near]}")
    print(f"  → 선정: {NAMES.get(pick, pick)}")


if __name__ == "__main__":
    main()
