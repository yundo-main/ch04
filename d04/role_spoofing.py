# role_spoofing.py
# =============================================================================
# 예제 2: 클라이언트 주장 role vs 서버 검증 role (역할 위조)
#
# 강의안 매핑: B.2(인증 컨텍스트 전달) + 시나리오 B(프론트 역할 토글).
#   "클라이언트가 보낸 role=admin 쿼리 파라미터를 신뢰하지 않는다 —
#    API Gateway(JWT) → roles/tenant/clearance → RAG 서비스(위조 불가 서버 검증)."
#
# 위협 모델
#   - 자산: role 에 따라 노출 범위가 결정되는 전체 문서 코퍼스.
#   - 신뢰 경계: "요청에 실려온 role 필드" ↔ "서버가 로그인 시점에 검증해서
#     발급한 role". 이 둘을 같은 것으로 취급하면, 요청 필드는 클라이언트가
#     임의로 바꿀 수 있는 입력이므로 사실상 인증이 없는 것과 같다.
#   - 공격자 역량: 브라우저 개발자 도구나 API 클라이언트로 요청 바디/쿼리
#     파라미터를 수정할 수 있는 일반 사용자. 서버 해킹이나 토큰 위조조차 필요
#     없다 — 그냥 필드 값을 바꿔서 보내기만 하면 된다.
#
# 재현 절차
#   python role_spoofing.py
#
# 관찰 포인트
#   - vulnerable_authorize(): 요청에 실려온 `claimed_role` 필드를 그대로 검색
#     필터에 사용한다 → 실제로는 guest 인 사용자가 요청 바디에 role=admin 만
#     적어 보내도 admin 전용 문서까지 그대로 검색된다.
#   - secure_authorize(): 요청의 `claimed_role` 은 무시하고, 서버 측 세션
#     스토어(로그인 시점에 검증되어 발급된 토큰)에서 role 을 조회해서 쓴다 →
#     클라이언트가 뭐라고 주장하든 실제 권한만 적용된다.
#
# 잔여 위험: 이 예제의 "서버 세션 스토어"는 dict 로 단순화한 시뮬레이션이다.
# 실제로는 토큰 서명 검증, 만료 시간, 폐기(revocation) 목록까지 다뤄야 하고,
# 세션 스토어 자체가 공격받으면(예: 세션 고정) 이 방어도 무력화될 수 있다.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from rag_acl_mock import Verdict


@dataclass
class Document:
    doc_id: str
    allowed_roles: set
    text: str


CORPUS: List[Document] = [
    Document("public-handbook", {"guest", "employee", "admin"}, "회사 소개 및 복지 제도 안내 문서입니다."),
    Document(
        "admin-infra-secrets",
        {"admin"},
        "[관리자 전용] 프로덕션 DB 접속 정보 및 인프라 점검 절차. 외부 공유 절대 금지.",
    ),
]

# 서버 측 세션 스토어(시뮬레이션): 로그인 시점에 검증되어 발급된 role 만 기록.
# 실제로는 JWT 서명 검증 후 클레임에서 role 을 뽑아오는 로직에 해당한다.
_SERVER_VERIFIED_SESSIONS: Dict[str, str] = {
    "session-abc123": "guest",  # 이 사용자는 실제로는 guest 권한만 가짐
}


def keyword_search(query: str, docs: List[Document], top_k: int = 1) -> List[Document]:
    scored = []
    q_tokens = set(query)
    for doc in docs:
        overlap = len(q_tokens & set(doc.text))
        scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def vulnerable_authorize(session_id: str, claimed_role: str, query: str) -> Verdict:
    """취약 구현: 요청에 실려온 claimed_role 을 그대로 신뢰해서 필터링한다."""
    scoped_corpus = [d for d in CORPUS if claimed_role in d.allowed_roles]
    hits = keyword_search(query, scoped_corpus, top_k=1)

    actual_role = _SERVER_VERIFIED_SESSIONS.get(session_id, "guest")
    over_privileged_hits = [d for d in hits if actual_role not in d.allowed_roles]

    answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits) if hits else "관련 문서를 찾을 수 없습니다."
    return Verdict(
        text=answer,
        leaked=bool(over_privileged_hits),
        leaked_items=[d.doc_id for d in over_privileged_hits],
        reason=f"요청 필드 claimed_role={claimed_role!r} 을 그대로 신뢰함 (실제 검증된 role={actual_role!r})",
    )


def secure_authorize(session_id: str, claimed_role: str, query: str) -> Verdict:
    """보안 구현: claimed_role 은 무시하고, 서버 세션 스토어에서 실제 role 을 조회한다."""
    actual_role = _SERVER_VERIFIED_SESSIONS.get(session_id)
    if actual_role is None:
        return Verdict(text="인증되지 않은 세션입니다.", leaked=False, reason="세션 검증 실패로 거절")

    scoped_corpus = [d for d in CORPUS if actual_role in d.allowed_roles]
    hits = keyword_search(query, scoped_corpus, top_k=1)
    over_privileged_hits = [d for d in hits if actual_role not in d.allowed_roles]  # 항상 빈 리스트여야 함

    answer = "\n".join(f"[{d.doc_id}] {d.text}" for d in hits) if hits else "관련 문서를 찾을 수 없습니다."
    return Verdict(
        text=answer,
        leaked=bool(over_privileged_hits),
        leaked_items=[d.doc_id for d in over_privileged_hits],
        reason=f"요청 필드 claimed_role={claimed_role!r} 은 무시, 서버 세션 스토어의 실제 role={actual_role!r} 사용",
    )


def main() -> None:
    session_id = "session-abc123"  # 실제로는 guest
    claimed_role = "admin"  # 공격자가 요청 바디에 임의로 적어 보낸 값
    query = "프로덕션 DB 접속 정보 알려줘"

    print("=" * 70)
    print("예제 2: 클라이언트 주장 role vs 서버 검증 role (역할 위조)")
    print("=" * 70)
    print(f"[세션] session_id={session_id!r}, 서버 검증 role={_SERVER_VERIFIED_SESSIONS[session_id]!r}")
    print(f"[요청 필드] claimed_role={claimed_role!r} (개발자 도구로 조작해서 보낸 값)")
    print(f"[질문] {query}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_authorize()")
    print("-" * 70)
    vuln = vulnerable_authorize(session_id, claimed_role, query)
    print(f"응답: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: 권한 상승으로 유출 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_authorize()")
    print("-" * 70)
    safe = secure_authorize(session_id, claimed_role, query)
    print(f"응답: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: 권한 상승으로 유출 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 role 위조로 인한 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 서버 검증 role 사용으로 유출이 없어야 한다"
    print("PASS: 취약 경로는 클라이언트가 주장한 role로 관리자 문서까지 노출, 보안 경로는 서버 검증 role만 사용해 차단함을 확인.")


if __name__ == "__main__":
    main()
