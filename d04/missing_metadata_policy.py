# missing_metadata_policy.py
# =============================================================================
# 예제 3: ACL 메타데이터 누락 — Fail-open vs Fail-closed
#
# 강의안 매핑: B.3(실패 모드) "메타 누락 시 기본 공개 → 대규모 유출" +
# 시나리오 A "메타 없이 전 직원 인덱스" (부서 위키 + 인사 폴더가 같은 컬렉션에
# 색인되는데, 마이그레이션 때 일부 문서에 ACL 태그를 안 붙인 경우).
#
# 위협 모델
#   - 자산: 예전에 색인됐지만 ACL 메타데이터 태깅이 누락된 레거시 문서(관행상
#     비공개였어야 하는 인사 문서 등).
#   - 신뢰 경계: "메타데이터가 없다" ↔ "메타데이터가 없으니 공개해도 된다"는
#     서로 다른 명제다. 색인 파이프라인이 후자로 잘못 구현되면, 태깅을 깜빡한
#     모든 문서가 기본값으로 전체 공개된다.
#   - 공격자 역량: 필요 없음 — 정상 사용자의 평범한 질문만으로 마이그레이션
#     실수가 그대로 유출로 이어진다(강의안 A.2 "유출 ≠ 해킹만"과 같은 맥락).
#
# 재현 절차
#   python missing_metadata_policy.py
#
# 관찰 포인트
#   - vulnerable_retrieve() [fail-open]: ACL 메타데이터가 없는 문서는 "제한이
#     없으니 공개"로 기본 처리한다 → 태깅을 깜빡한 인사 평가 문서가 아무 role
#     에게나 노출된다.
#   - secure_retrieve() [fail-closed]: ACL 메타데이터가 없거나 불완전한 문서는
#     "가장 제한적인 것"으로 기본 처리해 검색 후보에서 제외한다 → 태깅 누락이
#     유출로 이어지지 않는다(대신 그 문서는 아무한테도 안 보인다는 부작용은 있음
#     — 아래 잔여 위험 참고).
#
# 잔여 위험: fail-closed 는 "안전하지만 가용성을 희생"하는 선택이다. 태깅이
# 누락된 **공개용** 문서(원래는 아무나 봐도 되는 것)까지 덩달아 숨겨진다 —
# 그래서 fail-closed 는 임시방편이고, 근본 해결은 색인 파이프라인에서 ACL
# 태깅을 필수 필드로 강제하는 것이다(아래 잔여 위험 절 참고).
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from rag_acl_mock import Verdict


@dataclass
class Document:
    doc_id: str
    allowed_roles: Optional[set]  # None = 마이그레이션 때 ACL 태깅을 깜빡함
    text: str


CORPUS: List[Document] = [
    Document("it-onboarding-guide", {"guest", "employee", "hr", "admin"}, "신규 입사자 IT 계정 발급 안내입니다."),
    # 마이그레이션 때 ACL 태깅을 깜빡한 문서 — 원래는 hr 전용이어야 했다.
    Document(
        "perf-review-2025-legacy",
        None,
        "[인사평가] 2025년 하반기 개인별 평가 등급 및 승진 대상자 명단 (레거시 인덱스, 태깅 누락).",
    ),
]


def keyword_search(query: str, docs: List[Document], top_k: int = 1) -> List[Document]:
    scored = []
    q_tokens = set(query)
    for doc in docs:
        overlap = len(q_tokens & set(doc.text))
        scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def vulnerable_retrieve(requester_role: str, query: str) -> Verdict:
    """취약 구현 (fail-open): ACL 메타데이터가 없으면 '제한 없음'으로 취급한다."""
    def _is_allowed(doc: Document) -> bool:
        if doc.allowed_roles is None:
            return True  # 메타 없음 = 기본 공개(위험한 기본값)
        return requester_role in doc.allowed_roles

    scoped_corpus = [d for d in CORPUS if _is_allowed(d)]
    hits = keyword_search(query, scoped_corpus, top_k=1)
    leaked = [d for d in hits if d.allowed_roles is None]

    answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits) if hits else "관련 문서를 찾을 수 없습니다."
    return Verdict(
        text=answer,
        leaked=bool(leaked),
        leaked_items=[d.doc_id for d in leaked],
        reason="ACL 메타데이터가 없는 문서를 '제한 없음(공개)'으로 기본 처리(fail-open)",
    )


def secure_retrieve(requester_role: str, query: str) -> Verdict:
    """보안 구현 (fail-closed): ACL 메타데이터가 없으면 '가장 제한적'으로 취급해 제외한다."""
    def _is_allowed(doc: Document) -> bool:
        if doc.allowed_roles is None:
            return False  # 메타 없음 = 기본 차단(deny by default)
        return requester_role in doc.allowed_roles

    scoped_corpus = [d for d in CORPUS if _is_allowed(d)]
    hits = keyword_search(query, scoped_corpus, top_k=1)
    leaked = [d for d in hits if d.allowed_roles is None]  # 항상 빈 리스트여야 함

    answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits) if hits else "관련 문서를 찾을 수 없습니다."
    return Verdict(
        text=answer,
        leaked=bool(leaked),
        leaked_items=[d.doc_id for d in leaked],
        reason="ACL 메타데이터가 없는 문서를 '가장 제한적(비공개)'으로 기본 처리(fail-closed, deny by default)",
    )


def main() -> None:
    requester_role = "employee"  # hr 아님
    query = "인사평가 승진 대상자 명단 보여줘"

    print("=" * 70)
    print("예제 3: ACL 메타데이터 누락 — Fail-open vs Fail-closed")
    print("=" * 70)
    print(f"[요청자] role={requester_role!r}")
    print(f"[질문] {query}")
    print("[코퍼스 상태] perf-review-2025-legacy 문서는 마이그레이션 때 ACL 태깅 누락(allowed_roles=None)\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_retrieve() — fail-open")
    print("-" * 70)
    vuln = vulnerable_retrieve(requester_role, query)
    print(f"응답: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 유출 발생 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_retrieve() — fail-closed")
    print("-" * 70)
    safe = secure_retrieve(requester_role, query)
    print(f"응답: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 유출 발생 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 fail-open 으로 인한 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 fail-closed 로 유출이 없어야 한다"
    print("PASS: 취약 경로는 태깅 누락 문서를 기본 공개해서 유출, 보안 경로는 기본 차단(deny by default)으로 막음을 확인.")


if __name__ == "__main__":
    main()
