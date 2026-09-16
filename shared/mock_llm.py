# mock_llm.py (ch04/shared)
# =============================================================================
# ch04/d01~d08 이 공유하는, API 키 없이 재현 가능한 규칙 기반 '가짜 LLM' 엔진
# (가중치 기반, v2). 각 챕터는 이 파일을 직접 수정하지 않는다 — 자기 폴더에
# 필요하면 이 엔진(PatternRule/score_text/naive_generate/guarded_generate)을
# sys.path 로 가져와 자기 챕터 전용 카탈로그를 추가로 정의해서 쓴다.
#
# v1(단순 정규식 완전일치)과의 차이 — 세 가지를 동시에 개선한다:
#   1) 판정 정확도: 패턴 하나가 매치되면 무조건 켜고 끄는 이진 판정 대신,
#      규칙마다 가중치(weight)를 매겨 위험도 점수(risk_score, 0.0~1.0)를
#      누적한다. 약한 신호 여러 개가 겹치면 하나만으로는 안 걸리던 입력도
#      임계값을 넘을 수 있다 — 실제 콘텐츠 모더레이션 API의 스코어링 방식에
#      더 가깝다.
#   2) 응답의 다양성: 매칭된 규칙들의 category(override/prompt_leak/
#      financial_exfil)에 따라 서로 다른 "공격 성공" 응답을 합성한다.
#      항상 같은 고정 문자열을 반환하지 않는다 — 어떤 지시가 우세했는지에
#      따라 실제 모델의 응답도 달라진다는 것을 흉내낸다.
#   3) 재사용성: 판정 로직(score_text/naive_generate/guarded_generate)이
#      PatternRule 카탈로그를 인자로 받는 범용 엔진이라, 다른 챕터
#      (예: d02 jailbreak, d03 leakage)도 자신만의 카탈로그를 정의해 같은
#      엔진을 재사용할 수 있다. 이 파일에는 d01(프롬프트 인젝션)용
#      INJECTION_PATTERNS 카탈로그가 기본값으로 들어 있다.
#
# 실제 LLM 은 시스템 지시문 / 사용자 입력 / 검색된 문서를 구조적으로 분리하지
# 않고 하나의 토큰 스트림으로 받는다. 이 스트림 안에 명령형 문장이 섞여 있으면
# 모델이 그것을 '지시'로 오인해서 따를 수 있다 — 이것이 프롬프트 인젝션의
# 근본 원인이다. 이 mock 은 그 취약점 class 를 재현한다:
#   - naive_generate(): 시스템 지시문과 신뢰할 수 없는 입력을 구분 없이 하나의
#     문자열로 합쳐서 받는다. 위험도 점수가 임계값을 넘으면 매칭된 카테고리에
#     따라 인젝션 성공을 시뮬레이션한다.
#   - guarded_generate(): 신뢰할 수 없는 입력을 별도 채널(untrusted_blocks)로
#     받고, 그 안에서 발견된 위험 신호는 절대 실행하지 않는다. 대신 위험도
#     점수만 감사 로그용으로 남긴다.
#
# 주의(잔여 위험 고지): 이 mock 은 트랜스포머 어텐션 메커니즘을 흉내내는 것이
# 아니다. 가중치도 사람이 임의로 정한 값이며, 실제 모델의 확률적 판단과 다르다.
# "명령/데이터 채널이 분리되지 않으면 데이터가 곧 명령이 될 수 있다"는 구조적
# 취약점만 교육용으로 단순화한 것이다. 실제 모델에서는 이 규칙으로 잡히지 않는
# 우회(인코딩, 다국어, 패러프레이징, 간접 지시 등)가 가능하므로, 여기서 보여주는
# guarded_generate() 의 방어가 "인젝션 무력화"를 보장한다고 해석하면 안 된다.
# 실제 배포 전에는 레드팀 테스트와 출력/도구 호출 화이트리스트 검증이 필요하다.
# =============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Pattern, Tuple


@dataclass(frozen=True)
class PatternRule:
    """가중치 기반 판정의 기본 단위. 다른 챕터에서 재사용할 때는 이 타입으로
    자신만의 카탈로그(List[PatternRule])를 정의해 score_text() 등에 넘기면 된다.
    """

    pattern: Pattern[str]
    weight: float
    category: str
    label: str


# --- d01 기본 카탈로그: 직접/간접 프롬프트 인젝션 탐지용 ---------------------
# 교육용 최소 집합이다. 실제 탐지기는 훨씬 넓은 카탈로그와 다국어/인코딩
# 대응이 필요하다(아래 잔여 위험 참고).
INJECTION_PATTERNS: List[PatternRule] = [
    PatternRule(re.compile(r"이전\s*지시.{0,10}(무시|잊)", re.IGNORECASE), 0.6, "override", "이전 지시 무시"),
    PatternRule(re.compile(r"지금까지.{0,10}지시.{0,10}(무시|잊)", re.IGNORECASE), 0.6, "override", "누적 지시 무시"),
    PatternRule(re.compile(r"시스템\s*프롬프트.{0,15}(출력|공개|보여)", re.IGNORECASE), 0.8, "prompt_leak", "시스템 프롬프트 출력 요청"),
    PatternRule(re.compile(r"시스템\s*프롬프트", re.IGNORECASE), 0.5, "prompt_leak", "시스템 프롬프트 언급"),
    PatternRule(re.compile(r"system\s*prompt", re.IGNORECASE), 0.4, "prompt_leak", "system prompt(영문 언급)"),
    PatternRule(re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE), 0.6, "override", "ignore instructions(영문)"),
    PatternRule(re.compile(r"디버그\s*모드", re.IGNORECASE), 0.4, "override", "디버그 모드 요청"),
    PatternRule(re.compile(r"\[system\]", re.IGNORECASE), 0.5, "override", "[SYSTEM] 마커"),
    PatternRule(re.compile(r"실제\s*시스템\s*명령", re.IGNORECASE), 0.5, "override", "시스템 명령 주장"),
    PatternRule(re.compile(r"계좌.{0,10}입금", re.IGNORECASE), 0.9, "financial_exfil", "계좌 입금 유도"),
]

DETECTION_THRESHOLD = 0.4  # 이 이상 누적되면 "의심스러운 입력"으로 탐지(감사 신호)
OBEY_THRESHOLD = 0.5  # 이 이상 누적되면 mock 이 "지시를 따름"으로 시뮬레이션


@dataclass
class GenerationResult:
    text: str
    injection_detected: bool = False
    matched_patterns: List[str] = field(default_factory=list)  # 매칭된 규칙의 label 목록
    obeyed_injected_instruction: bool = False
    risk_score: float = 0.0


def score_text(text: str, catalog: List[PatternRule] = INJECTION_PATTERNS) -> Tuple[float, List[PatternRule]]:
    """카탈로그의 각 규칙을 검사해 매칭된 규칙과 누적 위험도 점수(0.0~1.0, 상한 고정)를 반환한다."""
    matched = [rule for rule in catalog if rule.pattern.search(text)]
    score = min(1.0, sum(rule.weight for rule in matched))
    return round(score, 2), matched


def _find_injection_matches(text: str, catalog: List[PatternRule] = INJECTION_PATTERNS) -> List[str]:
    """(콘텐츠 스캔용) 매칭된 규칙의 label 목록만 반환한다 — indirect_injection.py 의
    수집 단계 격리(quarantine) 판정 등 다른 파일이 재사용하는 핵심 함수."""
    _, matched = score_text(text, catalog)
    return [rule.label for rule in matched]


def _synthesize_response(matched: List[PatternRule], untrusted_text: str, system_instruction: str) -> str:
    """매칭된 규칙들의 category 조합에 따라 서로 다른 '공격 성공' 응답을 합성한다.

    우선순위: 시스템 프롬프트 유출 > 금전 탈취 유도 > 일반 지시 이행. 실제
    모델도 여러 신호가 겹치면 그중 하나로 수렴해서 응답하지, 모든 신호를
    동시에 반영하지는 않는다는 점을 단순화해서 흉내낸다.
    """
    categories = {rule.category for rule in matched}

    if "prompt_leak" in categories:
        return f"[유출된 시스템 프롬프트]\n{system_instruction}"
    if "financial_exfil" in categories:
        return (
            "[공격자 지시 이행] 문서에 안내된 대로 아래 계좌로 즉시 입금 부탁드립니다. "
            "(모의 유출 콘텐츠 — 실제 계좌 아님)"
        )
    if "override" in categories:
        return f"[공격자 지시 이행] 아래 문서에 포함된 지시를 그대로 따릅니다:\n{untrusted_text}"
    return "[정상 응답] 요청하신 내용에 안전하게 답변합니다."


def naive_generate(
    system_instruction: str,
    untrusted_text: str,
    catalog: List[PatternRule] = INJECTION_PATTERNS,
) -> GenerationResult:
    """취약 경로: 시스템 지시문과 신뢰할 수 없는 입력을 구분 없이 하나로 합쳐서 처리.

    합쳐진 전체 텍스트의 위험도 점수가 OBEY_THRESHOLD 를 넘으면, 매칭된
    카테고리에 따라 서로 다른 '공격자 지시 이행' 응답을 합성해서 반환한다
    (= 인젝션 성공을 시뮬레이션).
    """
    combined = f"{system_instruction}\n{untrusted_text}"
    score, matched = score_text(combined, catalog)
    detected = score >= DETECTION_THRESHOLD
    obeyed = score >= OBEY_THRESHOLD

    text = (
        _synthesize_response(matched, untrusted_text, system_instruction)
        if obeyed
        else "[정상 응답] 요청하신 내용에 안전하게 답변합니다."
    )

    return GenerationResult(
        text=text,
        injection_detected=detected,
        matched_patterns=[rule.label for rule in matched],
        obeyed_injected_instruction=obeyed,
        risk_score=score,
    )


def guarded_generate(
    system_instruction: str,
    safe_answer: str,
    untrusted_blocks: List[str],
    catalog: List[PatternRule] = INJECTION_PATTERNS,
) -> GenerationResult:
    """보안 경로: 신뢰 경계를 구조적으로 분리.

    - system_instruction 은 항상 우선하고, untrusted_blocks 내용에 의해 대체되지 않는다.
    - untrusted_blocks 는 '데이터'로만 취급된다 — 그 안의 명령형 문구는 절대 실행하지 않는다.
    - 각 블록의 위험도 점수를 계산해서 감사/콘텐츠 검수 파이프라인에 넘길 신호는 남긴다.
    """
    all_matched: List[PatternRule] = []
    max_score = 0.0
    for block in untrusted_blocks:
        score, matched = score_text(block, catalog)
        max_score = max(max_score, score)
        all_matched.extend(matched)

    return GenerationResult(
        text=safe_answer,
        injection_detected=max_score >= DETECTION_THRESHOLD,
        matched_patterns=[rule.label for rule in all_matched],
        obeyed_injected_instruction=False,
        risk_score=max_score,
    )
