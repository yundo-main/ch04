# real_llm.py
# =============================================================================
# leakage_mock.py 의 세 예제는 "민감정보가 벤더 호출/응답/로그에 도달하기
# 전에 걸러지는가"라는 파이프라인 결정을 규칙 기반으로 결정론적으로 재현할
# 뿐, 실제 모델이 그 데이터를 응답에 얼마나 그대로 되풀이하는지는 보여주지
# 않는다. 이 파일은 ch04/shared/local_llm.py 의 공용 Ollama 클라이언트를
# 그대로 재노출한다 — d03의 세 예제는 시나리오별 프롬프트를 직접
# 구성(USER_PASTE/CORPUS/SHARED_MEMORY 재사용)해서 `ask_real()`을 호출하므로
# 이 폴더 전용 wrapper 함수가 따로 필요 없다.
#
# 사전 준비 / 잔여 위험은 ch04/shared/local_llm.py 상단 주석 참고.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from local_llm import DEFAULT_MODEL, RealGenerationResult, ask_real, is_ollama_available  # noqa: E402,F401

__all__ = ["DEFAULT_MODEL", "RealGenerationResult", "ask_real", "is_ollama_available"]
