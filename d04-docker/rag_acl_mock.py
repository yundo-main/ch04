# rag_acl_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — RAG 권한 필터링 설계의 3가지
# 실패 지점을 각각 결정론적으로 재현하기 위한 공용 결과 타입.
#
# ch04 "4-4. RAG 권한 필터링 설계" 강의안 매핑:
#   1) prefilter_vs_postfilter.py — A.2(필터 삽입 위치), post-filter 의 존재 여부
#      사이드채널 경고
#   2) role_spoofing.py           — B.2(인증 컨텍스트), 시나리오 B(프론트 역할 토글)
#   3) missing_metadata_policy.py — B.3(실패 모드: 메타 누락 시 기본 공개), 시나리오 A
#
# 주의(잔여 위험 고지): 문서 내용/역할/조직 정보는 전부 가짜(더미) 데이터다.
# 권한 필터링이 "우회됐는가"만 판정 가능한 안전한 예시로 구성했다.
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
