# real_llm.py
# =============================================================================
# e2e_pipeline.py 의 handle_query() 는 기본적으로 응답을 f-string 으로
# 조립하는 결정론적 mock 이다 — 인젝션 차단/ACL/등급 필터/retrieval 재검증/
# 새니타이징/canary 스캔 같은 파이프라인 통제는 전부 진짜 로직이지만,
# "모델이 최종적으로 뭐라고 답하는가"는 재현하지 않는다. 이 파일은
# ch04/shared/local_llm.py 의 공용 Ollama 클라이언트를 그대로 재노출한다 —
# handle_query() 가 use_real_llm=True 일 때 이 클라이언트로 마지막 응답
# 생성 단계만 교체하고, 나머지 7개 통제는 동일하게 적용한다.
#
# 사전 준비 / 잔여 위험은 ch04/shared/local_llm.py 상단 주석 참고.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))  # 로컬 동명 파일이 있으면 그게 우선

from local_llm import DEFAULT_MODEL, RealGenerationResult, ask_real, is_ollama_available  # noqa: E402,F401

__all__ = ["DEFAULT_MODEL", "RealGenerationResult", "ask_real", "is_ollama_available"]
