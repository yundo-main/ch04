# jailbreak_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 '가짜 LLM' — 3개 탈옥(jailbreak) 기법을
# 각각 결정론적으로 재현하기 위한 공용 결과 타입과 헬퍼.
#
# 프롬프트 인젝션(ch04/d01-docker)이 "명령/데이터 채널이 안 섞여도 모델이 뚫릴 수
# 있다"를 보여줬다면, 여기서는 "안전 정책 자체를 우회하는" 세 가지 서로 다른
# 기법을 다룬다:
#   1) persona_jailbreak.py   — 페르소나/역할극으로 정책을 재정의하려는 시도
#   2) escalation_jailbreak.py — 여러 턴에 걸쳐 점진적으로 위험 수위를 높이는 시도
#   3) encoding_jailbreak.py   — Base64 등으로 인코딩해 키워드 필터를 우회하는 시도
#
# 주의(잔여 위험 고지): 실제 위험한 콘텐츠(무기 제작법 등)는 어디에도 포함하지
# 않는다. "정책 우회가 실제로 일어났는가"만 판정 가능한 안전한 플레이스홀더 문자열로
# 대체한다 — 방어 메커니즘 학습이 목적이지, 실제 유해 콘텐츠 생성이 목적이 아니다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Verdict:
    text: str
    jailbroken: bool
    reason: str = ""
    matched: List[str] = field(default_factory=list)
