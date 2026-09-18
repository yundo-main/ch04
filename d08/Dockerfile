# ch04/d08 End-to-End 보안 통합 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/d00-shared 의 공용 모듈(local_llm.py)을 함께
# COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# prompts.py는 d08 로컬 복사본을 쓴다.
# documents.json은 d08 로컬 복사본을 쓴다(d00-shared 공유 없음). ch04/ 에서:
#   docker build -f d08/Dockerfile -t e2e-security-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d00-shared/local_llm.py ./
COPY d08/documents.json d08/prompts.py d08/wrapper.py d08/e2e_pipeline.py d08/vulnerable_e2e.py d08/secure_e2e.py d08/gap_analysis.py ./

# 기본 실행: 세 Lab을 순서대로 실행. Docker는 mock 전용 정책이라 Lab 1·2의
# CMD에 --mock을 명시한다(실제 모델 검증은 로컬 venv에서 진행, Lab 3은
# 원래 실제 모델 호출이 없다).
# 하나만 실행하려면: docker run <image> python gap_analysis.py
CMD ["sh", "-c", "python vulnerable_e2e.py --mock && echo '========================================' && python secure_e2e.py --mock && echo '========================================' && python gap_analysis.py"]
