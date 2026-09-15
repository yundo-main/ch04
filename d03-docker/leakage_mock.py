# leakage_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — LLM 데이터 유출 경로 3가지를
# 각각 결정론적으로 재현하기 위한 공용 결과 타입.
#
# ch04 "4-3. LLM 데이터 유출 위험 분석" 강의안의 경로 카탈로그(P1~P8) 중:
#   1) credential_pii_leak.py       — P1(프롬프트→벤더) + P5(로그/SIEM)
#   2) multitenant_rag_leak.py      — P3(RAG 교차 테넌트)
#   3) memory_poisoning_leak.py     — P6(캐시·히스토리, Memory Poisoning)
# 을 각각 취약/보안 경로로 재현한다.
#
# 주의(잔여 위험 고지): 실제 API 키/PII 값은 전부 가짜(더미) 데이터다. 데이터
# 유출이 "일어났는가"만 판정 가능한 안전한 예시로 구성했다 — 실제 민감정보를
# 다루는 코드가 아니다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Verdict:
    text: str
    leaked: bool
    leaked_items: List[str] = field(default_factory=list)
    reason: str = ""
