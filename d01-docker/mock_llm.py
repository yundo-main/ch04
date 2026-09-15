# mock_llm.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 '가짜 LLM'.
#
# 실제 LLM 은 시스템 지시문 / 사용자 입력 / 검색된 문서를 구조적으로 분리하지 않고
# 하나의 토큰 스트림으로 받는다. 이 스트림 안에 명령형 문장이 섞여 있으면
# 모델이 그것을 '지시'로 오인해서 따를 수 있다 — 이것이 프롬프트 인젝션의 근본 원인이다.
#
# 이 mock 모델은 그 취약점 class 를 결정론적으로 재현한다:
#   - naive_generate(): 시스템 지시문과 신뢰할 수 없는 입력을 구분 없이 하나의
#     문자열로 합쳐서 받는다. INJECTION_PATTERNS 에 해당하는 문구가 있으면
#     시스템 지시문 대신 그 문구를 '따른다' (= 인젝션 성공을 시뮬레이션).
#   - guarded_generate(): 신뢰할 수 없는 입력을 별도 채널(untrusted_blocks)로 받고,
#     그 안에서 발견된 명령형 문구는 절대 실행하지 않는다. 대신 탐지 결과만
#     감사 로그로 남긴다.
#
# 주의(잔여 위험 고지): 이 mock 은 트랜스포머 어텐션 메커니즘을 흉내내는 것이
# 아니다. "명령/데이터 채널이 분리되지 않으면 데이터가 곧 명령이 될 수 있다"는
# 구조적 취약점만 교육용으로 단순화한 것이다. 실제 모델에서는 패턴 매칭으로
# 잡히지 않는 우회(인코딩, 다국어, 간접 지시 등)가 가능하므로, 여기서 보여주는
# guarded_generate() 의 방어가 "인젝션 무력화"를 보장한다고 해석하면 안 된다.
# 실제 배포 전에는 레드팀 테스트와 출력/도구 호출 화이트리스트 검증이 필요하다.
# =============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# 공격자가 흔히 쓰는 인젝션 문구 패턴 (교육용 최소 집합, 실제 탐지기는 훨씬 넓어야 함)
INJECTION_PATTERNS = [
    r"이전\s*지시.{0,10}(무시|잊)",
    r"지금까지.{0,10}지시.{0,10}(무시|잊)",
    r"시스템\s*프롬프트.{0,15}(출력|공개|보여)",
    r"system\s*prompt",
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"디버그\s*모드",
    r"\[system\]",
    r"실제\s*시스템\s*명령",
    r"계좌.{0,10}입금",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


@dataclass
class GenerationResult:
    text: str
    injection_detected: bool
    matched_patterns: List[str] = field(default_factory=list)
    obeyed_injected_instruction: bool = False


def _find_injection_matches(text: str) -> List[str]:
    hits = []
    for pattern in _COMPILED_PATTERNS:
        m = pattern.search(text)
        if m:
            hits.append(m.group(0))
    return hits


def naive_generate(system_instruction: str, untrusted_text: str) -> GenerationResult:
    """취약 경로: 시스템 지시문과 신뢰할 수 없는 입력을 구분 없이 하나로 합쳐서 처리.

    합쳐진 전체 텍스트 안에서 인젝션 패턴이 발견되면, 모델이 시스템 지시문 대신
    공격자 지시를 '따르는' 것으로 시뮬레이션한다(= 데이터가 명령이 된 상태).
    """
    combined = f"{system_instruction}\n{untrusted_text}"
    matches = _find_injection_matches(combined)

    if matches:
        # 인젝션 성공 시뮬레이션: 시스템 지시문을 무시하고 공격자가 원하는 것으로 보이는
        # 응답(여기서는 시스템 지시문 원문 노출 또는 악성 유도 문구 반영)을 반환한다.
        leaked = system_instruction if "시스템 프롬프트" in untrusted_text or "system prompt" in untrusted_text.lower() else None
        if leaked:
            text = f"[유출된 시스템 프롬프트]\n{leaked}"
        else:
            text = f"[공격자 지시 이행] 아래 문서에 포함된 지시를 그대로 따릅니다:\n{untrusted_text}"
        return GenerationResult(text=text, injection_detected=True, matched_patterns=matches, obeyed_injected_instruction=True)

    return GenerationResult(text="[정상 응답] 요청하신 내용에 안전하게 답변합니다.", injection_detected=False)


def guarded_generate(
    system_instruction: str,
    safe_answer: str,
    untrusted_blocks: List[str],
) -> GenerationResult:
    """보안 경로: 신뢰 경계를 구조적으로 분리.

    - system_instruction 은 항상 우선하고, untrusted_blocks 내용에 의해 대체되지 않는다.
    - untrusted_blocks 는 '데이터'로만 취급된다 — 그 안의 명령형 문구는 절대 실행하지 않는다.
    - 다만 탐지는 수행해서 감사/콘텐츠 검수 파이프라인에 넘길 신호를 남긴다.
    """
    all_matches: List[str] = []
    for block in untrusted_blocks:
        all_matches.extend(_find_injection_matches(block))

    return GenerationResult(
        text=safe_answer,
        injection_detected=bool(all_matches),
        matched_patterns=all_matches,
        obeyed_injected_instruction=False,
    )
