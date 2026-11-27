"""수집 시점의 SUMO 신호를 데이터셋의 숫자 리스트로 인코딩한다."""

# 소공로 네트워크의 교차로별 controlled-link 수. 리스트 순서는 linkIndex 순서다.
TLS_VECTOR_LENGTHS = {"J1": 5, "J3": 7}

# 소문자 g도 녹색, u(적황색)는 아직 정지 신호로 기록한다.
TLS_SIGNAL_VALUES = {"G": 1, "g": 1, "y": 0, "Y": 0,
                     "r": -1, "R": -1, "u": -1}


def encode_tls_state(signal: str) -> list[int]:
    """연결 순서를 유지해 녹색 1, 황색 0, 적색 -1의 리스트를 반환한다.

    소등 등 지원하지 않는 상태를 임의의 색으로 기록하지 않고 오류로 알린다.
    """
    try:
        return [TLS_SIGNAL_VALUES[value] for value in signal]
    except KeyError as exc:
        raise ValueError(f"숫자 인코딩을 정의하지 않은 SUMO 신호 상태: {exc.args[0]!r}") from exc
