# retrieval_authorization_enforcement.py
# =============================================================================
# 예제 1: Retrieval 단계 권한 재검증 — 동일 쿼리·다른 사용자 결과 집합 비교
#
# 강의안 매핑: Lab 1(권한 없는 사용자로 기밀 청크 포함 여부 확인) +
# Lab 2(동일 쿼리·다른 사용자 결과 집합 비교).
#
# ch04/d04(RAG 권한 필터링)와 ch04/d05(문서 등급 체계)에서 각각
# ACL과 classification을 설계했다면, 여기서는 그 둘이 **실제 검색 실행 지점
# (retrieval call)** 에서 매 쿼리마다 재적용되는지를 다룬다 — 설계는 맞아도
# 검색 함수가 매번 clearance를 인자로 받아 재검증하지 않으면(예: 결과를
# 캐싱해두고 재사용) 소용없다.
#
# 위협 모델
#   - 자산: classification이 서로 다른 문서가 섞인 단일 인덱스.
#   - 신뢰 경계: "검색 함수가 매 호출마다 requester의 clearance를 입력받아
#     그 안에서만 검색한다" ↔ "검색 함수는 유사도만 계산하고, 결과를 어떤
#     사용자에게 보여줄지는 호출부가 알아서 처리한다". 후자로 구현하면 검색
#     결과 자체에 상위 등급 문서가 이미 포함된 채로 나온다.
#   - 공격자 역량: 정상 로그인한 낮은 clearance 사용자. 추가 해킹 없이 평범한
#     질문만으로 상위 등급 문서 내용이 그대로 반환된다.
#
# 재현 절차
#   python retrieval_authorization_enforcement.py
#
# 관찰 포인트
#   - vulnerable_retrieve(): 전체 인덱스에서 유사도 top-k만 계산 → 낮은
#     clearance 사용자에게도 Restricted 문서가 그대로 반환된다(L1 결과에
#     Restricted 문서가 섞여 나옴 = L4 결과와 동일).
#   - secure_retrieve(): 검색 실행 전에 requester_clearance로 후보를 먼저
#     제한 → 동일 쿼리라도 사용자 clearance에 따라 결과 집합이 달라진다.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from retrieval_security_mock import Classification, Clearance, Verdict


@dataclass
class Document:
    doc_id: str
    classification: Classification
    text: str


def load_corpus(path: str = "documents.json") -> List[Document]:
    """이 폴더 전용 로컬 복사본을 쓴다(d00-shared 공유 없음) — 로컬(venv)/Docker
    어디서든 이 파일과 같은 디렉터리에서 찾는다."""
    doc_path = Path(__file__).resolve().parent / path
    with open(doc_path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Document(d["doc_id"], Classification[d["classification"].upper()], d["text"]) for d in raw]


CORPUS = load_corpus()


def keyword_search(query: str, docs: List[Document], top_k: int = 2) -> List[Document]:
    """임베딩 대신 단순 키워드 겹침으로 검색 (재현성을 위해 API 의존 제거)."""
    scored = []
    q_tokens = set(query)
    for doc in docs:
        overlap = len(q_tokens & set(doc.text))
        scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def vulnerable_retrieve(requester_clearance: Clearance, query: str) -> Verdict:
    """취약 구현: clearance와 무관하게 전체 인덱스에서 top-k를 계산한다."""
    hits = keyword_search(query, CORPUS, top_k=2)
    over_clearance_hits = [d for d in hits if requester_clearance < d.classification]

    text = "\n".join(f"[{d.doc_id}/{d.classification.name}] {d.text}" for d in hits)
    return Verdict(
        text=text,
        leaked=bool(over_clearance_hits),
        leaked_items=[d.doc_id for d in over_clearance_hits],
        reason="검색 함수가 clearance를 입력받지 않고 전체 인덱스에서 유사도만으로 top-k를 계산함",
    )


def secure_retrieve(requester_clearance: Clearance, query: str) -> Verdict:
    """보안 구현: 검색 실행 전에 clearance로 후보 인덱스를 먼저 제한한다."""
    scoped_corpus = [d for d in CORPUS if requester_clearance >= d.classification]
    hits = keyword_search(query, scoped_corpus, top_k=2)
    over_clearance_hits = [d for d in hits if requester_clearance < d.classification]  # 항상 빈 리스트여야 함

    text = "\n".join(f"[{d.doc_id}/{d.classification.name}] {d.text}" for d in hits) or "관련 문서를 찾을 수 없습니다."
    return Verdict(
        text=text,
        leaked=bool(over_clearance_hits),
        leaked_items=[d.doc_id for d in over_clearance_hits],
        reason="검색 실행 전 requester_clearance로 후보 인덱스를 먼저 제한(재검증)",
    )


def main() -> None:
    query = "접속 정보 및 절차 안내"

    print("=" * 70)
    print("예제 1: Retrieval 단계 권한 재검증 — 동일 쿼리·다른 사용자 비교")
    print("=" * 70)
    print(f"[질문] {query!r} (L1과 L4 두 사용자가 동일하게 질의)\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_retrieve()")
    print("-" * 70)
    vuln_low = vulnerable_retrieve(Clearance.L1, query)
    vuln_high = vulnerable_retrieve(Clearance.L4, query)
    print(f"L1 결과:\n{vuln_low.text}\n")
    print(f"L4 결과:\n{vuln_high.text}\n")
    print(f"L1==L4 결과 동일 = {vuln_low.text == vuln_high.text}")
    print(f"L1 판정: 상위 등급 유출 = {vuln_low.leaked} ({vuln_low.reason})")

    print()
    print("-" * 70)
    print("[보안 경로] secure_retrieve()")
    print("-" * 70)
    safe_low = secure_retrieve(Clearance.L1, query)
    safe_high = secure_retrieve(Clearance.L4, query)
    print(f"L1 결과:\n{safe_low.text}\n")
    print(f"L4 결과:\n{safe_high.text}\n")
    print(f"L1==L4 결과 동일 = {safe_low.text == safe_high.text}")
    print(f"L1 판정: 상위 등급 유출 = {safe_low.leaked} ({safe_low.reason})")

    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln_low.leaked is True, "취약 경로는 L1 사용자에게 상위 등급 유출이 재현돼야 한다"
    assert safe_low.leaked is False, "보안 경로는 L1 사용자에게 상위 등급 유출이 없어야 한다"
    print("PASS: 취약 경로는 clearance와 무관하게 동일 결과를 반환해 유출, 보안 경로는 사용자별로 결과 집합이 달라져 차단함을 확인.")


if __name__ == "__main__":
    main()
