# Autonomous Driving on Sogong-ro in Myeongdong (SUMO)

**[Project page](https://sjw0217a.github.io/Artificial_Intelligence_Driving/)** · [Local HTML](docs/index.html)

## Installation

Install SUMO 1.27.1 and set `SUMO_HOME` to its installation directory. Run the following commands from the repository root.

```bash
export PATH="$SUMO_HOME/bin:$PATH"
python -m pip install -r requirements.txt
```

## Run the simulation

```bash
python view_road.py --nogui --seconds 600          # Build the road network and run a 10-minute check
python view_road.py --christmas --speed 4          # View Christmas traffic in the GUI at 4× speed
python test.py models/strict_bc_dagger.pt --christmas
```

Omit `--christmas` to run with normal traffic. Road and traffic settings are defined in [env/road_config.py](env/road_config.py).

| Checkpoint | Model |
|---|---|
| `models/strict_bc.pt` | BC only |
| `models/strict_bc_dagger.pt` | BC + DAgger (final model) |
| `models/strict_bc_ppo3.pt` | BC + PPO (third configuration) |

## Reproduce training

The training script fits a behavior cloning (BC) policy to 1,000 demonstration episodes from a rule-based driver, then runs three rounds of DAgger with 400 episodes per round. It saves the BC checkpoint to `results/strict_0/pretrained_model.pt` and the final DAgger checkpoint to `results/strict_3/pretrained_model.pt`.

```bash
WORKERS=8 bash scripts/training/train_strict_model.sh
```

To reproduce the third PPO configuration, fine-tune the BC checkpoint using the demonstration data from the previous step.

```bash
RUN=strict_ppo3 EXTRA=--warmup-value-head-only REWARD_EXTRA=red_light_terminate=1 \
  bash scripts/training/train_strict_ppo.sh
```

## Reproduce the evaluation

This example evaluates the final model for 100 episodes using the first seed from the official Christmas evaluation. To compare all three models under the same traffic conditions, rerun the command with each checkpoint and a separate JSON output file.

```bash
python eval_section_time.py models/strict_bc_dagger.pt --christmas \
  --episodes 100 --eval-seed 2026111724 --json eval_xmas.json
```

The official evaluation runs 100 episodes per seed, with three seeds per condition. See the [evaluation script](scripts/training/strict_eval.sh) for the full procedure and [final_eval](docs/training/strict/final_eval/) for the per-episode results.

| Traffic condition | Additional flags | Evaluation seeds |
|---|---|---|
| Normal | None | 2026111721–2026111723 |
| Christmas | `--christmas` | 2026111724–2026111726 |
| Christmas with 1.3× traffic | `--christmas --traffic 1.3` | 2026111727–2026111729 |
| Christmas with 3× bus frequency | `--christmas --bus-scale 3` | 2026111730–2026111732 |

## Collect driving data

```bash
python collect_pomdp_data.py --model models/strict_bc_dagger.pt \
  --episodes 1000 --workers 8 --seed 300 --name strict_normal
```

This command collects data under normal traffic conditions. To collect Christmas traffic data, add `--christmas` and use `--name strict_xmas` for the output.
