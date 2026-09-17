# real_llm.py
# =============================================================================
# ch04/d00-shared/local_llm.py(공용 Ollama 클라이언트)를 그대로 재노출하는
# wrap — "어떻게 전송하는가"만 안다. d03 전용 시나리오 콘텐츠(USER_PASTE,
# 검색 컨텍스트 조합 등)는 여기 없다 — 각 스크립트의 run_real() 안에 있다.
#
# 사전 준비 / 잔여 위험은 ch04/d00-shared/local_llm.py 상단 주석 참고.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "d00-shared"))  # 로컬 동명 파일이 있으면 그게 우선

from local_llm import DEFAULT_MODEL, RealGenerationResult, ask_real, is_ollama_available  # noqa: E402,F401

__all__ = ["DEFAULT_MODEL", "RealGenerationResult", "ask_real", "is_ollama_available"]
