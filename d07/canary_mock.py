# canary_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — Canary Token 활용의 3가지
# 실패 지점을 각각 결정론적으로 재현하기 위한 공용 타입.
#
# ch04 "4-7. Canary Token 활용" 매핑:
#   1) canary_placement.py           — Lab 1(토큰 배치), 출처 특정(attribution)
#   2) response_canary_scanning.py   — Lab 2(탐지: 매칭 시 차단·로그)
#   3) exfiltration_simulation.py    — Lab 3(시뮬레이션: 인코딩 우회 탐지)
#
# 주의(잔여 위험 고지): 문서 내용/조직 정보/canary 값은 전부 가짜(더미)
# 데이터다. canary_token은 실제 시크릿이 아니라 유출 탐지·출처 추적 전용
# 워터마크 문자열이다.
# =============================================================================

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Document:
    doc_id: str
    classification: str
    owner: str
    canary_token: str
    text: str


@dataclass
class Verdict:
    text: str
    leaked: bool
    leaked_items: List[str] = field(default_factory=list)
    reason: str = ""


def load_canary_documents(path: str = "documents.json") -> List[Document]:
    """canary_token이 심어진 실습용 decoy 문서 세트를 로드한다.

    이 폴더 전용 로컬 복사본을 쓴다(d00-shared 공유 없음). 세트에는
    canary_token 이 없는 일반 문서도 섞여 있으므로, canary_token 이 실제로
    있는 문서만 골라 쓰고(Document 가 모르는 나머지 필드는 무시한다).
    """
    doc_path = Path(__file__).resolve().parent / path
    with open(doc_path, encoding="utf-8") as f:
        raw = json.load(f)
    valid_fields = {field_.name for field_ in dataclasses.fields(Document)}
    return [
        Document(**{k: v for k, v in d.items() if k in valid_fields})
        for d in raw
        if d.get("canary_token")
    ]
