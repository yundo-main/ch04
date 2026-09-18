# local_llm.py
# =============================================================================
# ch04/d01~d08 이 공유하는 로컬 Ollama HTTP 클라이언트 — 전송 계층만 담당한다.
#
# 이 파일은 어떤 챕터의 콘텐츠(공격 프롬프트 구성, 판정 로직)도 모른다.
# 각 챕터에는 이 파일을 그대로 재노출하는 얇은 `wrapper.py`가 하나씩 있고,
# 메인 스크립트는 이 파일을 직접 import 하지 않고 그 `wrapper.py`를 통해
# 쓴다 — `wrapper.py`는 전송 재노출만 할 뿐 콘텐츠는 전혀 모른다(콘텐츠는
# 각 스크립트의 run_real() 또는 그 챕터의 prompts.py에 있다). 예:
# d02/persona_jailbreak.py 는 `wrapper.py`가 재노출한 chat_messages() 를
# 호출해서 실제 모델에 페르소나 탈옥 시도를 보낸다.
#
# 사전 준비
#   1) Ollama 설치 및 데몬 실행 (macOS): brew install ollama && ollama serve
#   2) 모델 pull: ollama pull exaone3.5:2.4b
#
# 외부 API 나 시크릿이 필요 없다 — 전부 localhost:11434 로 로컬 호출.
# OLLAMA_HOST 환경변수로 서버 주소를, OLLAMA_MODEL 환경변수로 기본 모델을
# 재정의할 수 있다. 매번 커맨드라인에 넣는 대신 d00-shared/.env 파일에
# 고정해둘 수 있다(d00-shared/.env.example 참고 — 복사해서 d00-shared/.env로
# 저장하면 이 파일이 자동으로 읽는다. .env는 .gitignore 대상).
# 예: OLLAMA_MODEL=qwen2.5-1.5b-vulnerable-fixed python d02/persona_jailbreak.py
# 다만 Docker 실습은 mock 전용 정책이라 이 파일의 네트워크 호출 자체가
# 컨테이너 안에서 쓰이지 않는다 — d00-shared/guide.md 참고.
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
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "exaone3.5:2.4b")


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


def chat_messages(
    model: str, messages: List[dict], timeout: float = 180.0, temperature: float = 0.7
) -> RealGenerationResult:
    """가장 일반적인 형태 — OpenAI/Ollama 스타일 메시지 리스트를 그대로 전달한다.

    시스템/사용자 메시지를 어떻게 나눌지(또는 하나로 합칠지)는 호출부가
    결정한다 — 그 구성 자체가 각 예제의 "취약/보안 경로" 차이이기 때문이다.
    temperature 도 호출부가 정한다 — 문맥 재현(원문 인용)이 핵심인 예제는
    낮은 값을 넘겨 창작 편향을 줄일 수 있다(기본값 0.7 은 기존 호출과 동일).
    """
    payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": temperature}}
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


def ask_real(
    system_instruction: str,
    user_content: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 180.0,
    temperature: float = 0.7,
) -> RealGenerationResult:
    """가장 흔한 1턴 system+user 호출을 위한 편의 함수. chat_messages() 의 얇은 wrapper."""
    return chat_messages(
        model,
        [{"role": "system", "content": system_instruction}, {"role": "user", "content": user_content}],
        timeout=timeout,
        temperature=temperature,
    )
