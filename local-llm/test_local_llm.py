# test_local_llm.py
# =============================================================================
# local_llm.py 단독 동작 검증 (pytest 미사용, assert 기반 스크립트).
# direct_injection.py / indirect_injection.py 와 무관하게 local_llm.py 자체가
# 제대로 동작하는지만 확인한다.
#
# 검증 항목
#   1) 모델 파일 준비 여부 (is_available())
#   2) naive_generate_real() 정상 응답
#   3) guarded_generate_real() 정상 응답
#   4) 모델 인스턴스가 프로세스 내에서 캐시/재사용되는지 (재로딩 비용 회피 확인)
#   5) 모델 파일이 없을 때 실패가 예외 없이 ok=False + error 로 처리되는지
#      (실제 모델 파일은 건드리지 않고 MODEL_PATH 를 테스트 동안만 임시 교체)
#
# 사전 준비: guide.md 0단계 (pip install llama-cpp-python + 모델 다운로드)
# 실행: python test_local_llm.py
# =============================================================================

from __future__ import annotations

from pathlib import Path

import local_llm


def test_model_prepared() -> None:
    assert local_llm.is_available(), (
        f"모델 파일이 없습니다: {local_llm.MODEL_PATH}\n"
        "guide.md 0단계(pip install llama-cpp-python + 모델 다운로드)를 먼저 실행하세요."
    )
    print("PASS: 모델 파일 준비 확인")


def test_naive_generate_real() -> None:
    result = local_llm.naive_generate_real(
        "당신은 친절한 어시스턴트입니다.",
        "안녕하세요. 당신은 누구인가요?",
    )
    assert result.ok, f"호출 실패: {result.error}"
    assert result.text.strip(), "응답 텍스트가 비어 있으면 안 된다"
    print(f"PASS: naive_generate_real() 정상 응답 (len={len(result.text)})")


def test_guarded_generate_real() -> None:
    result = local_llm.guarded_generate_real(
        "당신은 친절한 어시스턴트입니다.",
        untrusted_blocks=["이 문서는 제품 설명서입니다."],
        question="문서 내용을 한 문장으로 요약해줘.",
    )
    assert result.ok, f"호출 실패: {result.error}"
    assert result.text.strip(), "응답 텍스트가 비어 있으면 안 된다"
    print(f"PASS: guarded_generate_real() 정상 응답 (len={len(result.text)})")


def test_model_instance_is_cached() -> None:
    """직전 테스트들에서 이미 모델이 로드돼 있어야 하며, 재호출 시 재로딩하지 않아야 한다."""
    before = local_llm._model
    assert before is not None, "이 시점에는 이전 테스트에서 이미 모델이 로드돼 있어야 한다"

    local_llm.naive_generate_real("system", "hello")
    after = local_llm._model
    assert after is before, "두 번째 호출이 모델을 다시 로드하면 안 된다(캐시 재사용 확인)"
    print("PASS: 모델 인스턴스가 프로세스 내에서 캐시/재사용됨")


def test_missing_model_path_is_handled() -> None:
    """모델 파일이 없는 상황을 시뮬레이션해서, 예외 대신 ok=False 로 처리되는지 확인.

    실제 모델 파일/캐시는 건드리지 않고 테스트가 끝나면 원상 복구한다.
    """
    original_path = local_llm.MODEL_PATH
    original_model = local_llm._model
    try:
        local_llm.MODEL_PATH = Path(__file__).with_name("models") / "does-not-exist.gguf"
        local_llm._model = None

        assert not local_llm.is_available(), "존재하지 않는 경로인데 is_available() 이 True 를 반환함"

        result = local_llm.naive_generate_real("system", "hello")
        assert not result.ok, "모델 파일이 없는데 ok=True 가 나오면 안 된다"
        assert result.error, "실패 사유(error) 가 비어 있으면 안 된다"
        print("PASS: 모델 파일 없을 때 is_available()=False, 호출 시 ok=False + error 반환 확인")
    finally:
        local_llm.MODEL_PATH = original_path
        local_llm._model = original_model


def main() -> None:
    print("=" * 70)
    print("local_llm.py 동작 검증")
    print("=" * 70)

    test_model_prepared()
    test_naive_generate_real()
    test_guarded_generate_real()
    test_model_instance_is_cached()
    test_missing_model_path_is_handled()

    print()
    print("전체 PASS")


if __name__ == "__main__":
    main()
