# real_llm.py
# =============================================================================
# chunk_sanitization.py 는 "새니타이징된 컨텍스트에 인젝션 마커/PII 문자열이
# 남아 있는가"만 규칙 기반으로 결정론적으로 판정한다 — 그 컨텍스트를 실제로
# 받은 모델이 잔존 지시(마커는 지워졌지만 명령 본문은 남은 문장)를 실제로
# 따르는지는 보여주지 않는다. 이 파일은 ch04/shared/local_llm.py 의 공용
# Ollama 클라이언트를 그대로 재노출한다.
#
# 사전 준비 / 잔여 위험은 ch04/shared/local_llm.py 상단 주석 참고.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from local_llm import DEFAULT_MODEL, RealGenerationResult, ask_real, is_ollama_available  # noqa: E402,F401

__all__ = ["DEFAULT_MODEL", "RealGenerationResult", "ask_real", "is_ollama_available"]
