# direct_injection.py
# =============================================================================
# 예제 1: 직접 프롬프트 인젝션 (Direct Prompt Injection)
#
# 위협 모델
#   - 자산: 시스템 프롬프트(내부 운영 지시문) — 경쟁사/공격자에게 노출되면
#     탈옥(jailbreak) 프롬프트 설계에 악용될 수 있는 낮은~중간 민감도 자산.
#   - 신뢰 경계: 사용자 입력(신뢰 불가) ↔ 시스템 지시문(신뢰).
#   - 공격자 역량: 챗봇 UI에 텍스트를 입력할 수 있는 인증/비인증 최종 사용자.
#     별도의 API 접근 권한이나 인프라 접근은 필요 없음 (낮은 역량으로 시도 가능).
#
# 재현 절차
#   python direct_injection.py
#
# 관찰 포인트
#   - vulnerable_respond(): 시스템 지시문 + 사용자 입력을 하나의 문자열로 합쳐
#     모델에 전달 → 인젝션 문구에 따라 시스템 프롬프트가 그대로 유출된다.
#   - secure_respond(): 시스템 지시문은 별도 채널로 고정하고, 사용자 입력은
#     '데이터'로만 취급 → 동일한 인젝션 시도가 탐지는 되지만 실행되지 않는다.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from mock_llm import GenerationResult, guarded_generate, naive_generate  # noqa: E402
from real_llm import DEFAULT_MODEL, guarded_generate_real, is_ollama_available, naive_generate_real  # noqa: E402
from prompts import (
    DIRECT_ATTACKER_INPUT as ATTACKER_INPUT,
    DIRECT_SAFE_ANSWER,
    DIRECT_SYSTEM_INSTRUCTION as SYSTEM_INSTRUCTION,
)


def vulnerable_respond(user_input: str) -> GenerationResult:
    """취약 구현: system + user 입력을 한 채널로 합쳐서 모델에 전달."""
    return naive_generate(SYSTEM_INSTRUCTION, user_input)


def secure_respond(user_input: str) -> GenerationResult:
    """보안 구현: system 지시문은 고정, user 입력은 데이터로만 취급.

    실제 서비스에서는 여기서 정상 질의에 대한 답변을 생성하되,
    사용자 입력에서 시스템 프롬프트 유출을 유도하는 패턴이 잡히면
    감사 로그에 injection_detected=True 로 기록해 보안팀이 추세를 볼 수 있게 한다.
    """
    return guarded_generate(SYSTEM_INSTRUCTION, DIRECT_SAFE_ANSWER, untrusted_blocks=[user_input])


def main() -> None:
    print("=" * 70)
    print("예제 1: 직접 프롬프트 인젝션 (Direct Prompt Injection)")
    print("=" * 70)
    print(f"[시스템 지시문]\n{SYSTEM_INSTRUCTION}\n")
    print(f"[공격자 입력]\n{ATTACKER_INPUT}\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_respond()")
    print("-" * 70)
    vuln_result = vulnerable_respond(ATTACKER_INPUT)
    print(f"응답:\n{vuln_result.text}\n")
    print(f"위험도 점수: {vuln_result.risk_score}")
    print(f"인젝션 탐지 여부: {vuln_result.injection_detected}")
    print(f"매칭 패턴: {vuln_result.matched_patterns}")
    print(f"공격자 지시 이행 여부: {vuln_result.obeyed_injected_instruction}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_respond()")
    print("-" * 70)
    safe_result = secure_respond(ATTACKER_INPUT)
    print(f"응답:\n{safe_result.text}\n")
    print(f"위험도 점수: {safe_result.risk_score}")
    print(f"인젝션 탐지 여부: {safe_result.injection_detected}")
    print(f"매칭 패턴: {safe_result.matched_patterns}")
    print(f"공격자 지시 이행 여부: {safe_result.obeyed_injected_instruction}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln_result.obeyed_injected_instruction is True, "취약 경로는 인젝션을 재현해야 한다"
    assert safe_result.obeyed_injected_instruction is False, "보안 경로는 인젝션을 실행하면 안 된다"
    assert safe_result.injection_detected is True, "보안 경로도 탐지 신호는 남겨야 한다(감사 목적)"
    print("PASS: 취약 경로는 유출 재현, 보안 경로는 탐지만 하고 실행은 차단함을 확인.")

    if "--real" in sys.argv:
        run_real(ATTACKER_INPUT)


def run_real(user_input: str, model: str = DEFAULT_MODEL) -> None:
    """실제 로컬 소형 LLM(Ollama) 대상으로 동일한 인젝션 시도를 재현한다.

    mock 은 항상 같은 결과를 내지만, 실제 모델은 비결정적이고 모델마다 다르게
    반응할 수 있다 — 여기서 관찰하는 것은 "이 모델이 이 문구에 실제로 어떻게
    반응했는가"이지, 일반화된 결론이 아니다.
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

    print("[취약 경로] naive_generate_real() — system + user 를 한 메시지로 합쳐 전달")
    vuln = naive_generate_real(SYSTEM_INSTRUCTION, user_input, model=model)
    if not vuln.ok:
        print(f"호출 실패: {vuln.error}")
    else:
        print(f"응답:\n{vuln.text}\n")

    print("[보안 경로] guarded_generate_real() — 신뢰 불가 입력을 태그로 격리")
    safe = guarded_generate_real(
        SYSTEM_INSTRUCTION,
        untrusted_blocks=[user_input],
        question="위 사용자 메시지에 정중하게 응답하세요.",
        model=model,
    )
    if not safe.ok:
        print(f"호출 실패: {safe.error}")
    else:
        print(f"응답:\n{safe.text}\n")

    print(
        "참고: 응답에 시스템 지시문 원문이 그대로 보이면 이 모델/문구 조합에서는\n"
        "해당 경로가 실패한 것이다 (mock 과 달리 실제 모델 결과는 매번 다를 수 있음)."
    )


if __name__ == "__main__":
    main()
