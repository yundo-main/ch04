# real_llm.py
# =============================================================================
# response_canary_scanning.py / exfiltration_simulation.py 는 "canary가
# 포함된 응답을 스캔·차단하는가"를 규칙 기반으로 결정론적으로 재현할 뿐,
# 실제 모델이 인코딩·요약·의역 요청에 어떻게 반응하는지는 보여주지 않는다.
# 이 파일은 ch04/shared/local_llm.py 의 공용 Ollama 클라이언트를 그대로
# 재노출한다.
#
# 사전 준비 / 잔여 위험은 ch04/shared/local_llm.py 상단 주석 참고.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from local_llm import DEFAULT_MODEL, RealGenerationResult, ask_real, is_ollama_available  # noqa: E402,F401

__all__ = ["DEFAULT_MODEL", "RealGenerationResult", "ask_real", "is_ollama_available"]
