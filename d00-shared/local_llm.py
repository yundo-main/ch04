# local_llm.py
# =============================================================================
# ch04/d01~d08 이 공유하는 로컬 Ollama HTTP 클라이언트 — 전송 계층만 담당한다.
#
# 이 파일은 어떤 챕터의 시나리오(공격 프롬프트 구성, 판정 로직)도 모른다.
# 각 챕터는 이 파일을 자기 폴더의 메인 스크립트에서 직접 import 해서 쓴다 —
# 챕터마다 별도의 real_llm.py wrapper를 두지 않는다(이전에는 각 챕터에
# `real_llm.py`라는 중간 계층이 있었지만, 스크립트 하나당 계층이 두 겹이 되는
# 게 불필요한 간접화라고 판단해 없앴다). 예: d02/persona_jailbreak.py 는 이
# 파일의 chat_messages() 를 직접 호출해서 실제 모델에 페르소나 탈옥 시도를
# 보낸다.
#
# 사전 준비
#   1) Ollama 설치 및 데몬 실행 (macOS): brew install ollama && ollama serve
#   2) 모델 pull: ollama pull exaone3.5:2.4b
#
# 외부 API 나 시크릿이 필요 없다 — 전부 localhost:11434 로 로컬 호출.
# OLLAMA_HOST 환경변수로 재정의 가능(다만 Docker 실습은 mock 전용 정책이라
# 이 파일의 네트워크 호출 자체가 컨테이너 안에서 쓰이지 않는다 — d00-shared/
# guide.md 참고).
#
# 잔여 위험: 실제 모델은 버전/온도(temperature)/문구에 따라 결과가 달라진다
# (비결정적일 수 있음). 이 클라이언트로 얻은 결과 하나로 "이 모델은 안전/
# 취약하다"고 일반화하면 안 된다 — 반복 검증(레드팀 테스트)이 필요하다.
# =============================================================================

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = "exaone3.5:2.4b"


@dataclass
class RealGenerationResult:
    text: str
    model: str
    ok: bool
    error: str = ""


def is_ollama_available(timeout: float = 1.5) -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        return True
    except (urllib.error.URLError, OSError):
        return False


def chat_messages(model: str, messages: List[dict], timeout: float = 60.0) -> RealGenerationResult:
    """가장 일반적인 형태 — OpenAI/Ollama 스타일 메시지 리스트를 그대로 전달한다.

    시스템/사용자 메시지를 어떻게 나눌지(또는 하나로 합칠지)는 호출부가
    결정한다 — 그 구성 자체가 각 예제의 "취약/보안 경로" 차이이기 때문이다.
    """
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.7}}
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body.get("message", {}).get("content", "").strip()
        return RealGenerationResult(text=text, model=model, ok=True)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        return RealGenerationResult(text="", model=model, ok=False, error=str(exc))


def ask_real(system_instruction: str, user_content: str, model: str = DEFAULT_MODEL, timeout: float = 60.0) -> RealGenerationResult:
    """가장 흔한 1턴 system+user 호출을 위한 편의 함수. chat_messages() 의 얇은 wrapper."""
    return chat_messages(
        model,
        [{"role": "system", "content": system_instruction}, {"role": "user", "content": user_content}],
        timeout=timeout,
    )
