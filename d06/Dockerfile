# ch04/d06 Retrieval 보안 구현 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/d00-shared 의 공용 모듈(local_llm.py)을 함께
# COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# prompts.py는 d06 로컬 복사본을 쓴다.
# documents.json은 d06 로컬 복사본을 쓴다(d00-shared 공유 없음). ch04/ 에서:
#   docker build -f d06/Dockerfile -t retrieval-security-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d00-shared/local_llm.py ./
COPY d06/documents.json d06/prompts.py d06/retrieval_security_mock.py d06/wrapper.py d06/retrieval_authorization_enforcement.py d06/embedding_poisoning.py d06/chunk_sanitization.py ./

# 기본 실행: 세 예제를 순서대로 실행. Docker는 mock 전용 정책이라 예제 3의
# CMD에 --mock을 명시한다(실제 모델 검증은 로컬 venv에서 진행).
# 하나만 실행하려면: docker run <image> python embedding_poisoning.py
CMD ["sh", "-c", "python retrieval_authorization_enforcement.py && echo '========================================' && python embedding_poisoning.py && echo '========================================' && python chunk_sanitization.py --mock"]
