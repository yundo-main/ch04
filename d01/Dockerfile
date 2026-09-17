# ch04/d01 프롬프트 인젝션 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — GEMINI_API_KEY 등 시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/d00-shared 의 공용 모듈(mock_llm.py, local_llm.py)을
# 함께 COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# prompts.py/documents.json은 d01 로컬 복사본을 쓴다. ch04/ 에서 다음처럼
# 빌드한다:
#   docker build -f d01/Dockerfile -t prompt-injection-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d00-shared/mock_llm.py d00-shared/local_llm.py ./
COPY d01/real_llm.py d01/direct_injection.py d01/indirect_injection.py d01/documents.json d01/prompts.py ./

# 기본 실행: 두 예제를 순서대로 실행. Docker는 mock 전용 정책이라 CMD에
# --mock을 명시한다(실제 모델 검증은 로컬 venv에서 진행).
# 하나만 실행하려면: docker run <image> python direct_injection.py --mock
CMD ["sh", "-c", "python direct_injection.py --mock && echo '========================================' && python indirect_injection.py --mock"]
