---
description: staged 변경(또는 지정 범위)을 reviewer 에이전트로 리뷰 — 예: /review, /review HEAD~1, /review main...HEAD
agent: reviewer
---
리뷰 범위 인자: $ARGUMENTS
(비어 있으면 아래 staged diff를 리뷰한다. staged가 비어 있으면 작업 트리 diff를 직접 확인한다. 인자가 있으면 `git diff <인자>`로 그 범위를 직접 가져와 리뷰한다.)

## 현재 상태
!`git status --short`

## staged 변경 요약
!`git diff --staged --stat`

## staged diff
!`git diff --staged`

reviewer 지침의 0~5단계를 순서대로 따르고, 정해진 보고 형식으로만 답하라.
