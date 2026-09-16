# default_classification_missing.py
# =============================================================================
# 예제 1: 인제스트 시 등급 미지정 — 기본값 Public 취약점
#
# 강의안 매핑: 시나리오 A "업로드 API 기본 classification 누락 → 전부 검색
# 가능" + A.3(인제스트 게이트: "등급 미지정 → 임베딩 거부 또는 quarantine").
#
# 위협 모델
#   - 자산: 업로드 API를 통해 색인되는 신규 문서 전체.
#   - 신뢰 경계: "업로드 요청에 classification 필드가 없다" ↔ "그 문서는
#     Public로 취급해도 된다"는 서로 다른 명제다. 인제스트 파이프라인이
#     전자를 후자로 잘못 처리하면, 등급을 깜빡 지정하지 않은 모든 신규 문서가
#     기본값으로 전체 공개된다.
#   - 공격자 역량: 필요 없음 — 정상 업로드 플로우에서 담당자가 필드 하나를
#     빠뜨리는 것만으로 재현된다(해킹이 아니라 운영 실수가 유출 경로).
#
# 재현 절차
#   python default_classification_missing.py
#
# 관찰 포인트
#   - vulnerable_ingest_and_search(): classification 필드가 없는 업로드를
#     기본값 Classification.PUBLIC 으로 색인한다 → L1(가장 낮은 clearance)
#     사용자도 검색 결과에서 그 문서를 그대로 받는다.
#   - secure_ingest_and_search(): classification 필드가 없는 업로드는
#     quarantine(검색 후보에서 제외)하고 색인을 보류한다 → 등급 미지정이
#     즉시 유출로 이어지지 않는다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from doc_classification_mock import Classification, Clearance, Verdict, load_sample_documents


@dataclass
class Document:
    doc_id: str
    classification: Optional[Classification]  # None = 업로드 시 등급 미지정
    text: str


def vulnerable_ingest(raw_uploads: List[dict]) -> List[Document]:
    """취약 구현: classification 누락 시 기본값 Public으로 색인한다."""
    docs = []
    for u in raw_uploads:
        classification = u.get("classification")
        if classification is None:
            classification = Classification.PUBLIC  # 위험한 기본값
        docs.append(Document(u["doc_id"], classification, u["text"]))
    return docs


def secure_ingest(raw_uploads: List[dict]) -> List[Document]:
    """보안 구현: classification 누락 시 색인을 보류(quarantine)한다."""
    docs = []
    for u in raw_uploads:
        classification = u.get("classification")
        # quarantine: 등급이 없으면 검색 후보에 아예 넣지 않는다(None 유지).
        docs.append(Document(u["doc_id"], classification, u["text"]))
    return docs


def search(requester_clearance: Clearance, docs: List[Document]) -> List[Document]:
    """B.1 클리어런스 모델: user.clearance >= doc.classification 인 문서만 반환."""
    return [
        d
        for d in docs
        if d.classification is not None and requester_clearance >= d.classification
    ]


# guide.md 등급 정의서에 따라 태깅된 샘플 문서 세트(documents.json)에서
# Public 등급 문서를 정상 업로드 베이스라인으로 가져온다.
_SAMPLE_DOCS = load_sample_documents()
RAW_UPLOADS = [
    {"doc_id": d["doc_id"], "classification": Classification[d["classification"].upper()], "text": d["text"]}
    for d in _SAMPLE_DOCS
    if d["classification"] == "public"
] + [
    # 담당자가 업로드 폼에서 등급 선택을 빠뜨린 케이스 — 실제로는 M&A 관련 초안(원래 Restricted 대상).
    {"doc_id": "ma-draft-2025", "text": "[초안] A사 인수 관련 실사 자료 및 밸류에이션 요약."},
]


def main() -> None:
    requester = Clearance.L1  # 가장 낮은 clearance: Public만 봐야 정상

    print("=" * 70)
    print("예제 1: 인제스트 시 등급 미지정 — 기본값 Public 취약점")
    print("=" * 70)
    print(f"[요청자] clearance={requester.name} (Public까지만 검색 가능해야 함)")
    print("[업로드] ma-draft-2025 는 classification 필드 누락(실사 초안, 원래는 Restricted 대상)\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_ingest() — 미지정 시 기본값 Public")
    print("-" * 70)
    vuln_docs = vulnerable_ingest(RAW_UPLOADS)
    vuln_hits = search(requester, vuln_docs)
    leaked = [d.doc_id for d in vuln_hits if d.doc_id == "ma-draft-2025"]
    vuln = Verdict(
        text="\n".join(f"[{d.doc_id}] {d.text}" for d in vuln_hits),
        leaked=bool(leaked),
        leaked_items=leaked,
        reason="classification 미지정 문서를 Public으로 기본 처리(fail-open)",
    )
    print(f"검색 결과:\n{vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 등급 미지정 문서 유출 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_ingest() — 미지정 시 quarantine")
    print("-" * 70)
    safe_docs = secure_ingest(RAW_UPLOADS)
    safe_hits = search(requester, safe_docs)
    safe = Verdict(
        text="\n".join(f"[{d.doc_id}] {d.text}" for d in safe_hits) or "관련 문서를 찾을 수 없습니다.",
        leaked=False,
        reason="classification 미지정 문서는 quarantine 상태로 검색 후보에서 제외",
    )
    print(f"검색 결과:\n{safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 등급 미지정 문서 유출 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 기본값 Public으로 인한 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 quarantine으로 유출이 없어야 한다"
    print("PASS: 취약 경로는 등급 미지정 문서를 Public 기본값으로 노출, 보안 경로는 quarantine으로 차단함을 확인.")


if __name__ == "__main__":
    main()
