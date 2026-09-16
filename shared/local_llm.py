# local_llm.py
# =============================================================================
# ch04/d01~d08 이 공유하는 로컬 Ollama HTTP 클라이언트.
#
# 각 챕터는 이 파일을 직접 import 하지 않는다 — 대신 자기 폴더의 real_llm.py
# (얇은 wrapper)가 sys.path 로 이 디렉터리를 찾아 chat_messages()/ask_real()을
# 가져오고, 그 위에 자기 챕터 전용 공격 시나리오(프롬프트 구성) 함수를 얹는다.
# 예: d02/real_llm.py 의 persona_jailbreak_real() 는 chat_messages() 를
# 호출해서 실제 모델에 페르소나 탈옥 시도를 보낸다.
#
# 사전 준비
#   1) Ollama 설치 및 데몬 실행 (macOS): brew install ollama && ollama serve
#   2) 소형 모델 pull: ollama pull llama3.2:1b
#
# 외부 API 나 시크릿이 필요 없다 — 전부 localhost:11434 로 로컬 호출.
# OLLAMA_HOST 환경변수로 재정의 가능(Docker 컨테이너에서 호스트의 Ollama에
# 연결할 때 필요 — 각 챕터 guide.md의 "Docker 컨테이너에서 --real 실행 시" 참고).
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
DEFAULT_MODEL = "llama3.2:1b"


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
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.2}}
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
