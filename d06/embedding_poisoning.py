# embedding_poisoning.py
# =============================================================================
# 예제 2: 임베딩 포이즈닝(Embedding Poisoning) — 인제스트 단계 이상 탐지 부재
#
# 강의안 매핑: 4-6 "Embedding Poisoning & Chunk Sanitization" 실습 스크립트
# (lab01_retrieval_security.py) 대응.
#
# 위협 모델
#   - 자산: 여러 주제를 넘나드는 정상 질의들에 대해 top-1 슬롯을 계속
#     차지하도록 설계된 인덱스 전체의 검색 신뢰성.
#   - 신뢰 경계: "인제스트되는 모든 문서를 동등하게 신뢰하고 유사도 점수만
#     본다" ↔ "특정 문서 하나가 서로 무관한 다수 주제 질의에 비정상적으로
#     넓게 매칭되면 색인 전에 의심한다". 전자로 구현하면, 공격자가 문서
#     하나에 여러 주제의 키워드를 인위적으로 채워 넣는 것만으로 그 문서가
#     거의 모든 질의에서 최상위로 검색되게 만들 수 있다.
#   - 공격자 역량: 인제스트 파이프라인에 문서를 하나 제출할 수 있는 권한(예:
#     공용 위키 기여, 지원 티켓 첨부 등 낮은 신뢰 경로). 검색 인프라 자체를
#     해킹할 필요는 없다 — 문서 내용만으로 검색 결과를 오염시킨다.
#
# 재현 절차
#   python embedding_poisoning.py
#
# 관찰 포인트
#   - vulnerable_ingest(): 인제스트 시 문서 내용에 대한 검증 없이 그대로
#     색인한다 → 여러 무관한 주제 키워드를 채운 poisoned 문서가 배송/환불/
#     보안 등 서로 다른 질의에서 매번 top-1을 차지해 정상 문서를 밀어낸다.
#   - secure_ingest(): 색인 전에 후보 문서를 고정된 probe 질의 세트와 비교해
#     "비정상적으로 넓은 주제 커버리지"를 탐지하면 quarantine한다 → poisoned
#     문서가 색인되지 않아 검색 결과가 오염되지 않는다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from retrieval_security_mock import Verdict


@dataclass
class Document:
    doc_id: str
    text: str


LEGITIMATE_CORPUS: List[Document] = [
    Document("shipping-faq", "배송은 결제 완료 후 평균 2~3영업일 소요됩니다."),
    Document("refund-policy", "환불은 구매 후 7일 이내, 미개봉 상품에 한해 가능합니다."),
    Document("security-2fa-guide", "2단계 인증은 설정 > 보안 메뉴에서 활성화할 수 있습니다."),
]

# 공격자가 제출한 문서: 배송/환불/보안 키워드를 모두 인위적으로 채워 넣어
# 어떤 질의가 와도 겹침 점수가 높게 나오도록 만든 poisoned 문서.
POISONED_DOC = Document(
    "poisoned-catchall",
    "배송 환불 보안 인증 결제 계정 주문 취소 로그인 비밀번호 2단계 영업일 "
    "미개봉 활성화 설정 메뉴 절차 안내 확인 처리 완료 요청 문의 지원",
)

# 서로 무관한 주제를 대표하는 고정 probe 질의 세트 — 인제스트 시 이상 탐지에 사용.
PROBE_QUERIES = ["배송 얼마나 걸려요", "환불 가능한가요", "2단계 인증 설정 방법", "계정 로그인 문제"]
POISON_TOPIC_SPREAD_THRESHOLD = 3  # 이 개수 이상의 probe에 걸리면 의심


def overlap_score(query: str, text: str) -> int:
    return len(set(query) & set(text))


def keyword_search(query: str, docs: List[Document], top_k: int = 1) -> List[Document]:
    scored = [(overlap_score(query, d.text), d) for d in docs]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def vulnerable_ingest(candidate: Document) -> List[Document]:
    """취약 구현: 인제스트 시 내용 검증 없이 그대로 색인한다."""
    return LEGITIMATE_CORPUS + [candidate]


def _topic_spread(candidate: Document) -> int:
    """candidate 문서가 서로 무관한 probe 질의 중 몇 개에서 다른 정상 문서보다 높은 점수를 내는지."""
    hits = 0
    for probe in PROBE_QUERIES:
        candidate_score = overlap_score(probe, candidate.text)
        best_legit_score = max(overlap_score(probe, d.text) for d in LEGITIMATE_CORPUS)
        # 동점도 이상 신호로 카운트한다: 특정 주제 전용 문서와 동등하게 매칭되는
        # 범용 문서는 그 자체로 "비정상적으로 넓은 커버리지"를 시사한다.
        if candidate_score >= best_legit_score:
            hits += 1
    return hits


def secure_ingest(candidate: Document) -> List[Document]:
    """보안 구현: probe 질의 커버리지가 임계치를 넘으면 quarantine(색인 제외)한다."""
    if _topic_spread(candidate) >= POISON_TOPIC_SPREAD_THRESHOLD:
        return LEGITIMATE_CORPUS  # quarantine: candidate를 색인에서 제외
    return LEGITIMATE_CORPUS + [candidate]


def main() -> None:
    test_queries = ["배송 얼마나 걸려요", "환불 규정 알려줘", "2단계 인증 켜는 법"]

    print("=" * 70)
    print("예제 2: 임베딩 포이즈닝 — 인제스트 단계 이상 탐지 부재")
    print("=" * 70)
    print(f"[공격 문서] {POISONED_DOC.doc_id} — 여러 무관한 주제 키워드를 인위적으로 채움")
    print(f"[Probe 커버리지] {_topic_spread(POISONED_DOC)} / {len(PROBE_QUERIES)} (임계치 {POISON_TOPIC_SPREAD_THRESHOLD})\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_ingest() — 검증 없이 색인")
    print("-" * 70)
    vuln_index = vulnerable_ingest(POISONED_DOC)
    hijacked = []
    for q in test_queries:
        top = keyword_search(q, vuln_index, top_k=1)[0]
        print(f"질의 {q!r} → top-1: [{top.doc_id}]")
        if top.doc_id == POISONED_DOC.doc_id:
            hijacked.append(q)
    vuln = Verdict(
        text=f"poisoned 문서가 top-1을 차지한 질의: {hijacked}",
        leaked=bool(hijacked),
        leaked_items=hijacked,
        reason="인제스트 시 주제 커버리지 검증 없이 그대로 색인(fail-open)",
    )
    print(f"\n사유: {vuln.reason}")
    print(f"판정: 검색 결과 오염 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_ingest() — probe 커버리지 이상 탐지")
    print("-" * 70)
    safe_index = secure_ingest(POISONED_DOC)
    hijacked_safe = []
    for q in test_queries:
        top = keyword_search(q, safe_index, top_k=1)[0]
        print(f"질의 {q!r} → top-1: [{top.doc_id}]")
        if top.doc_id == POISONED_DOC.doc_id:
            hijacked_safe.append(q)
    safe = Verdict(
        text=f"poisoned 문서가 top-1을 차지한 질의: {hijacked_safe}",
        leaked=bool(hijacked_safe),
        leaked_items=hijacked_safe,
        reason="probe 질의 커버리지가 임계치를 넘어 quarantine(색인 제외)",
    )
    print(f"\n사유: {safe.reason}")
    print(f"판정: 검색 결과 오염 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 poisoned 문서의 검색 결과 장악이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 quarantine으로 검색 결과 오염이 없어야 한다"
    print("PASS: 취약 경로는 poisoned 문서가 모든 질의의 top-1을 장악, 보안 경로는 인제스트 시점에 격리해 차단함을 확인.")


if __name__ == "__main__":
    main()
