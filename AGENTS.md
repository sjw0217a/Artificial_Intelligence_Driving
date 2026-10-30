# AGENTS.md — 모든 코딩 에이전트 공통 규칙

명동 소공로(한국은행 앞 → 회현사거리, 남쪽 방향) SUMO 자율주행 팀 프로젝트.
설계는 `docs/myeongdong_sumo_design.md`, 진행 상황과 결정은 `HANDOFF.md`가 기준이다.
최종 평가는 수업 저장소의 `project_materials/6_Project_Evaluation.md` 기준
(충돌률 < 5%, 완주, 충분한 일반 차량과 interaction, Teleport 없는 안정성, 데이터 10^7개).

## 절대 규칙 (교수님 규칙 포함 — 어기면 리뷰에서 차단)

1. **Observation과 데이터 형식은 추가만 한다.**
   - `env/sumo_env.py`의 `_get_obs()`에서 기존 [0~30]의 계산식, 순서, 정규화를 바꾸거나 지우지 않는다. 새 값은 [31] 이후에 덧붙인다.
   - `observation_space`의 차원과 `_get_obs()`가 실제로 내는 길이가 같아야 한다. 같은 상황에서 [0~30] 값이 변경 전과 같아야 한다.
   - `collect_pomdp_data.py`의 기존 키(`observation`, `action_raw`, `action.*`, `reward`, `terminated`, `truncated`, `state`, `detected_vehicles`, `event.*`, `next_*`, NPZ 배열 이름)는 이름과 의미를 바꾸지 않는다. 새 정보는 새 키로만 추가한다.
2. **`env/sumo/`는 직접 고치지 않는다.** `road_builder.build()`가 실행할 때마다 다시 만든다. 도로·교통 변경은 `env/road_config.py`(값) 또는 `env/road_builder.py`(생성 로직)에서 한다.
3. **Reward는 두 곳을 같이 본다.** 기본값은 `env/mdp_config.py`의 `REWARD`, PPO 실험은 `train.py`의 `REWARD_OVERRIDES`가 덮어쓴다. `test.py`와 `collect_pomdp_data.py`는 `train.REWARD`를 쓴다. 새 보상 항은 `sumo_env.step()`에서 실제로 계산되는지 확인한다.
4. **평가 지표를 섞지 않는다.** 충돌, 도착(완주), 경로 이탈, 시간초과, Teleport는 따로 집계한다. 경로 이탈이 시간초과로 집계되면 안 된다.
5. **시나리오는 설정으로만 바꾼다.** 크리스마스 시나리오는 `TRAFFIC["christmas"]["enabled"]`이고 기본값은 `False`(평시)다.
6. **`road_config.py`의 `*` 표시 값은 거리뷰 확인 전 추정값이다.** 사실처럼 문서화하지 않는다.
7. 주석과 문서는 한국어로, 주변 코드의 주석 밀도와 스타일을 따른다.

## 검증 명령

```bash
python -m py_compile $(git ls-files '*.py')     # 문법
python view_road.py --nogui --seconds 600       # 도로 생성 + 10분 시뮬레이션. Waiting 0, 오류 없음이어야 함
```

환경(`sumo_env.py`)을 바꿨다면 keep-lane 정책으로 1 Episode를 돌려 ego 생성·종료 사유·관측 길이를 확인한다.

## 작업 방식 (tmux)

- **파일을 고치는 에이전트는 한 번에 하나.** 리뷰 에이전트(opencode `reviewer`)는 읽기 전용이다.
  opencode에서 `/review` (staged diff), `/review HEAD~1`, `/review main...HEAD` 처럼 쓴다. 설정: `.opencode/agents/`, `.opencode/commands/`.
- 작업 단위가 끝나면 `git add`로 끊고, 리뷰는 **staged diff**(또는 지정한 커밋 범위)에 대해서만 한다.
- 몇 분 이상 걸리는 학습·데이터 수집은 별도 윈도우에서 로그를 남기며 돌린다.
  ```bash
  python train.py 2>&1 | tee results/train_$(date +%m%d_%H%M).log
  ```
- 실행 중인 tmux 세션이나 학습 프로세스를 에이전트가 임의로 종료하지 않는다.

## 리뷰 체크리스트 (작성자도 커밋 전에 스스로 확인)

- [ ] 관측: 기존 [0~30] 그대로, 새 값은 뒤에, `observation_space` 차원 일치, 값 범위 [-1, 1]
- [ ] 데이터: 기존 키 그대로, 새 키만 추가
- [ ] `env/sumo/` 생성 파일을 손으로 고치지 않음
- [ ] Reward: `mdp_config.py`와 `train.py` 둘 다 반영, `step()`에서 실제 계산
- [ ] 검증 명령을 돌렸고 결과(Teleport, Waiting, 오류)를 확인함
- [ ] 평가 지표(충돌·완주·경로 이탈·시간초과·Teleport)가 따로 집계됨
- [ ] 바뀐 동작이 `HANDOFF.md`나 설계 문서와 어긋나면 문서도 갱신함
