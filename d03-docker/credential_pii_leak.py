# credential_pii_leak.py
# =============================================================================
# 예제 1: 자격증명/PII 유출 (Context Redaction 미적용)
#
# 강의안 매핑: 시나리오 A("코드 리뷰 좀") — 소스+시크릿이 공개 LLM 에 그대로
# 붙여넣어지고, 그게 벤더 API 호출과 로그에 그대로 남는 경로.
#   경로: P1(프롬프트→벤더 API), P5(로그/SIEM 적재)
#
# 위협 모델
#   - 자산: API 키/토큰(자격증명), 이메일(PII).
#   - 신뢰 경계: 사용자가 붙여넣는 원문 ↔ 실제로 외부(LLM 벤더, 로그 시스템)로
#     나가도 되는 내용. 이 둘을 구분하지 않으면 붙여넣은 그대로 다 나간다.
#   - 공격자 역량: 이건 "공격"이 아니라 "실수"에 가깝다 — 악의 없는 사용자가
#     디버깅 목적으로 코드를 그대로 붙여넣는 정상적인 업무 흐름에서 발생한다.
#     (강의안 A.2: "유출 ≠ 해킹만")
#
# 재현 절차
#   python credential_pii_leak.py
#
# 관찰 포인트
#   - vulnerable_send_to_vendor(): 사용자가 붙여넣은 원문을 마스킹 없이 그대로
#     "벤더 API 호출 로그"와 "SIEM 로그"에 남긴다 → 자격증명/이메일이 그대로 유출.
#   - secure_send_to_vendor(): 벤더로 보내기 *전에* Context Redaction(정규식
#     기반 마스킹)을 적용 → 로그/벤더 호출 어디에도 원본 값이 남지 않는다.
#
# 잔여 위험: 정규식 기반 탐지는 형식이 정해진 자격증명(API 키 패턴, 이메일)만
# 잡는다. 형식이 없는 비밀(사내 은어로 된 코드네임, 평문 비밀번호 등)이나 새로운
# 발급 형식은 놓칠 수 있다 — 실서비스에서는 벤더별 시크릿 스캐너, DLP 도구와
# 병행해야 한다.
# =============================================================================

from __future__ import annotations

import re

from leakage_mock import Verdict

# 사용자가 "코드 리뷰 좀 봐줘"라며 그대로 붙여넣은 코드 스니펫 (더미 값).
USER_PASTE = """\
아래 함수가 왜 401 에러를 내는지 봐줄래?

def call_payment_api():
    api_key = "sk-proj-9fQ2mK7pX1vB4nD8sT3wZ6yC0aL5rH2j"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.post(
        "https://api.payments.example.com/charge",
        headers=headers,
        json={"contact": "billing-admin@internal-corp.example.com"},
    )
"""

_API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _find_sensitive(text: str) -> list[str]:
    hits = _API_KEY_PATTERN.findall(text) + _EMAIL_PATTERN.findall(text)
    return hits


def vulnerable_send_to_vendor(user_paste: str) -> Verdict:
    """취약 구현: 원문을 마스킹 없이 그대로 벤더 API 호출/로그에 남긴다."""
    vendor_call_log = f"[벤더 API 호출 로그] prompt={user_paste!r}"
    siem_log = f"[SIEM 로그] raw_input={user_paste!r}"
    leaked_items = _find_sensitive(vendor_call_log + siem_log)

    return Verdict(
        text=f"{vendor_call_log}\n{siem_log}",
        leaked=bool(leaked_items),
        leaked_items=leaked_items,
        reason="마스킹 없이 원문을 벤더 호출과 로그에 그대로 남김",
    )


def _redact(text: str) -> str:
    text = _API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
    text = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    return text


def secure_send_to_vendor(user_paste: str) -> Verdict:
    """보안 구현: 벤더로 보내기 전에 Context Redaction(마스킹)을 적용한다."""
    redacted = _redact(user_paste)
    vendor_call_log = f"[벤더 API 호출 로그] prompt={redacted!r}"
    siem_log = f"[SIEM 로그] raw_input={redacted!r}"
    leaked_items = _find_sensitive(vendor_call_log + siem_log)

    return Verdict(
        text=f"{vendor_call_log}\n{siem_log}",
        leaked=bool(leaked_items),
        leaked_items=leaked_items,
        reason="전송/로깅 전 정규식 기반 마스킹(Context Redaction) 적용",
    )


def main() -> None:
    print("=" * 70)
    print("예제 1: 자격증명/PII 유출 (Context Redaction 미적용)")
    print("=" * 70)
    print(f"[사용자가 붙여넣은 원문]\n{USER_PASTE}")

    print("-" * 70)
    print("[취약 경로] vulnerable_send_to_vendor()")
    print("-" * 70)
    vuln = vulnerable_send_to_vendor(USER_PASTE)
    print(f"{vuln.text}\n")
    print(f"유출된 항목: {vuln.leaked_items}")
    print(f"판정: 유출 발생 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_send_to_vendor()")
    print("-" * 70)
    safe = secure_send_to_vendor(USER_PASTE)
    print(f"{safe.text}\n")
    print(f"유출된 항목: {safe.leaked_items}")
    print(f"판정: 유출 발생 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 자격증명/이메일 유출이 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 마스킹 후 유출이 없어야 한다"
    print("PASS: 취약 경로는 원문 그대로 유출, 보안 경로는 Context Redaction으로 차단함을 확인.")


if __name__ == "__main__":
    main()
