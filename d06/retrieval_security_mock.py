# retrieval_security_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — Retrieval 보안 구현의 3가지
# 실패 지점을 각각 결정론적으로 재현하기 위한 공용 타입.
#
# ch04 "4-6. Retrieval 보안 구현" 매핑:
#   1) retrieval_authorization_enforcement.py — 검색 단계 권한 재검증(Lab 1/2)
#   2) embedding_poisoning.py                 — 인제스트 단계 이상 탐지
#   3) chunk_sanitization.py                  — 응답 조립 전 청크 새니타이징
#
# 주의(잔여 위험 고지): 문서 내용/조직 정보는 전부 가짜(더미) 데이터다.
# 실제 임베딩 대신 결정론적 키워드 겹침 점수로 유사도 검색을 시뮬레이션한다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


class Classification(IntEnum):
    """ch04/d05 guide.md 등급 정의서와 동일한 4단계 등급."""

    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class Clearance(IntEnum):
    """L1~L4가 검색 가능한 최대 등급과 1:1 대응한다."""

    L1 = 0
    L2 = 1
    L3 = 2
    L4 = 3


@dataclass
class Verdict:
    text: str
    leaked: bool
    leaked_items: List[str] = field(default_factory=list)
    reason: str = ""
