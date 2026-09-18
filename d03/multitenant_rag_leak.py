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

import sys
from dataclasses import dataclass
from typing import List

from leakage_mock import Verdict
from wrapper import DEFAULT_MODEL, ask_real, is_ollama_available  # noqa: E402
from prompts import MULTITENANT_QUERY, RAG_ANSWER_SYSTEM_INSTRUCTION  # noqa: E402


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
    if "--mock" not in sys.argv and not is_ollama_available():
        print("LLM 연결 안됨: Ollama 서버(http://localhost:11434)에 연결할 수 없습니다.")
        print("Ollama 설치/서버 실행 여부를 확인하거나 --mock으로 실행하세요.")
        return

    requester_tenant_id = "tenant_b"
    query = MULTITENANT_QUERY

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

    if "--mock" not in sys.argv:
        run_real()


def run_real(model: str = DEFAULT_MODEL) -> None:
    """실제 로컬 소형 LLM(Ollama)에 필터링 전/후 검색 컨텍스트를 넘겨, 실제
    응답에 타 테넌트 기밀 문서 내용이 그대로 인용되는지 관찰한다.
    """
    print()
    print("=" * 70)
    print(f"[실제 모델] Ollama ({model}) 대상 재현")
    print("=" * 70)

    requester_tenant_id = "tenant_b"
    query = MULTITENANT_QUERY
    system_instruction = RAG_ANSWER_SYSTEM_INSTRUCTION

    vuln_hits = keyword_search(query, CORPUS, top_k=1)
    safe_hits = keyword_search(query, [d for d in CORPUS if d.tenant_id == requester_tenant_id], top_k=1)

    def _build_prompt(hits: List[Document]) -> str:
        context = "\n".join(f"- {d.text}" for d in hits) if hits else "(참고할 문서 없음)"
        return f"[참고 문서]\n{context}\n\n[질문] {query}"

    print("[취약 경로] tenant_id 필터 없이 검색된 컨텍스트로 응답 생성")
    vuln = ask_real(system_instruction, _build_prompt(vuln_hits), model=model)
    if not vuln.ok:
        print(f"호출 실패: {vuln.error}")
    else:
        print(f"응답:\n{vuln.text}\n")
        print(f"응답에 '37%' 또는 '010-1234'(테넌트 A 기밀) 포함 여부: {('37%' in vuln.text) or ('010-1234' in vuln.text)}")

    print()
    print("[보안 경로] tenant_id 로 필터링된 컨텍스트로 응답 생성")
    safe = ask_real(system_instruction, _build_prompt(safe_hits), model=model)
    if not safe.ok:
        print(f"호출 실패: {safe.error}")
    else:
        print(f"응답:\n{safe.text}\n")
        print(f"응답에 '37%' 또는 '010-1234'(테넌트 A 기밀) 포함 여부: {('37%' in safe.text) or ('010-1234' in safe.text)}")

    print(
        "\n참고: 보안 경로도 모델이 컨텍스트에 없는 내용을 환각으로 지어낼 수는 있다 — "
        "다만 그 경우는 '실제 테넌트 A 데이터 유출'이 아니라 별도의 환각 문제다."
    )


if __name__ == "__main__":
    main()
