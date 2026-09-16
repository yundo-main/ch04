# ch04/d02 jailbreak 방어 전략 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
#
# 빌드 컨텍스트 주의: ch04/shared 의 공용 모듈(local_llm.py, prompts.py)을
# 함께 COPY 해야 하므로, 빌드 컨텍스트는 이 폴더가 아니라 ch04/ 루트다.
# ch04/ 에서:
#   docker build -f d02/Dockerfile -t jailbreak-defense-demo .
FROM python:3.12-slim

WORKDIR /app

COPY shared/local_llm.py shared/prompts.py ./
COPY d02/jailbreak_mock.py d02/real_llm.py d02/persona_jailbreak.py d02/escalation_jailbreak.py d02/encoding_jailbreak.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python persona_jailbreak.py
CMD ["sh", "-c", "python persona_jailbreak.py && echo '========================================' && python escalation_jailbreak.py && echo '========================================' && python encoding_jailbreak.py"]
