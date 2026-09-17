# e2e_pipeline.py
# =============================================================================
# API 키 없이 재현 가능한 규칙 기반 시뮬레이션 — ch04/d01~d07에서 각각
# 다룬 7가지 통제를 하나의 End-to-End RAG 파이프라인으로 결합한다.
#
# ch04 "4-8. End-to-End 보안 통합" 매핑:
#   1) vulnerable_e2e.py — Lab 1(동일 시나리오, 통제 전부 OFF)
#   2) secure_e2e.py     — Lab 2(동일 시나리오, 통제 전부 ON)
#   3) gap_analysis.py   — Lab 3(통제 하나씩 isolate해서 7항 자체 채점)
#
# PipelineConfig의 7개 플래그는 앞선 챕터와 1:1 대응한다:
#   block_prompt_injection        — d01 프롬프트 인젝션 방어
#   resist_persona_jailbreak      — d02 탈옥(Jailbreak) 방어
#   mask_credential_pii           — d03 데이터 유출(PII/자격증명) 방지
#   filter_by_role_acl            — d04 RAG 권한 필터링(ACL)
#   enforce_classification        — d05 문서 보안 등급 체계(clearance)
#   revalidate_and_sanitize_retrieval — d06 Retrieval 실행 지점 재검증 + 청크 새니타이징
#   scan_canary_with_audit        — d07 Canary Token 탐지 + 감사 로그
#
# 주의(잔여 위험 고지): 문서 내용/조직 정보/canary 값은 전부 가짜(더미)
# 데이터다. 실제 임베딩 대신 키워드 겹침 점수로 검색을 시뮬레이션한다.
# =============================================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import List, Optional

from real_llm import DEFAULT_MODEL, ask_real  # noqa: E402
from prompts import RAG_ANSWER_SYSTEM_INSTRUCTION  # noqa: E402


class Classification(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class Clearance(IntEnum):
    L1 = 0
    L2 = 1
    L3 = 2
    L4 = 3


INJECTION_MARKERS = ["[SYSTEM]", "이전 지시를 무시", "지금부터"]
JAILBREAK_PHRASES = ["개발자 모드", "모든 필터를 해제"]
PHONE_PATTERN = re.compile(r"01[016789]-?\d{3,4}-?\d{4}")


@dataclass
class Document:
    doc_id: str
    classification: Classification
    allowed_roles: set
    owner: str
    canary_token: Optional[str]
    text: str


def load_corpus(path: str = "documents.json") -> List[Document]:
    """이 폴더 전용 로컬 복사본을 쓴다(d00-shared 공유 없음) — 로컬(venv)/Docker
    어디서든 이 파일과 같은 디렉터리에서 찾는다."""
    doc_path = Path(__file__).resolve().parent / path
    with open(doc_path, encoding="utf-8") as f:
        raw = json.load(f)
    return [
        Document(
            doc_id=d["doc_id"],
            classification=Classification[d["classification"].upper()],
            allowed_roles=set(d["allowed_roles"]),
            owner=d["owner"],
            canary_token=d["canary_token"],
            text=d["text"],
        )
        for d in raw
    ]


CORPUS = load_corpus()
CANARY_REGISTRY = {d.canary_token: d.doc_id for d in CORPUS if d.canary_token}


@dataclass
class PipelineConfig:
    block_prompt_injection: bool = False
    resist_persona_jailbreak: bool = False
    mask_credential_pii: bool = False
    filter_by_role_acl: bool = False
    enforce_classification: bool = False
    revalidate_and_sanitize_retrieval: bool = False
    scan_canary_with_audit: bool = False


@dataclass
class PipelineResult:
    response: str
    clean_query: str
    injection_accepted: bool
    unauthorized_cited: bool
    canary_exposed: bool
    audit_events: List[str] = field(default_factory=list)


def _strip_all(text: str, markers: List[str]) -> str:
    result = text
    for m in markers:
        result = result.replace(m, "")
    return result


def _keyword_search(query: str, docs: List[Document], top_k: int = 1) -> List[Document]:
    scored = [(len(set(query) & set(d.text)), d) for d in docs]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [d for _score, d in scored[:top_k]]


def handle_query(
    query: str,
    requester_role: str,
    requester_clearance: Clearance,
    config: PipelineConfig,
    corpus: Optional[List[Document]] = None,
    use_real_llm: bool = False,
    model: Optional[str] = None,
) -> PipelineResult:
    corpus = corpus if corpus is not None else CORPUS
    audit: List[str] = []

    injection_present = any(m in query for m in INJECTION_MARKERS)
    clean_query = query
    if injection_present and config.block_prompt_injection:
        clean_query = _strip_all(clean_query, INJECTION_MARKERS)
        audit.append("prompt_injection_blocked")

    jailbreak_present = any(p in clean_query for p in JAILBREAK_PHRASES)
    if jailbreak_present and config.resist_persona_jailbreak:
        clean_query = _strip_all(clean_query, JAILBREAK_PHRASES)
        audit.append("jailbreak_resisted")

    candidates = corpus
    if config.filter_by_role_acl:
        candidates = [d for d in candidates if requester_role in d.allowed_roles]
    if config.enforce_classification:
        candidates = [d for d in candidates if requester_clearance >= d.classification]

    hits = _keyword_search(clean_query, candidates, top_k=1)

    if config.revalidate_and_sanitize_retrieval:
        hits = [d for d in hits if requester_role in d.allowed_roles and requester_clearance >= d.classification]
        if hits:
            audit.append("retrieval_revalidated")
        chunk_texts = [_strip_all(d.text, INJECTION_MARKERS) for d in hits]
    else:
        chunk_texts = [d.text for d in hits]

    unauthorized_cited = any(
        requester_role not in d.allowed_roles or requester_clearance < d.classification for d in hits
    )

    if use_real_llm:
        if chunk_texts:
            user_content = f"[참고 문서]\n{chunk_texts[0]}\n\n[질문] {clean_query}"
            real_result = ask_real(RAG_ANSWER_SYSTEM_INSTRUCTION, user_content, model=model or DEFAULT_MODEL)
            response = real_result.text if real_result.ok else f"[실제 모델 호출 실패: {real_result.error}]"
        else:
            response = "관련 문서를 찾을 수 없습니다."
    else:
        response = (
            f"질문하신 내용에 대한 문서 인용: {chunk_texts[0]}" if chunk_texts else "관련 문서를 찾을 수 없습니다."
        )

    if config.mask_credential_pii:
        response = PHONE_PATTERN.sub("[REDACTED-PHONE]", response)

    canary_hits = [t for t in CANARY_REGISTRY if t in response]
    canary_exposed = bool(canary_hits)
    if config.scan_canary_with_audit:
        audit.append("canary_scan_performed")
        if canary_hits:
            response = "[차단됨] 이 응답은 보안 정책에 따라 반환되지 않습니다."
            audit.append(f"canary_blocked:{canary_hits}")
            canary_exposed = False

    return PipelineResult(
        response=response,
        clean_query=clean_query,
        injection_accepted=injection_present and not config.block_prompt_injection,
        unauthorized_cited=unauthorized_cited,
        canary_exposed=canary_exposed,
        audit_events=audit,
    )
