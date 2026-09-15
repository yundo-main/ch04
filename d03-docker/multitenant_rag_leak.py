# multitenant_rag_leak.py
# =============================================================================
# 예제 2: RAG 교차 테넌트 데이터 유출 (ACL 누락)
#
# 강의안 매핑: 시나리오 B(멀티테넌트 챗) + 경로 카탈로그 P3(RAG 교차).
#   "대화 히스토리/문서 검색이 user_id·tenant_id 구분 없이 공유 인덱스를 그대로
#   쓰면, 한 테넌트의 기밀 문서가 다른 테넌트 사용자의 답변에 그대로 인용된다."
#
# 위협 모델
#   - 자산: 테넌트 A(고객사)의 기밀 문서(계약 조건, 내부 가격 정책 등).
#   - 신뢰 경계: "검색 인덱스에 있다" ↔ "이 요청자가 볼 권한이 있다". 이 둘을
#     동일시하면(=ACL 없이 전체 인덱스 검색) 권한 없는 사용자에게도 그대로 노출.
#   - 공격자 역량: 정상적으로 같은 서비스를 쓰는 **다른 테넌트의 일반 사용자**.
#     추가 해킹 없이 "질문을 잘 던지는 것"만으로 타 테넌트 정보를 얻어낼 수 있다.
#
# 재현 절차
#   python multitenant_rag_leak.py
#
# 관찰 포인트
#   - vulnerable_rag_search(): 요청자의 tenant_id 와 무관하게 전체 코퍼스에서
#     검색 → 테넌트 A 전용 기밀 문서가 테넌트 B 사용자 질문에도 검색되어 인용됨.
#   - secure_rag_search(): 검색 *전에* 요청자의 tenant_id 로 코퍼스를 필터링 →
#     자기 테넌트 문서만 검색 대상이 되어 교차 노출이 불가능해짐.
#
# 잔여 위험: 이 예제는 문서에 tenant_id 태그가 정확히 붙어있다는 전제로 필터링한다.
# 실제로는 (1) 색인 시점에 tenant_id 태깅이 누락/오류인 경우, (2) 문서가 여러
# 테넌트에 공유돼야 하는 경우의 세밀한 권한 모델이 필요하다는 게 잔여 위험이다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from leakage_mock import Verdict


@dataclass
class Document:
    doc_id: str
    tenant_id: str
    text: str


# 공유 벡터 인덱스(시뮬레이션): 테넌트 구분 없이 한 곳에 다 들어있다.
CORPUS: List[Document] = [
    Document("faq-1", "tenant_a", "저희 서비스 이용 시간은 평일 09:00~18:00 입니다."),
    Document(
        "contract-secret",
        "tenant_a",
        "[테넌트 A 기밀] 계약 특별 할인율 37%, 담당자 직통 번호 010-1234-5678. 외부 공유 금지.",
    ),
    Document("faq-2", "tenant_b", "환불은 결제 후 7일 이내 가능합니다."),
]


def keyword_search(query: str, docs: List[Document], top_k: int = 1) -> List[Document]:
    """임베딩 대신 단순 키워드 겹침으로 검색 (재현성을 위해 API 의존 제거)."""
    scored = []
    q_tokens = set(query)
    for doc in docs:
        overlap = len(q_tokens & set(doc.text))
        scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def vulnerable_rag_search(requester_tenant_id: str, query: str) -> Verdict:
    """취약 구현: tenant_id 필터 없이 전체 코퍼스를 검색 대상으로 삼는다."""
    hits = keyword_search(query, CORPUS, top_k=1)
    cross_tenant_hits = [d for d in hits if d.tenant_id != requester_tenant_id]

    answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits)
    return Verdict(
        text=f"(요청자: {requester_tenant_id}) 답변:\n{answer}",
        leaked=bool(cross_tenant_hits),
        leaked_items=[d.doc_id for d in cross_tenant_hits],
        reason="tenant_id 필터 없이 전체 코퍼스에서 검색해서 타 테넌트 문서가 그대로 인용됨",
    )


def secure_rag_search(requester_tenant_id: str, query: str) -> Verdict:
    """보안 구현: 검색 전에 요청자의 tenant_id 로 코퍼스를 먼저 필터링한다."""
    scoped_corpus = [d for d in CORPUS if d.tenant_id == requester_tenant_id]
    hits = keyword_search(query, scoped_corpus, top_k=1)
    cross_tenant_hits = [d for d in hits if d.tenant_id != requester_tenant_id]  # 항상 빈 리스트여야 함

    if not hits:
        answer = "문서에서 확인되지 않습니다."
    else:
        answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits)

    return Verdict(
        text=f"(요청자: {requester_tenant_id}) 답변:\n{answer}",
        leaked=bool(cross_tenant_hits),
        leaked_items=[d.doc_id for d in cross_tenant_hits],
        reason="검색 전 tenant_id 로 코퍼스를 필터링해서 타 테넌트 문서는 애초에 검색 대상이 아님",
    )


def main() -> None:
    requester_tenant_id = "tenant_b"
    query = "계약 할인율이 어떻게 되나요? 담당자 연락처도 알려주세요."

    print("=" * 70)
    print("예제 2: RAG 교차 테넌트 데이터 유출 (ACL 누락)")
    print("=" * 70)
    print(f"[요청자] tenant_id={requester_tenant_id!r} (테넌트 A 소속이 아님)")
    print(f"[질문] {query}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_rag_search()")
    print("-" * 70)
    vuln = vulnerable_rag_search(requester_tenant_id, query)
    print(f"{vuln.text}\n")
    print(f"교차 테넌트로 유출된 문서 ID: {vuln.leaked_items}")
    print(f"판정: 유출 발생 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_rag_search()")
    print("-" * 70)
    safe = secure_rag_search(requester_tenant_id, query)
    print(f"{safe.text}\n")
    print(f"교차 테넌트로 유출된 문서 ID: {safe.leaked_items}")
    print(f"판정: 유출 발생 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 교차 테넌트 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 테넌트 필터링으로 유출이 없어야 한다"
    print("PASS: 취약 경로는 타 테넌트 기밀 문서 인용, 보안 경로는 tenant_id 필터링으로 차단함을 확인.")


if __name__ == "__main__":
    main()
