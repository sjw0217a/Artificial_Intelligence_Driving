"""PPO 정책(HybridActorCritic)을 시연 데이터로 먼저 학습시킨다 (BC로 시작해서 PPO로 다듬기).

처음부터 PPO를 돌리면 무작위 차선변경 → 충돌 → "기어가기"나 "차선 유지"로 굳기 쉽다.
그래서 규칙 기반 시연(collect_pomdp_data.py --policy rule)으로 같은 네트워크를 먼저 맞춰 둔다.

    actor:  가감속 평균 μ는 시연의 가감속을 MSE로, 차선 head는 시연의 차선 명령을 cross-entropy로
    critic: 시연 에피소드의 할인 누적보상(reward-to-go)을 MSE로

critic까지 맞춰 두는 이유: 가치가 0 근처에서 시작하면 PPO 첫 업데이트들의 advantage가
엉터리라 애써 맞춘 actor가 바로 망가진다.

수업 BC(train_bc.py, algorithms/bc.py)와 네트워크 구조가 달라 가중치를 옮길 수 없어서
PPO 네트워크를 직접 학습한다. 데이터 형식은 collect_pomdp_data.py가 만드는 NPZ 그대로.
"""
import numpy as np
import torch
import torch.nn.functional as F


def load_demos(paths, gamma: float):
    """NPZ 여러 개 → (obs, accel, lane_idx, returns). 에피소드는 파일마다 따로 센다."""
    obs, accel, lane_idx, returns = [], [], [], []
    for path in paths:
        d = np.load(path)
        ep, rew = d["episode"], d["reward"].astype(np.float64)
        ret = np.zeros_like(rew)
        g = 0.0
        for i in range(len(rew) - 1, -1, -1):        # 에피소드 끝에서 앞으로
            if i == len(rew) - 1 or ep[i + 1] != ep[i]:
                g = 0.0
            g = rew[i] + gamma * g
            ret[i] = g
        obs.append(d["observation"])
        accel.append(np.clip(d["action_raw"][:, 0], -1.0, 1.0))
        # 명령(+1 왼쪽 / 0 유지 / -1 오른쪽) → HybridActorCritic의 인덱스(0 / 1 / 2)
        lane_idx.append(1 - d["lane_change"].astype(np.int64))
        returns.append(ret)
    cat = lambda xs, dt: torch.as_tensor(np.concatenate(xs), dtype=dt)  # noqa: E731
    return (cat(obs, torch.float32), cat(accel, torch.float32),
            cat(lane_idx, torch.long), cat(returns, torch.float32))


def lane_class_weights(lane):
    """차선 명령(왼/유지/오른) 칸별 가중치: 빈도 역수의 제곱근, 유지=1, 최대 20."""
    counts = torch.bincount(lane, minlength=3).float().clamp_min(1.0)
    class_w = (counts.sum() / counts).sqrt()
    return (class_w / class_w[1]).clamp(max=20.0)


def pretrain_policy(agent, paths, gamma=0.99, epochs=30, batch_size=256, lr=3e-4,
                    log_std=-1.0, seed=0, log=print):
    """agent.policy(HybridActorCritic)를 시연에 맞춘다. 끝나면 가감속 탐험 폭을 log_std로 둔다."""
    torch.manual_seed(seed)
    policy, dev = agent.policy, agent.device
    obs, accel, lane, ret = load_demos(paths, gamma)
    n = len(obs)
    # 차선 변경은 전체 스텝의 1% 미만이라, 변경 칸에 가중치를 줘야 argmax가 변경을 낸다
    counts = torch.bincount(lane, minlength=3).float().clamp_min(1.0)
    class_w = lane_class_weights(lane).to(dev)   # 왼쪽 변경처럼 몇 개 없는 칸이 과하게 커지지 않게
    log(f"[pretrain] 시연 {n} step, 차선 명령 (왼쪽/유지/오른쪽) = {counts.long().tolist()}, "
        f"가중치 {[round(float(w), 1) for w in class_w]}")

    opt = torch.optim.Adam(policy.parameters(), lr=lr)
    obs, accel, lane, ret = obs.to(dev), accel.to(dev), lane.to(dev), ret.to(dev)
    for ep in range(epochs):
        perm = torch.randperm(n, device=dev)
        tot = {"accel": 0.0, "lane": 0.0, "value": 0.0}
        for idx in perm.split(batch_size):
            mu, _, logits, value = policy(obs[idx])
            l_acc = F.mse_loss(mu.squeeze(-1), accel[idx])
            l_lane = F.cross_entropy(logits, lane[idx], weight=class_w)
            l_val = F.mse_loss(value, ret[idx])
            loss = l_acc + l_lane + 0.5 * l_val
            opt.zero_grad()
            loss.backward()
            opt.step()
            for k, v in (("accel", l_acc), ("lane", l_lane), ("value", l_val)):
                tot[k] += v.item() * len(idx)
        if ep % 10 == 9 or ep == epochs - 1:
            with torch.no_grad():
                _, _, logits, _ = policy(obs)
                pred = logits.argmax(-1)
                change = lane != 1
                recall = (pred[change] == lane[change]).float().mean().item()
                false_lc = (pred[~change] != 1).float().mean().item()
            log(f"[pretrain] epoch {ep + 1:3d}  " + "  ".join(f"{k}={v / n:.4f}" for k, v in tot.items())
                + f"  변경 재현율={recall:.0%}  불필요 변경={false_lc:.2%}")

    with torch.no_grad():
        policy.log_std.fill_(float(log_std))
    return policy
