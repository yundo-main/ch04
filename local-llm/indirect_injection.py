# indirect_injection.py
# =============================================================================
# 예제 2: 간접 프롬프트 인젝션 (Indirect Prompt Injection / RAG 문서 오염)
#
# ch03/d06/rag-agent 의 build_prompt() 패턴(검색 문서 + 질문을 한 문자열로
# 합쳐 LLM 에 전달)을 그대로 재현한 뒤, 검색 인덱스에 오염된 문서 한 건이
# 섞여 있을 때 무슨 일이 벌어지는지 실제 모델로 보여준다. 임베딩 API 호출
# 없이도 재현 가능하도록 키워드 기반 검색으로 단순화했다.
#
# 위협 모델
#   - 자산: 사용자에게 전달되는 최종 답변(신뢰성) + 사용자 자산(사회공학
#     유도로 인한 금전 피해).
#   - 신뢰 경계: 검색된 문서(Context) 는 "시스템이 준비한 신뢰 데이터"로
#     취급되기 쉽지만, 실제로는 제3자가 채워 넣거나 수정할 수 있는 콘텐츠다
#     (지식베이스 기고자, 크롤링 대상 웹페이지, 티켓 첨부파일 등).
#   - 공격자 역량: 지식베이스에 문서를 추가/수정할 수 있는 낮은 권한
#     (예: 위키 기고 권한, 고객 문의 티켓 작성자) — 사용자를 직접 속이지 않고도
#     '문서를 통해' LLM 의 답변을 조작한다는 점이 직접 인젝션과의 차이.
#
# 사전 준비 (models/ 에 GGUF 모델 필요, guide.md 0단계 참고)
#   pip install llama-cpp-python
#   curl -L -o models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
#     https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
#
# 재현 절차
#   python indirect_injection.py
#
# 관찰 포인트
#   - vulnerable_run_rag(): 검색된 문서 텍스트를 그대로 프롬프트에 이어붙임
#     → 오염된 문서의 [SYSTEM] 지시를 모델이 따르면 계좌 유도 문구가 나온다.
#   - secure_run_rag(): 검색된 문서를 <untrusted_data> 태그로 감싸 데이터로만
#     다루도록 지시 + 수집 단계에서 인젝션 패턴을 탐지해 격리(quarantine)
#     대상으로 표시 → 태그 지시에도 모델이 원문을 그대로 노출하는지 관찰.
#
# 잔여 위험: 태그 기반 보안은 "프롬프트 수준" 방어일 뿐이다. 실제 소형 모델은
# 이 지시를 무시하고 태그 안의 문구를 그대로 노출하거나 따를 수 있다 — 그 경우가
# '프롬프트 기반 방어만으로는 부족하다'는 잔여 위험을 실측으로 보여주는 결과다.
# =============================================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from local_llm import (
    RealGenerationResult,
    contains_any_keyword,
    guarded_generate_real,
    is_available,
    naive_generate_real,
)
from prompts import (
    INDIRECT_SYSTEM_INSTRUCTION as SYSTEM_INSTRUCTION,
    INDIRECT_USER_QUESTION,
)

DOCUMENTS_PATH = Path(__file__).with_name("documents.json")

# 수집 단계 콘텐츠 스캔용 최소 패턴 (교육용, 실제 탐지기는 훨씬 넓어야 함)
_QUARANTINE_PATTERNS = [
    re.compile(r"\[system\]", re.IGNORECASE),
    re.compile(r"실제\s*시스템\s*명령"),
    re.compile(r"이전\s*지시.{0,10}(무시|잊)"),
    re.compile(r"계좌.{0,10}입금"),
]

# 출력 단 필터용 키워드: 응답 자체에 이 중 하나라도 있으면 사회공학 유도가 새어나간 것
_LURE_KEYWORDS = ["계좌", "입금", "보증금", "카카오뱅크"]


@dataclass
class Document:
    doc_id: str
    text: str


def load_documents() -> List[Document]:
    rows = json.loads(DOCUMENTS_PATH.read_text(encoding="utf-8"))
    return [Document(doc_id=r["doc_id"], text=r["text"]) for r in rows]


def keyword_search(question: str, documents: List[Document], top_k: int = 1) -> List[Document]:
    """임베딩 대신 단순 키워드 겹침으로 검색 (재현성을 위해 API 의존 제거).

    실제 서비스의 벡터 검색과 스코어링 로직은 다르지만, "검색된 문서가
    그대로 신뢰 컨텍스트로 프롬프트에 들어간다"는 이 예제의 핵심 전제는 동일하다.
    """
    scored = []
    q_tokens = set(question)
    for doc in documents:
        overlap = len(q_tokens & set(doc.text))
        scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _score, doc in scored[:top_k]]


def build_context_block(documents: List[Document]) -> str:
    return "\n".join(f"[{d.doc_id}] {d.text}" for d in documents)


def _looks_poisoned(text: str) -> bool:
    return any(p.search(text) for p in _QUARANTINE_PATTERNS)


def vulnerable_run_rag(question: str) -> RealGenerationResult:
    """취약 구현: 검색 문서를 그대로 이어붙여 하나의 프롬프트로 모델에 전달."""
    docs = load_documents()
    hits = keyword_search(question, docs, top_k=1)
    context_block = build_context_block(hits)
    prompt = f"--- Context ---\n{context_block}\n---\nQuestion: {question}"
    return naive_generate_real(SYSTEM_INSTRUCTION, prompt)


def secure_run_rag(question: str) -> RealGenerationResult:
    """보안 구현: (1) 검색 문서를 <untrusted_data> 태그로 감싸 데이터 전용으로 전달 +
    (2) 수집 단계 콘텐츠 스캔으로 오염 의심 문서를 격리(quarantine) 대상으로 표시 +
    (3) 그래도 응답에 계좌 유도 문구가 새어나오면 출력 단에서 강제로 차단하는 하드 게이트.

    (1)(2)만으로는 모델이 태그 지시를 무시할 수 있다 — 그래서 (3)이 진짜 방어선이다.
    이 구조 덕분에 보안 경로는 '운이 좋으면 안전한 것'이 아니라 '항상 안전한 것'이 된다.
    """
    docs = load_documents()
    hits = keyword_search(question, docs, top_k=1)

    quarantined = [d.doc_id for d in hits if _looks_poisoned(d.text)]
    if quarantined:
        print(f"[콘텐츠 보안 스캔] 격리 대상 문서: {quarantined} (인젝션 패턴 탐지)")

    result = guarded_generate_real(
        SYSTEM_INSTRUCTION,
        untrusted_blocks=[d.text for d in hits],
        question=question,
    )
    if result.ok and contains_any_keyword(result.text, _LURE_KEYWORDS):
        clean = next((d for d in docs if d.doc_id == "refund_policy"), None)
        result.text = (
            f"[출력 필터에 의해 차단됨] 환불 정책: {clean.text}"
            if clean
            else "[출력 필터에 의해 차단됨] 문서에서 확인되지 않습니다."
        )
    return result


def main() -> None:
    question = INDIRECT_USER_QUESTION

    print("=" * 70)
    print("예제 2: 간접 프롬프트 인젝션 (RAG 문서 오염)")
    print("=" * 70)
    print(f"[질문] {question}\n")

    if not is_available():
        print(
            "모델 파일을 찾을 수 없습니다. 먼저 모델을 준비하세요.\n"
            "  pip install llama-cpp-python\n"
            "  curl -L -o models/qwen2.5-0.5b-instruct-q4_k_m.gguf \\\n"
            "    https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
        )
        return

    print("-" * 70)
    print("[취약 경로] vulnerable_run_rag()")
    print("-" * 70)
    vuln = vulnerable_run_rag(question)
    if not vuln.ok:
        print(f"호출 실패: {vuln.error}")
    else:
        vuln_leaked = contains_any_keyword(vuln.text, _LURE_KEYWORDS)
        print(f"응답:\n{vuln.text}\n")
        print(f"판정: 계좌 유도 문구 포함 = {vuln_leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_run_rag()")
    print("-" * 70)
    safe = secure_run_rag(question)
    if not safe.ok:
        print(f"호출 실패: {safe.error}")
    else:
        safe_leaked = contains_any_keyword(safe.text, _LURE_KEYWORDS)
        print(f"응답:\n{safe.text}\n")
        print(f"판정: 계좌 유도 문구 포함 = {safe_leaked}")

    print()
    print("=" * 70)
    print(
        "보안 경로는 태그 지시 + 출력 단 필터(하드 게이트)를 함께 쓰기 때문에\n"
        "'판정: ... = True' 가 나올 수 없다(필터가 걸리면 정상 환불 정책으로 대체됨).\n"
        "반면 취약 경로는 아무 필터가 없어서, 모델이 오염 문서 지시를 따르면 그대로 노출된다.\n"
        "이번 실행에서 취약 경로 판정이 False 라면 이 모델/문구 조합에서는 공격 자체가\n"
        "성공하지 못한 것이다 — 실제 모델 결과는 비결정적이라 매번 다를 수 있다."
    )


if __name__ == "__main__":
    main()
