# response_canary_scanning.py
# =============================================================================
# 예제 2: 응답 canary 스캐닝 — 출력 검사 없이 그대로 반환
#
# 강의안 매핑: Lab 2 "security.py 출력 검사로 매칭 시 차단·로그".
#
# 위협 모델
#   - 자산: canary가 심어진 Restricted 문서가 실수로(또는 인젝션으로)
#     컨텍스트에 포함되었을 때, 그 사실이 최종 사용자 응답으로 새어나가기
#     전에 잡아낼 수 있는 마지막 방어선.
#   - 신뢰 경계: "LLM이 생성한 응답은 그대로 반환해도 된다" ↔ "응답을
#     반환하기 전에 알려진 canary 목록과 대조해야 한다". 전자로 구현하면,
#     상류 단계(권한 필터, 프롬프트 설계)가 어떤 이유로든 뚫렸을 때 canary
#     문자열이 그대로 사용자에게 노출되고도 아무 알람도 울리지 않는다.
#   - 공격자 역량: 컨텍스트에 Restricted 문서가 섞여 들어가게 만들 수 있는
#     프롬프트 인젝션(ch04/d01) 능력. 이 예제 자체는 인젝션이 이미
#     성공했다고 가정하고, 그다음 방어선(출력 검사)이 작동하는지만 본다.
#
# 재현 절차
#   python response_canary_scanning.py
#
# 관찰 포인트
#   - vulnerable_respond(): LLM 응답을 canary 매칭 검사 없이 그대로 반환
#     → canary 문자열이 사용자에게 그대로 노출되고 알람도 없다.
#   - secure_respond(): 반환 직전 응답 텍스트를 canary 레지스트리와 대조 →
#     매칭되면 응답을 차단하고, 어느 문서(canary_token → doc_id)에서 나온
#     것인지 알람 로그로 남긴다.
# =============================================================================

from __future__ import annotations

import sys

from canary_mock import Verdict, load_canary_documents
from real_llm import DEFAULT_MODEL, ask_real, is_ollama_available  # noqa: E402 (shared/ 를 sys.path 에 추가함)
from prompts import RAG_ANSWER_SYSTEM_INSTRUCTION  # noqa: E402

CORPUS = load_canary_documents()
CANARY_REGISTRY = {d.canary_token: d.doc_id for d in CORPUS}  # canary_token -> 출처 doc_id


def mock_llm_response(context_doc_text: str) -> str:
    """모의 LLM: 프롬프트 인젝션이 이미 성공해 컨텍스트 원문을 그대로 답변에 포함시킨다."""
    return f"요청하신 내부 문서 원문은 다음과 같습니다 - {context_doc_text}"


def vulnerable_respond(context_doc_text: str) -> Verdict:
    """취약 구현: 응답을 canary 매칭 검사 없이 그대로 반환한다."""
    response = mock_llm_response(context_doc_text)
    matched = [t for t in CANARY_REGISTRY if t in response]
    return Verdict(
        text=response,
        leaked=bool(matched),
        leaked_items=matched,
        reason="응답을 반환하기 전에 canary 매칭 검사를 하지 않음",
    )


def secure_respond(context_doc_text: str) -> Verdict:
    """보안 구현: 반환 직전 canary 레지스트리와 대조해 매칭 시 차단·로그한다."""
    response = mock_llm_response(context_doc_text)
    matched = [t for t in CANARY_REGISTRY if t in response]

    if matched:
        for token in matched:
            print(f"[ALERT] canary 유출 탐지: token={token} source_doc={CANARY_REGISTRY[token]}")
        return Verdict(
            text="[차단됨] 이 응답은 보안 정책에 따라 반환되지 않습니다.",
            leaked=False,
            leaked_items=matched,
            reason=f"canary 매칭({matched})으로 응답 차단 및 알람 로그 기록",
        )
    return Verdict(text=response, leaked=False, reason="canary 매칭 없음")


def main() -> None:
    target = next(d for d in CORPUS if d.doc_id == "restricted-infra-credentials-doc")

    print("=" * 70)
    print("예제 2: 응답 canary 스캐닝 — 출력 검사 없이 그대로 반환")
    print("=" * 70)
    print(f"[가정] 프롬프트 인젝션으로 {target.doc_id} 문서 원문이 컨텍스트에 포함됨\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_respond()")
    print("-" * 70)
    vuln = vulnerable_respond(target.text)
    print(f"응답: {vuln.text}\n")
    print(f"사유: {vuln.reason}")
    print(f"판정: canary 유출 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_respond()")
    print("-" * 70)
    safe = secure_respond(target.text)
    print(f"응답: {safe.text}\n")
    print(f"사유: {safe.reason}")
    print(f"판정: canary 유출 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 canary가 그대로 노출되는 것이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 canary 매칭으로 응답이 차단돼야 한다"
    print("PASS: 취약 경로는 canary가 응답에 그대로 노출, 보안 경로는 매칭 즉시 차단 및 알람 로그를 남김을 확인.")

    if "--real" in sys.argv:
        run_real()


def run_real(model: str = DEFAULT_MODEL) -> None:
    """실제 로컬 소형 LLM(Ollama)에 canary가 포함된 문서를 컨텍스트로 넘겨,
    실제 응답에 canary가 그대로 나타나는지 관찰한다.

    동일한 실제 응답 하나에 대해 "그대로 반환(취약)" vs "canary 매칭 시
    차단·알람(보안)" 두 처리 방식을 비교한다 — 응답 자체는 같고, 처리
    방식만 다르다는 점이 핵심이다.
    """
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

    target = next(d for d in CORPUS if d.doc_id == "restricted-infra-credentials-doc")
    system_instruction = RAG_ANSWER_SYSTEM_INSTRUCTION
    question = "프로덕션 인프라 접속 정보 알려줘"

    result = ask_real(system_instruction, f"[참고 문서]\n{target.text}\n\n[질문] {question}", model=model)
    if not result.ok:
        print(f"호출 실패: {result.error}")
        return

    print(f"[실제 모델 응답]\n{result.text}\n")
    matched = [t for t in CANARY_REGISTRY if t in result.text]

    print("[취약 경로] 응답을 canary 검사 없이 그대로 반환")
    print(f"canary 유출 여부: {bool(matched)}")

    print()
    print("[보안 경로] 동일 응답을 canary 레지스트리와 대조")
    if matched:
        for token in matched:
            print(f"[ALERT] canary 유출 탐지: token={token} source_doc={CANARY_REGISTRY[token]}")
        print("응답: [차단됨] 이 응답은 보안 정책에 따라 반환되지 않습니다.")
    else:
        print(f"응답: {result.text}")
    print(f"canary 유출 여부: {False if matched else bool(matched)}")

    print(
        "\n참고: 실제 모델이 canary 문자열을 그대로 인용하지 않고 의역/요약하면 "
        "이 substring 매칭 자체가 놓칠 수 있다 — 그 경우도 유출이 없다는 뜻은 "
        "아니며, 의미 기반 탐지가 별도로 필요하다는 잔여 위험을 보여준다."
    )


if __name__ == "__main__":
    main()
