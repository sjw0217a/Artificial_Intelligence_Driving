# 명동 소공로 자율주행 (SUMO + PPO/BC)

한국은행 앞 교차로 → 소공로(신세계백화점 본점 앞) → 회현사거리, **남쪽 방향**.
두 신호 사이 약 187 m 안에서 세 방향 진입 차량이 세 방향 진출 차로(좌3·직3·우1)로 갈라지는
"신호 사이 엇갈림(눈치싸움)"을 SUMO로 만들고, 그 위에서 AV를 학습시키는 팀 프로젝트.

- 설계: [docs/myeongdong_sumo_design.md](docs/myeongdong_sumo_design.md)
- 진행 상황 · 결정 사항 · 남은 일: [HANDOFF.md](HANDOFF.md)
- 기반 코드와 수업 자료: [bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving](https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving)
  (SUMO 설치는 그 저장소의 `project_materials/1_SUMO_*_Setup.md` 참고)

## 실행

```bash
pip install -r requirements.txt
python view_road.py --nogui --seconds 600   # 도로망 생성 + 10분 시뮬레이션 검증
python view_road.py                         # sumo-gui로 보기 (▶ 눌러서 재생)
```

크리스마스 시나리오(미디어파사드 구경 감속 + 교통량 1.3배)는
`env/road_config.py`의 `TRAFFIC["christmas"]["enabled"] = True`.

## 구조

| 경로 | 역할 |
|---|---|
| `env/road_config.py` | 도로망(노드·엣지·차로 연결·신호·정류장), 교통량, 운전 성향 |
| `env/road_builder.py` | 설정 → SUMO 파일 생성 (`env/sumo/`, 실행할 때마다 다시 만들어짐) |
| `env/mdp_config.py`, `env/sumo_env.py` | 관측·행동·보상, Gymnasium 환경 |
| `algorithms/`, `utils/` | PPO, BC, 신경망, 버퍼, 평가, 로깅 |
| `train.py`, `train_bc.py`, `test.py`, `collect_pomdp_data.py` | 학습 · 평가 · 데이터 수집 |

> 규칙: observation과 데이터 형식은 **추가만** 한다. 기존 31차원과 기존 데이터 키는 바꾸거나 지우지 않는다.
