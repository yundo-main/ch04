# downgrade_on_summarization.py
# =============================================================================
# 예제 3: 요약본 하향 재분류 — 청크 상속 원칙 위반(상속+상향만)
#
# 강의안 매핑: A.4(청크 상속: "문서 등급이 기본이고, 청크는 상속 + 상향만") +
# 시나리오 C "Restricted 원문을 Internal 요약으로 잘못 재분류".
#
# 위협 모델
#   - 자산: Restricted 원문에서 파생된 요약본(RAG 파이프라인이 자동 생성해
#     별도 청크로 색인하는 산출물).
#   - 신뢰 경계: "요약 서비스가 산출물의 등급을 새로 매긴다" ↔ "파생 산출물은
#     원본 등급을 상속하고 절대 하향할 수 없다"는 서로 다른 설계다. 요약
#     파이프라인이 전자로 구현되면, 원문이 Restricted여도 요약본은 훨씬 낮은
#     등급으로 색인되어 광범위하게 노출될 수 있다.
#   - 공격자 역량: 필요 없음 — 요약 파이프라인의 등급 산정 로직 결함만으로,
#     정상 사용자의 평범한 검색이 그대로 유출 경로가 된다.
#
# 재현 절차
#   python downgrade_on_summarization.py
#
# 관찰 포인트
#   - vulnerable_summarize(): 요약 서비스가 산출물의 등급을 원문과 무관하게
#     콘텐츠 길이/톤만 보고 임의로(Internal) 재산정한다 → Restricted 원문의
#     핵심 내용이 요약본을 통해 Internal 등급 사용자에게까지 노출된다.
#   - secure_summarize(): 요약본의 classification = max(원문 등급, 산정값)
#     으로 강제한다(상속 + 상향만) → 요약이라는 이유로 원문보다 낮은 등급이
#     될 수 없다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass

from doc_classification_mock import Classification, Clearance, Verdict


@dataclass
class Document:
    doc_id: str
    classification: Classification
    text: str


SOURCE = Document(
    "exec-comp-restricted",
    Classification.RESTRICTED,
    "[Restricted] 임원 보상 체계 및 개인별 스톡옵션 배분 상세 내역.",
)


def _naive_service_estimate(_summary_text: str) -> Classification:
    """요약 서비스가 콘텐츠만 보고 매기는 등급(원문 등급을 참조하지 않음)."""
    return Classification.INTERNAL


def vulnerable_summarize(source: Document) -> tuple[Document, Verdict]:
    """취약 구현: 요약본 등급을 원문과 무관하게 서비스 추정값으로만 결정한다."""
    summary_text = f"{source.text[:20]}... (요약)"
    estimated = _naive_service_estimate(summary_text)
    summary = Document(f"{source.doc_id}-summary", estimated, summary_text)

    downgraded = summary.classification < source.classification
    return summary, Verdict(
        text=f"[{summary.doc_id}] classification={summary.classification.name} (원문: {source.classification.name})",
        leaked=downgraded,
        leaked_items=[summary.doc_id] if downgraded else [],
        reason="요약 서비스 추정 등급을 원문 등급 검증 없이 그대로 사용(하향 발생)",
    )


def secure_summarize(source: Document) -> tuple[Document, Verdict]:
    """보안 구현: 요약본 등급 = max(원문 등급, 서비스 추정값) — 상속 + 상향만 허용."""
    summary_text = f"{source.text[:20]}... (요약)"
    estimated = _naive_service_estimate(summary_text)
    enforced = max(estimated, source.classification)
    summary = Document(f"{source.doc_id}-summary", enforced, summary_text)

    downgraded = summary.classification < source.classification  # 항상 False여야 함
    return summary, Verdict(
        text=f"[{summary.doc_id}] classification={summary.classification.name} (원문: {source.classification.name})",
        leaked=downgraded,
        reason="요약본 등급을 max(원문, 추정값)으로 강제(상속 + 상향만, 하향 금지)",
    )


def search(requester_clearance: Clearance, doc: Document) -> bool:
    """B.1 클리어런스 모델: 요약본이 요청자 clearance 안에서 검색되는지 확인."""
    return requester_clearance >= doc.classification


def main() -> None:
    requester = Clearance.L2  # Internal까지만 봐야 정상 (Restricted 원문은 접근 불가)

    print("=" * 70)
    print("예제 3: 요약본 하향 재분류 — 청크 상속 원칙 위반")
    print("=" * 70)
    print(f"[원문] {SOURCE.doc_id} — classification={SOURCE.classification.name}")
    print(f"[요청자] clearance={requester.name} (Restricted 원문은 접근 불가해야 함)\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_summarize()")
    print("-" * 70)
    vuln_summary, vuln = vulnerable_summarize(SOURCE)
    can_see_vuln = search(requester, vuln_summary)
    print(f"결과: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 요청자가 요약본을 볼 수 있음 = {can_see_vuln} / 하향 발생 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_summarize()")
    print("-" * 70)
    safe_summary, safe = secure_summarize(SOURCE)
    can_see_safe = search(requester, safe_summary)
    print(f"결과: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 요청자가 요약본을 볼 수 있음 = {can_see_safe} / 하향 발생 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True and can_see_vuln is True, "취약 경로는 하향으로 인한 요청자 노출이 재현돼야 한다"
    assert safe.leaked is False and can_see_safe is False, "보안 경로는 상속+상향 강제로 요청자에게 노출되지 않아야 한다"
    print("PASS: 취약 경로는 요약본이 Internal로 하향돼 노출, 보안 경로는 max(원문,추정) 강제로 Restricted 유지되어 차단됨을 확인.")


if __name__ == "__main__":
    main()
