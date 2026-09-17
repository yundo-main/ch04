# ch04/d07 Canary Token 활용 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/d00-shared 의 공용 모듈(local_llm.py)을 함께
# COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# prompts.py는 d07 로컬 복사본을 쓴다.
# documents.json은 d07 로컬 복사본을 쓴다(d00-shared 공유 없음). ch04/ 에서:
#   docker build -f d07/Dockerfile -t canary-token-demo .
FROM python:3.12-slim

WORKDIR /app

COPY d00-shared/local_llm.py ./
COPY d07/documents.json d07/prompts.py d07/canary_mock.py d07/real_llm.py d07/canary_placement.py d07/response_canary_scanning.py d07/exfiltration_simulation.py ./

# 기본 실행: 세 예제를 순서대로 실행. Docker는 mock 전용 정책이라 예제
# 2·3의 CMD에 --mock을 명시한다(실제 모델 검증은 로컬 venv에서 진행,
# 예제 1은 원래 실제 모델 호출이 없다).
# 하나만 실행하려면: docker run <image> python response_canary_scanning.py --mock
CMD ["sh", "-c", "python canary_placement.py && echo '========================================' && python response_canary_scanning.py --mock && echo '========================================' && python exfiltration_simulation.py --mock"]
