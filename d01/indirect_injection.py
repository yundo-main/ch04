# indirect_injection.py
# =============================================================================
# 예제 2: 간접 프롬프트 인젝션 (Indirect Prompt Injection / RAG 문서 오염)
#
# ch03/d06/rag-agent 의 build_prompt() 패턴(검색 문서 + 질문을 한 문자열로
# 합쳐 LLM 에 전달)을 그대로 재현한 뒤, 검색 인덱스에 오염된 문서 한 건이
# 섞여 있을 때 무슨 일이 벌어지는지 보여준다. 임베딩 API 호출 없이도
# 재현 가능하도록 키워드 기반 검색으로 단순화했다.
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
# 재현 절차
#   python indirect_injection.py
#
# 관찰 포인트
#   - vulnerable_run_rag(): 검색된 문서 텍스트를 그대로 프롬프트에 이어붙임
#     → 오염된 문서의 [SYSTEM] 지시가 실행되어 계좌 유도 문구가 출력된다.
#   - secure_run_rag(): 검색된 문서를 '데이터'로만 다루고, 수집 단계에서
#     인젝션 패턴을 탐지해 격리(quarantine) 대상으로 표시한다
#     → 오염 문서가 검색되어도 지시가 실행되지 않고, 정상 환불 정책만 답한다.
# =============================================================================

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from mock_llm import GenerationResult, guarded_generate, naive_generate  # noqa: E402
from real_llm import DEFAULT_MODEL, guarded_generate_real, is_ollama_available, naive_generate_real  # noqa: E402
from prompts import (
    INDIRECT_SYSTEM_INSTRUCTION as SYSTEM_INSTRUCTION,
    INDIRECT_USER_QUESTION,
)

DOCUMENTS_PATH = Path(__file__).with_name("documents.json")


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


def vulnerable_run_rag(question: str) -> GenerationResult:
    """취약 구현: 검색 문서를 그대로 이어붙여 하나의 프롬프트로 모델에 전달."""
    docs = load_documents()
    hits = keyword_search(question, docs, top_k=1)
    context_block = build_context_block(hits)
    prompt = f"--- Context ---\n{context_block}\n---\nQuestion: {question}"
    return naive_generate(SYSTEM_INSTRUCTION, prompt)


def secure_run_rag(question: str) -> GenerationResult:
    """보안 구현: 검색 문서를 데이터 전용 채널로 분리 + 수집 단계 콘텐츠 검사.

    - 각 문서는 untrusted_blocks 로 별도 전달되어, 그 안의 지시문이 있어도
      실행되지 않는다.
    - 콘텐츠 보안 스캔에서 인젝션 패턴이 잡힌 문서는 quarantined 목록에 올려
      운영자가 검수/삭제하도록 신호를 남긴다 (MLSecOps 데이터 거버넌스 통제).
    """
    docs = load_documents()
    hits = keyword_search(question, docs, top_k=1)

    safe_answer = _lookup_known_answer(question, docs)
    result = guarded_generate(
        SYSTEM_INSTRUCTION,
        safe_answer,
        untrusted_blocks=[d.text for d in hits],
    )

    quarantined = [d.doc_id for d in hits if _looks_poisoned(d.text)]
    if quarantined:
        print(f"[콘텐츠 보안 스캔] 격리 대상 문서: {quarantined} (인젝션 패턴 탐지)")

    return result


def _looks_poisoned(text: str) -> bool:
    from mock_llm import _find_injection_matches  # 내부 헬퍼 재사용

    return bool(_find_injection_matches(text))


def _lookup_known_answer(question: str, docs: List[Document]) -> str:
    """보안 경로에서 실제로 반환할 정답: 오염되지 않은 정책 원문 기준으로 답한다.

    실제 서비스에서는 이 부분이 '오염되지 않은 것으로 검증된 문서'만 근거로
    삼는 LLM 호출이 되어야 한다. 이 예제는 재현성을 위해 고정 응답으로 대체.
    """
    clean = next((d for d in docs if d.doc_id == "refund_policy"), None)
    if clean is None:
        return "문서에서 확인되지 않습니다."
    return f"환불 정책: {clean.text}"


def main() -> None:
    question = INDIRECT_USER_QUESTION

    print("=" * 70)
    print("예제 2: 간접 프롬프트 인젝션 (RAG 문서 오염)")
    print("=" * 70)
    print(f"[질문] {question}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_run_rag()")
    print("-" * 70)
    vuln_result = vulnerable_run_rag(question)
    print(f"응답:\n{vuln_result.text}\n")
    print(f"위험도 점수: {vuln_result.risk_score}")
    print(f"인젝션 탐지 여부: {vuln_result.injection_detected}")
    print(f"공격자 지시 이행 여부: {vuln_result.obeyed_injected_instruction}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_run_rag()")
    print("-" * 70)
    safe_result = secure_run_rag(question)
    print(f"응답:\n{safe_result.text}\n")
    print(f"위험도 점수: {safe_result.risk_score}")
    print(f"인젝션 탐지 여부: {safe_result.injection_detected}")
    print(f"공격자 지시 이행 여부: {safe_result.obeyed_injected_instruction}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert "계좌" in vuln_result.text, "취약 경로는 오염 문서의 계좌 유도 문구를 반영해야 한다"
    assert vuln_result.obeyed_injected_instruction is True
    assert "계좌" not in safe_result.text, "보안 경로는 계좌 유도 문구를 반환하면 안 된다"
    assert safe_result.obeyed_injected_instruction is False
    print("PASS: 취약 경로는 사회공학 유도 문구 노출, 보안 경로는 정상 환불 정책만 반환함을 확인.")

    if "--real" in sys.argv:
        run_real(question)


def run_real(question: str, model: str = DEFAULT_MODEL) -> None:
    """실제 로컬 소형 LLM(Ollama) 대상으로 동일한 RAG 문서 오염 시나리오를 재현한다."""
    print()
    print("=" * 70)
    print(f"[실제 모델] Ollama ({model}) 대상 재현")
    print("=" * 70)

    if not is_ollama_available():
        print(
            "Ollama 데몬에 연결할 수 없습니다 (http://localhost:11434).\n"
            "  brew install ollama && ollama serve\n"
            f"  ollama pull {model}\n"
            "실행 후 다시 시도하세요."
        )
        return

    docs = load_documents()
    hits = keyword_search(question, docs, top_k=1)
    context_block = build_context_block(hits)

    print("[취약 경로] naive_generate_real() — Context + Question 을 한 메시지로 합쳐 전달")
    vuln_prompt = f"--- Context ---\n{context_block}\n---\nQuestion: {question}"
    vuln = naive_generate_real(SYSTEM_INSTRUCTION, vuln_prompt, model=model)
    if not vuln.ok:
        print(f"호출 실패: {vuln.error}")
    else:
        print(f"응답:\n{vuln.text}\n")

    print("[보안 경로] guarded_generate_real() — 검색 문서를 태그로 격리")
    safe = guarded_generate_real(
        SYSTEM_INSTRUCTION,
        untrusted_blocks=[d.text for d in hits],
        question=question,
        model=model,
    )
    if not safe.ok:
        print(f"호출 실패: {safe.error}")
    else:
        print(f"응답:\n{safe.text}\n")

    print(
        "참고: 응답에 계좌/입금 유도 문구가 남아 있으면 이 모델/문구 조합에서는\n"
        "태그 기반 보안이 실패한 것이다 — 프롬프트 수준 방어의 한계를 실제로 보여주는 결과."
    )


if __name__ == "__main__":
    main()
