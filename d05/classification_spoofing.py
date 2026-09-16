# classification_spoofing.py
# =============================================================================
# 예제 2: 클라이언트 주장 등급 vs 서버 검증 등급 (등급 위조)
#
# 강의안 매핑: 시나리오 B "클라이언트가 classification=public으로 재색인
# 요청, 서버 오너 검증 없음" + A.3(인제스트 게이트: 오너 확인 단계).
#
# 위협 모델
#   - 자산: 이미 Restricted로 색인된 문서를 더 낮은 등급으로 재색인(하향)할
#     수 있는 재색인(reindex) API.
#   - 신뢰 경계: "재색인 요청에 담긴 classification 값" ↔ "문서 오너/DLP가
#     실제로 검증한 등급". 재색인 API가 요청 필드를 그대로 신뢰하면, 문서를
#     수정할 수 있는 사용자 누구나 등급을 스스로 낮춰 재색인할 수 있다.
#   - 공격자 역량: 문서 편집 권한은 있지만 등급 변경 권한(오너 승인)은 없는
#     내부자. API 요청 바디의 classification 필드만 바꿔 보내면 된다 —
#     별도 해킹이나 권한 상승 없이도 재현된다.
#
# 재현 절차
#   python classification_spoofing.py
#
# 관찰 포인트
#   - vulnerable_reindex(): 요청에 실려온 classification을 그대로 신뢰해서
#     재색인한다 → Restricted 원문이 요청자가 주장한 Public으로 그대로
#     낮아진다.
#   - secure_reindex(): 하향 재색인은 오너 승인 플래그(owner_approved)가
#     없으면 거부하고 기존 등급을 유지한다 → 클라이언트 주장과 무관하게
#     검증된 절차 없이는 등급이 낮아지지 않는다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass

from doc_classification_mock import Classification, Verdict


@dataclass
class Document:
    doc_id: str
    classification: Classification
    text: str


ORIGINAL = Document(
    "ma-duediligence-report",
    Classification.RESTRICTED,
    "[Restricted] A사 인수 실사 보고서: 재무 리스크 및 임원진 평가 포함.",
)


def vulnerable_reindex(doc: Document, requested_classification: Classification, owner_approved: bool) -> Verdict:
    """취약 구현: 요청에 실려온 classification을 오너 검증 없이 그대로 반영한다."""
    new_doc = Document(doc.doc_id, requested_classification, doc.text)
    downgraded = new_doc.classification < doc.classification
    return Verdict(
        text=f"[{new_doc.doc_id}] classification={new_doc.classification.name} (기존: {doc.classification.name})",
        leaked=downgraded,
        leaked_items=[new_doc.doc_id] if downgraded else [],
        reason=f"오너 검증 없이 요청 필드 classification={requested_classification.name} 을 그대로 반영",
    )


def secure_reindex(doc: Document, requested_classification: Classification, owner_approved: bool) -> Verdict:
    """보안 구현: 하향 요청은 오너 승인(owner_approved)이 없으면 거부하고 기존 등급을 유지한다."""
    is_downgrade = requested_classification < doc.classification
    if is_downgrade and not owner_approved:
        return Verdict(
            text=f"[{doc.doc_id}] classification={doc.classification.name} (하향 요청 거부, 기존 유지)",
            leaked=False,
            reason="하향 재색인 요청이나 오너 승인이 없어 거부(기존 등급 유지)",
        )
    new_doc = Document(doc.doc_id, requested_classification, doc.text)
    return Verdict(
        text=f"[{new_doc.doc_id}] classification={new_doc.classification.name}",
        leaked=False,
        reason="오너 승인 확인 후 등급 변경 적용" if is_downgrade else "상향 또는 동일 등급이라 즉시 적용",
    )


def main() -> None:
    requested_classification = Classification.PUBLIC  # 공격자가 재색인 요청에 적어 보낸 값
    owner_approved = False  # 실제로는 오너 승인을 받지 않음

    print("=" * 70)
    print("예제 2: 클라이언트 주장 등급 vs 서버 검증 등급 (등급 위조)")
    print("=" * 70)
    print(f"[원본 문서] {ORIGINAL.doc_id} — classification={ORIGINAL.classification.name}")
    print(f"[재색인 요청] classification={requested_classification.name}, owner_approved={owner_approved}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_reindex()")
    print("-" * 70)
    vuln = vulnerable_reindex(ORIGINAL, requested_classification, owner_approved)
    print(f"결과: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 등급 하향 유출 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_reindex()")
    print("-" * 70)
    safe = secure_reindex(ORIGINAL, requested_classification, owner_approved)
    print(f"결과: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 등급 하향 유출 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 오너 검증 없는 하향 재색인이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 오너 승인 없는 하향 요청을 거부해야 한다"
    print("PASS: 취약 경로는 요청 필드만으로 Restricted→Public 하향을 허용, 보안 경로는 오너 승인 없이는 거부함을 확인.")


if __name__ == "__main__":
    main()
