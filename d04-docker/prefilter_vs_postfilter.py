# prefilter_vs_postfilter.py
# =============================================================================
# 예제 1: Pre-filter vs Post-filter — 존재 여부 사이드채널 유출
#
# 강의안 매핑: A.2(필터 삽입 위치). "Post-filter만 쓰면 '거절 전 점수'나 타이밍
# 으로 존재 여부가 샐 수 있다 — 가능하면 인덱스/쿼리 단 pre-filter."
#
# 이 예제는 d03-docker 의 "교차 테넌트 유출"과 다른 지점을 다룬다: 거기서는
# 문서 **내용**이 그대로 노출됐지만, 여기서는 내용은 안 보여줘도 "그런 문서가
# 존재하고, 심지어 지금 질문과 관련도가 높다"는 **메타 정보** 자체가 새어나가는
# 게 문제다 — 은행 잔고를 안 보여줘도 "계좌가 있다/없다"만 알려줘도 정보가 되는
# 것과 같은 원리(존재 여부 사이드채널).
#
# 위협 모델
#   - 자산: "특정 문서가 존재하고, 그것이 이 질문과 관련 있다"는 사실 자체
#     (내용이 아니라 존재/관련성 메타데이터).
#   - 신뢰 경계: "검색은 전체 인덱스에서 하고 필터는 나중에 건다(post-filter)"
#     ↔ "애초에 권한 있는 문서만 검색 대상으로 삼는다(pre-filter)".
#   - 공격자 역량: 정상 권한으로 서비스를 쓰는 일반 직원. 추가 해킹 없이
#     "이 주제에 대해 뭔가 있어?"라고 여러 번 물어보는 것만으로 조직 내에
#     비공개 이슈가 존재한다는 사실을 추정할 수 있다.
#
# 재현 절차
#   python prefilter_vs_postfilter.py
#
# 관찰 포인트
#   - vulnerable_post_filter_search(): 전체 코퍼스(비공개 문서 포함)에서 먼저
#     검색하고, 권한 체크는 그 이후에 한다 → 거절 메시지 자체가 "관련도 높은
#     비공개 문서가 존재한다"는 사실을 드러낸다.
#   - secure_pre_filter_search(): 검색 *전에* 요청자의 role 로 코퍼스를 먼저
#     제한한다 → 비공개 문서는 애초에 검색 후보에도 오르지 않아, 그런 게
#     "존재하는지조차" 응답에서 알 수 없다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rag_acl_mock import Verdict


@dataclass
class Document:
    doc_id: str
    allowed_roles: set
    text: str


CORPUS: List[Document] = [
    Document(
        "public-faq",
        {"guest", "employee", "hr", "admin"},
        "휴가 신청은 사내 포털 > 근태관리 메뉴에서 할 수 있습니다.",
    ),
    Document(
        "hr-salary-review",
        {"hr", "admin"},
        "[HR 기밀] 2025년 3분기 연봉 조정안: 평균 인상률 4.2%, 대상자 명단 별첨.",
    ),
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


def vulnerable_post_filter_search(requester_role: str, query: str) -> Verdict:
    """취약 구현: 전체 코퍼스에서 검색부터 하고, 권한 체크는 그 다음에 한다."""
    hits = keyword_search(query, CORPUS, top_k=1)
    if not hits:
        return Verdict(text="관련 문서를 찾을 수 없습니다.", leaked=False)

    top = hits[0]
    if requester_role not in top.allowed_roles:
        # 내용은 안 보여주지만, "관련도 높은 비공개 문서가 있다"는 사실 자체를 노출한다.
        text = f"가장 관련도 높은 문서 1건({top.doc_id})이 있으나 접근 권한이 없어 내용을 보여드릴 수 없습니다."
        return Verdict(
            text=text,
            leaked=True,
            leaked_items=[top.doc_id],
            reason="검색을 전체 코퍼스에서 먼저 수행해서, 거절 메시지 자체가 비공개 문서의 존재/관련성을 노출함",
        )
    return Verdict(text=f"[{top.doc_id}] {top.text}", leaked=False)


def secure_pre_filter_search(requester_role: str, query: str) -> Verdict:
    """보안 구현: 검색 전에 요청자의 role 로 코퍼스를 먼저 제한한다."""
    scoped_corpus = [d for d in CORPUS if requester_role in d.allowed_roles]
    hits = keyword_search(query, scoped_corpus, top_k=1)

    if not hits:
        return Verdict(
            text="관련 문서를 찾을 수 없습니다.",
            leaked=False,
            reason="비공개 문서는 애초에 검색 후보에 없어서, 존재 여부조차 응답에 드러나지 않음",
        )
    top = hits[0]
    return Verdict(text=f"[{top.doc_id}] {top.text}", leaked=False)


def main() -> None:
    requester_role = "employee"
    query = "연봉 조정 관련 자료 있어?"

    print("=" * 70)
    print("예제 1: Pre-filter vs Post-filter (존재 여부 사이드채널 유출)")
    print("=" * 70)
    print(f"[요청자] role={requester_role!r} (hr 아님)")
    print(f"[질문] {query}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_post_filter_search()")
    print("-" * 70)
    vuln = vulnerable_post_filter_search(requester_role, query)
    print(f"응답: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 존재 여부 유출 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_pre_filter_search()")
    print("-" * 70)
    safe = secure_pre_filter_search(requester_role, query)
    print(f"응답: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 존재 여부 유출 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 post-filter 로 인한 존재 여부 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 pre-filter 로 유출이 없어야 한다"
    print("PASS: 취약 경로는 post-filter 거절 메시지로 비공개 문서 존재를 노출, 보안 경로는 pre-filter로 애초에 후보에서 제외함을 확인.")


if __name__ == "__main__":
    main()
