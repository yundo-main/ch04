# canary_placement.py
# =============================================================================
# 예제 1: Canary Token 배치 — 재사용된 canary로 인한 출처 특정(attribution) 실패
#
# 강의안 매핑: Lab 1 "config.py / vector_db.py에서 카나리아 문자열·문서 확인".
#
# 위협 모델
#   - 자산: 유출 사고 발생 시, canary 매칭만으로 "어느 문서/부서에서
#     새어나갔는지"를 특정할 수 있는 능력(사고 대응 속도와 직결).
#   - 신뢰 경계: "canary 토큰 하나를 여러 decoy 문서에 재사용해도 유출은
#     탐지된다" ↔ "canary는 문서 단위로 고유해야 출처까지 특정된다"는 서로
#     다른 명제다. 탐지는 되어도 출처를 못 찾으면, 어느 문서를 격리하고
#     누구에게 책임을 물을지 알 수 없어 대응이 지연된다.
#   - 공격자 역량: 무관 — 이 예제는 공격이 아니라 canary 배치 설계 자체의
#     결함(재사용)을 다룬다.
#
# 재현 절차
#   python canary_placement.py
#
# 관찰 포인트
#   - vulnerable_deploy_canaries(): 모든 decoy 문서에 동일한 canary
#     문자열(STATIC_CANARY) 하나를 재사용 → 유출된 canary로 역조회하면
#     후보 문서가 여러 개 나와 출처를 하나로 좁힐 수 없다.
#   - secure_deploy_canaries(): documents.json에 문서별로 이미 부여된 고유
#     canary_token을 그대로 사용 → 유출된 canary 하나가 정확히 문서 하나에
#     매핑되어 출처가 즉시 특정된다.
# =============================================================================

from __future__ import annotations

from typing import Dict, List

from canary_mock import Verdict, load_canary_documents

CORPUS = load_canary_documents()

STATIC_CANARY = "CANARY-SHARED-0001"  # 재사용되는(잘못된) canary


def vulnerable_deploy_canaries() -> Dict[str, List[str]]:
    """취약 구현: 모든 decoy 문서에 동일한 canary를 재사용해 배치한다."""
    registry: Dict[str, List[str]] = {}
    for doc in CORPUS:
        registry.setdefault(STATIC_CANARY, []).append(doc.doc_id)
    return registry


def secure_deploy_canaries() -> Dict[str, List[str]]:
    """보안 구현: 문서별 고유 canary_token으로 1:1 레지스트리를 만든다."""
    registry: Dict[str, List[str]] = {}
    for doc in CORPUS:
        registry.setdefault(doc.canary_token, []).append(doc.doc_id)
    return registry


def identify_source(registry: Dict[str, List[str]], token: str) -> Verdict:
    candidates = registry.get(token, [])
    ambiguous = len(candidates) != 1
    return Verdict(
        text=f"token={token!r} → 후보 문서: {candidates}",
        leaked=ambiguous,
        leaked_items=candidates,
        reason=(
            "동일 canary를 여러 문서가 공유해 출처를 하나로 특정할 수 없음"
            if ambiguous
            else "canary가 문서 하나에만 매핑되어 있어 정확히 특정됨"
        ),
    )


def main() -> None:
    leaked_doc = next(d for d in CORPUS if d.doc_id == "restricted-ma-duediligence")

    print("=" * 70)
    print("예제 1: Canary Token 배치 — 재사용 canary로 인한 출처 특정 실패")
    print("=" * 70)
    print(f"[유출 시나리오] {leaked_doc.doc_id} 문서가 어딘가로 유출된 것을 canary 매칭으로 발견\n")

    print("-" * 70)
    print("[취약 경로] vulnerable_deploy_canaries() — canary 재사용")
    print("-" * 70)
    vuln_registry = vulnerable_deploy_canaries()
    vuln = identify_source(vuln_registry, STATIC_CANARY)
    print(f"결과: {vuln.text}")
    print(f"사유: {vuln.reason}")
    print(f"판정: 출처 특정 실패 = {vuln.leaked}")

    print()
    print("-" * 70)
    print("[보안 경로] secure_deploy_canaries() — 문서별 고유 canary")
    print("-" * 70)
    safe_registry = secure_deploy_canaries()
    safe = identify_source(safe_registry, leaked_doc.canary_token)
    print(f"결과: {safe.text}")
    print(f"사유: {safe.reason}")
    print(f"판정: 출처 특정 실패 = {safe.leaked}")

    print()
    print("=" * 70)
    print("검증 기준 (assert)")
    print("=" * 70)
    assert vuln.leaked is True, "취약 경로는 canary 재사용으로 인한 출처 특정 실패가 재현돼야 한다"
    assert safe.leaked is False, "보안 경로는 고유 canary로 출처가 정확히 특정돼야 한다"
    print("PASS: 취약 경로는 재사용된 canary로 후보 문서 여러 개가 나와 출처 특정 실패, 보안 경로는 고유 canary로 즉시 특정됨을 확인.")


if __name__ == "__main__":
    main()
