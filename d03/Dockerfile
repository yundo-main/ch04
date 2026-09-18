# ch04/d03 LLM 데이터 유출 위험 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/d00-shared 의 공용 모듈(local_llm.py)을 함께
# COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# prompts.py는 d03 로컬 복사본을 쓴다.
# ch04/ 에서:
#   docker build -f d03/Dockerfile -t llm-data-leakage-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d00-shared/local_llm.py ./
COPY d03/leakage_mock.py d03/wrapper.py d03/credential_pii_leak.py d03/multitenant_rag_leak.py d03/memory_poisoning_leak.py d03/prompts.py ./

# 기본 실행: 세 예제를 순서대로 실행. Docker는 mock 전용 정책이라 CMD에
# --mock을 명시한다(실제 모델 검증은 로컬 venv에서 진행).
# 하나만 실행하려면: docker run <image> python credential_pii_leak.py --mock
CMD ["sh", "-c", "python credential_pii_leak.py --mock && echo '========================================' && python multitenant_rag_leak.py --mock && echo '========================================' && python memory_poisoning_leak.py --mock"]
