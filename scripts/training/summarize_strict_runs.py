"""strict 학습 실행 기록 정리: results/의 로그를 docs/training/strict/run_logs/로 옮기고, 학습 곡선 그림과 요약 숫자를 만든다.

    python scripts/training/summarize_strict_runs.py --copy   # results/ → docs/training/strict/run_logs/ (results/가 있는 컴퓨터에서 한 번)
    python scripts/training/summarize_strict_runs.py          # run_logs/만 읽어 그림(strict_train_curves.png)과 요약 출력

BC·DAgger: train.py --pretrain 로그의 epoch별 손실 (학습 데이터 기준, 따로 떼어 둔 검증 데이터는 없음).
PPO: training_log.csv (업데이트마다), eval_log.csv (10,240 step마다 내부 점검 10 Episode, 모델 선택에는 안 씀).
"""
import argparse
import csv
import json
import math
import os
import re
import shutil

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(BASE, "docs", "training", "strict", "run_logs")
BC_RUNS = ["strict_0", "strict_1", "strict_2", "strict_3"]
PPO_RUNS = ["strict_ppo", "strict_ppo2", "strict_ppo3"]
BC_NAMES = {"strict_0": "BC (시연)", "strict_1": "DAgger 1라운드", "strict_2": "DAgger 2라운드", "strict_3": "DAgger 3라운드"}
PPO_NAMES = {"strict_ppo": "PPO 1차", "strict_ppo2": "PPO 2차", "strict_ppo3": "PPO 3차"}


def copy():
    os.makedirs(OUT, exist_ok=True)
    res = os.path.join(BASE, "results")
    for r in BC_RUNS + PPO_RUNS:
        shutil.copy(os.path.join(res, r, "cli_args.json"), os.path.join(OUT, f"{r}_cli_args.json"))
    for r in PPO_RUNS:
        for f in ("training_log.csv", "eval_log.csv"):
            shutil.copy(os.path.join(res, r, f), os.path.join(OUT, f"{r}_{f}"))
    keep = [l for l in open(os.path.join(res, "strict_dagger.log"), encoding="utf-8")
            if l.startswith("[pretrain]")]
    open(os.path.join(OUT, "bc_dagger_pretrain.txt"), "w", encoding="utf-8").writelines(keep)
    print("복사:", OUT)


def bc_logs():
    """bc_dagger_pretrain.txt → {run: [(epoch, accel, lane, value), ...]} (학습 순서대로 strict_0..3)."""
    runs, cur = [], None
    for line in open(os.path.join(OUT, "bc_dagger_pretrain.txt"), encoding="utf-8"):
        if "시연" in line and "step" in line:
            cur = {"steps": int(re.search(r"시연 (\d+) step", line).group(1)), "ep": []}
            runs.append(cur)
        m = re.search(r"epoch\s+(\d+)\s+accel=([\d.]+)\s+lane=([\d.]+)\s+value=([\d.]+)\s+변경 재현율=(\d+)%\s+불필요 변경=([\d.]+)%", line)
        if m and cur is not None:
            cur["ep"].append(tuple(float(x) for x in m.groups()))
    return dict(zip(BC_RUNS, runs))


def read_csv(path):
    return [{k: float(v) if v not in ("", None) else None for k, v in r.items()} for r in csv.DictReader(open(path))]


def summary(bc, ppo, ev):
    print("BC·DAgger (학습 데이터 기준, 마지막 epoch):")
    for r, d in bc.items():
        e = d["ep"][-1]
        print(f"  {BC_NAMES[r]}: 데이터 {d['steps']:,} step, epoch {int(e[0])}, 가감속 MSE {e[1]:.4f}, 차선 CE {e[2]:.4f}, "
              f"가치 MSE {e[3]:.3f}, 차선 변경 재현율 {e[4]:.0f}%, 불필요 변경 {e[5]:.2f}%")
    print("PPO:")
    for r in PPO_RUNS:
        t, e = ppo[r], ev[r]
        first = [x for x in t if x["update"] <= 5]
        after = [x for x in t if 6 <= x["update"] <= 10]
        last = t[-20:]
        mean = lambda rows, k: sum(x[k] for x in rows if x[k] is not None) / max(1, sum(x[k] is not None for x in rows))  # noqa: E731
        print(f"  {PPO_NAMES[r]}: 업데이트 {len(t)}회, 학습 보상(마지막 20회 평균) {mean(last, 'ep_rew_mean'):.2f}, "
              f"approx_kl 1~5번 {mean(first, 'approx_kl'):.2e} / 6~10번 {mean(after, 'approx_kl'):.4f} / 마지막 20회 {mean(last, 'approx_kl'):.4f}, "
              f"bc_loss 마지막 20회 {mean(last, 'bc_loss'):.4f}, 차선 변경 확률 {mean(last, 'p_lane_change'):.4f}, "
              f"내부 점검 충돌(전체 평균) {mean(e, 'collision_rate'):.3f}, 완주 {mean(e, 'success_rate'):.3f}")


def plot(bc, ppo):
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    BC_C = {"strict_0": "#b4b2a9", "strict_1": "#9ec5f4", "strict_2": "#5598e7", "strict_3": "#2a78d6"}
    PPO_C = {"strict_ppo": "#1baf7a", "strict_ppo2": "#eda100", "strict_ppo3": "#eb6834"}

    def style(ax, title, ylabel, xlabel):
        ax.set_title(title, loc="left", fontsize=12.5, color=INK, fontweight="bold", pad=8)
        ax.set_ylabel(ylabel, fontsize=10, color=INK2)
        ax.set_xlabel(xlabel, fontsize=10, color=INK2)
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(INK2)
        ax.tick_params(colors=INK2, labelsize=9)
        ax.set_facecolor(SURF)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.4), facecolor=SURF)
    ax = axes[0, 0]
    for r, d in bc.items():
        ep = [e[0] for e in d["ep"]]
        ax.plot(ep, [e[2] for e in d["ep"]], color=BC_C[r], lw=2, marker="o", ms=5, label=BC_NAMES[r])
    style(ax, "BC·DAgger: 차선 손실 (cross-entropy)", "손실", "epoch")
    ax.set_xticks([10, 20, 30])
    ax.legend(frameon=False, fontsize=9.5)
    ax = axes[0, 1]
    for r, d in bc.items():
        ep = [e[0] for e in d["ep"]]
        ax.plot(ep, [e[1] for e in d["ep"]], color=BC_C[r], lw=2, marker="o", ms=5, label=BC_NAMES[r])
    style(ax, "BC·DAgger: 가감속 손실 (MSE)", "손실", "epoch")
    ax.set_xticks([10, 20, 30])
    ax = axes[1, 0]
    for r, t in ppo.items():
        xs = [x["steps"] / 1000 for x in t]
        ys = [x["ep_rew_mean"] for x in t]
        k = 10
        sm = [sum(ys[max(0, i - k + 1):i + 1]) / len(ys[max(0, i - k + 1):i + 1]) for i in range(len(ys))]
        ax.plot(xs, sm, color=PPO_C[r], lw=2, label=PPO_NAMES[r])
    style(ax, "PPO: 학습 중 Episode 보상 (최근 10회 이동평균)", "보상", "학습 step (천)")
    ax.legend(frameon=False, fontsize=9.5)
    ax = axes[1, 1]
    for r, t in ppo.items():
        xs = [x["update"] for x in t if x["update"] <= 30]
        ys = [math.log10(max(abs(x["approx_kl"]), 1e-9)) for x in t if x["update"] <= 30]
        ax.plot(xs, ys, color=PPO_C[r], lw=2, marker="o", ms=4, label=PPO_NAMES[r])
    ax.axvspan(0.5, 5.5, color=GRID, alpha=0.6, lw=0)
    ax.text(3, -4.5, "critic\nwarmup", ha="center", fontsize=9, color=INK2)
    ax.set_yticks(range(-9, 0), [f"1e{v}" for v in range(-9, 0)])
    style(ax, "PPO: 업데이트마다 정책 변화 (approx_kl, 처음 30회)", "approx_kl (로그 눈금)", "업데이트")
    fig.suptitle("strict 학습 실행 기록", x=0.012, ha="left", fontsize=14.5, fontweight="bold", color=INK, y=0.995)
    fig.text(0.012, 0.008, "BC·DAgger 손실은 학습 데이터 기준 (데이터가 라운드마다 늘어 값끼리 직접 비교하지 않음)  ·  "
             "PPO 보상은 시도마다 보상 설정(3차는 신호 위반 즉시 종료)이 달라 값끼리 비교하지 않음  ·  1차는 warmup 동안 정책까지 바뀜", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.025, 1, 0.96), h_pad=2.2, w_pad=3)
    out = os.path.join(BASE, "docs", "training", "strict", "strict_train_curves.png")
    fig.savefig(out, dpi=200, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--copy", action="store_true")
    a = p.parse_args()
    if a.copy:
        copy()
    bc = bc_logs()
    ppo = {r: read_csv(os.path.join(OUT, f"{r}_training_log.csv")) for r in PPO_RUNS}
    ev = {r: read_csv(os.path.join(OUT, f"{r}_eval_log.csv")) for r in PPO_RUNS}
    summary(bc, ppo, ev)
    try:
        plot(bc, ppo)
    except ImportError:
        print("matplotlib이 없어 그림은 건너뜀")
