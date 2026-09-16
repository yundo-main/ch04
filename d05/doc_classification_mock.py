# doc_classification_mock.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — 문서 보안 등급 체계 설계의 3가지
# 실패 지점을 각각 결정론적으로 재현하기 위한 공용 타입.
#
# ch04 "4-5. 문서 보안 등급 체계 설계" 강의안 매핑:
#   1) default_classification_missing.py — 시나리오 A(기본값 Public), A.3(인제스트 게이트)
#   2) classification_spoofing.py        — 시나리오 B(등급 위조), A.3(오너 확인)
#   3) downgrade_on_summarization.py     — 시나리오 C(요약본 하향), A.4(청크 상속: 상속+상향만)
#
# 주의(잔여 위험 고지): 문서 내용/조직 정보는 전부 가짜(더미) 데이터다.
# 등급 체계가 "우회됐는가"만 판정 가능한 안전한 예시로 구성했다.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import List


class Classification(IntEnum):
    """강의안 A.2 표준 등급. 숫자가 클수록 민감도가 높다."""

    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class Clearance(IntEnum):
    """강의안 B.1 사용자 clearance. L1~L4가 검색 가능한 최대 등급과 1:1 대응한다."""

    L1 = 0  # Public까지
    L2 = 1  # Internal까지
    L3 = 2  # Confidential까지
    L4 = 3  # Restricted까지


@dataclass
class Verdict:
    text: str
    leaked: bool
    leaked_items: List[str] = field(default_factory=list)
    reason: str = ""


def load_sample_documents(path: str = "documents.json") -> List[dict]:
    """guide.md 등급 정의서에 따라 태깅된 샘플 문서 세트를 로드한다.

    ch04/shared/documents.json 을 공유한다(d05~d08 이 같은 문서 세트를 쓴다) —
    이 폴더에는 로컬 복사본이 없다. 로컬(venv) 실행 시에는 ch04/shared/ 형제
    디렉터리에서 찾고, Docker 이미지 안(빌드 시 shared/ 를 같은 디렉터리로
    평탄화해서 COPY 함)에서는 이 파일과 같은 디렉터리에서 찾는다.

    각 문서의 classification 값이 Classification 열거형에 없는 값이면 KeyError로
    실패한다 — 등급 정의서에 없는 등급이 슬쩍 섞여 들어오는 것을 막기 위한 검증.
    """
    here = Path(__file__).resolve().parent
    shared_candidate = here.parent / "shared" / path
    doc_path = shared_candidate if shared_candidate.exists() else here / path
    with open(doc_path, encoding="utf-8") as f:
        raw = json.load(f)
    for doc in raw:
        Classification[doc["classification"].upper()]
    return raw
