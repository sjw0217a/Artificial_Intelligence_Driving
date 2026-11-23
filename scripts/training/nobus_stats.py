"""관측 [37] 효과 비교 + 네 모델 비교 집계 (docs/training/strict/nobus_비교_계획.md). 새 실행 없이 저장된 Episode별 JSON만 읽는다.

    python scripts/training/nobus_stats.py            # 화면 출력
    python scripts/training/nobus_stats.py --save     # docs/training/strict/nobus_stats.txt, nobus_stats.json에도 저장

실패 = 충돌 · 신호 위반 · 경로 이탈 · 시간초과 중 하나라도 있는 Episode. 표준편차는 표본 표준편차(n − 1).
추월 = 정류장에 버스가 선 동안 S1b에서 1번 이상 차로에 있었던 Episode (버스를 만난 Episode 중).
같은 Episode 비교: 두 모델이 같은 시드의 같은 순번 Episode (출발 교통이 같다).
"""
import json, math, os, statistics as st, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "training", "strict", "nobus_eval")
CONDS = [("normal", "평시"), ("xmas", "크리스마스"), ("xmas13", "크리스마스 ×1.3"), ("xmasbus3", "크리스마스 + 버스 3배")]
MODELS = [("bc", "BC"), ("bc_dagger", "BC + DAgger (최종)"), ("bc_dagger_beta", "BC + DAgger β 쿨다운"),
          ("bc_ppo", "BC + PPO 3차"), ("nobus", "BC + DAgger, [37] 없음")]
SEEDS = ["s1", "s2", "s3"]


def load(m, c, s):
    with open(os.path.join(ROOT, m, f"{c}_{s}.json"), encoding="utf-8") as f:
        return json.load(f)


def fail(e):
    return e["outcome"] != "arrived" or e["red_light"] > 0


def ms(xs, d=2):
    return f"{st.mean(xs):.{d}f} ± {st.stdev(xs):.{d}f}"


def main():
    out, res = [], {}
    p = out.append
    p("[관측 [37] 효과 · 네 모델 비교] 시드 443001~443012, 조건마다 300 Episode, 다섯 모델 같은 시드")
    p("")
    p(f"{'모델':<24}{'충돌':>12}{'신호 위반':>12}{'경로 이탈':>8}{'시간초과':>8}{'실패':>6}{'실패 % (평균±표준편차)':>20}{'복잡 구간':>10}")
    for m, name in MODELS:
        eps = {c: {s: load(m, c, s) for s in SEEDS} for c, _ in CONDS}
        allep = [e for c, _ in CONDS for s in SEEDS for e in eps[c][s]]
        n = len(allep)
        col = sum(e["outcome"] == "collided" for e in allep); red = sum(e["red_light"] > 0 for e in allep)
        rf = sum(e["outcome"] == "route_failed" for e in allep); to = sum(e["outcome"] == "timeout" for e in allep)
        fl = sum(fail(e) for e in allep)
        rep = [100.0 * sum(fail(e) for c, _ in CONDS for e in eps[c][s]) / sum(len(eps[c][s]) for c, _ in CONDS) for s in SEEDS]
        sec = [e["section_s"] for e in allep if e["section_s"] is not None]
        res[m] = {"n": n, "collided": col, "red": red, "route_failed": rf, "timeout": to, "fail": fl,
                  "fail_pct_rep": rep, "section_mean": st.mean(sec), "cond": {}}
        p(f"{name:<24}{f'{col} ({100*col/n:.1f}%)':>12}{f'{red} ({100*red/n:.1f}%)':>12}{rf:>8}{to:>8}{fl:>6}{ms(rep):>20}{st.mean(sec):>9.2f}초")
        for c, cname in CONDS:
            ce = [e for s in SEEDS for e in eps[c][s]]
            seen = [e for e in ce if e["bus_seen"]]
            byp = [e for e in seen if e["bypass"]]
            res[m]["cond"][c] = {"fail": sum(fail(e) for e in ce), "collided": sum(e["outcome"] == "collided" for e in ce),
                                 "red": sum(e["red_light"] > 0 for e in ce), "route_failed": sum(e["outcome"] == "route_failed" for e in ce),
                                 "timeout": sum(e["outcome"] == "timeout" for e in ce),
                                 "bus_seen": len(seen), "bypass": len(byp),
                                 "sec_bus": st.mean([e["section_s"] for e in seen if e["section_s"] is not None]) if seen else None}
    p("")
    p("조건별 실패 (충돌 / 신호 위반 / 경로 이탈 / 시간초과)")
    for c, cname in CONDS:
        p(f"  {cname}: " + " | ".join(f"{name} {res[m]['cond'][c]['fail']} ({res[m]['cond'][c]['collided']}/{res[m]['cond'][c]['red']}/{res[m]['cond'][c]['route_failed']}/{res[m]['cond'][c]['timeout']})" for m, name in MODELS))
    p("")
    p("버스를 만난 Episode 중 추월 (추월 수 / 만난 수, 만났을 때 복잡 구간 평균)")
    for c, cname in CONDS:
        p(f"  {cname}: " + " | ".join(
            f"{name} {res[m]['cond'][c]['bypass']}/{res[m]['cond'][c]['bus_seen']}"
            + (f" ({100*res[m]['cond'][c]['bypass']/res[m]['cond'][c]['bus_seen']:.0f}%, {res[m]['cond'][c]['sec_bus']:.1f}초)" if res[m]['cond'][c]['bus_seen'] else "")
            for m, name in MODELS))
    p("")
    p("같은 Episode에서 둘 다 버스를 만났을 때 ([37] 없음 vs 최종)")
    pair = {}
    for c, cname in CONDS:
        d, both, a_only, b_only, nb = [], 0, 0, 0, 0
        for s in SEEDS:
            A, B = load("bc_dagger", c, s), load("nobus", c, s)
            for a, b in zip(A, B):
                if a["bus_seen"] and b["bus_seen"]:
                    nb += 1
                    if a["section_s"] is not None and b["section_s"] is not None:
                        d.append(b["section_s"] - a["section_s"])
                    both += a["bypass"] and b["bypass"]; a_only += a["bypass"] and not b["bypass"]; b_only += b["bypass"] and not a["bypass"]
        if nb:
            se = st.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else float("nan")
            pair[c] = {"n": nb, "final_only": a_only, "nobus_only": b_only, "both": both,
                       "sec_diff_mean": st.mean(d) if d else None, "sec_diff_se": se}
            p(f"  {cname}: {nb}쌍 · 최종만 추월 {a_only}, [37] 없음만 추월 {b_only}, 둘 다 {both} · "
              f"복잡 구간 차이([37] 없음 − 최종) {st.mean(d):+.2f} ± {se:.2f}초 (평균 ± 표준오차)")
    res["_pairs"] = pair
    text = "\n".join(out) + "\n"
    print(text, end="")
    if "--save" in sys.argv:
        base = os.path.join(ROOT, "..")
        open(os.path.join(base, "nobus_stats.txt"), "w", encoding="utf-8").write(text)
        json.dump(res, open(os.path.join(base, "nobus_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
