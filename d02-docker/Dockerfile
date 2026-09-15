# ch04/d02-docker jailbreak 방어 전략 예제 실행용 이미지.
# 외부 의존성 없음(표준 라이브러리만 사용) — API 키/시크릿 불필요.
FROM python:3.12-slim

WORKDIR /app

COPY jailbreak_mock.py persona_jailbreak.py escalation_jailbreak.py encoding_jailbreak.py ./

# 기본 실행: 세 예제를 순서대로 실행.
# 하나만 실행하려면: docker run <image> python persona_jailbreak.py
CMD ["sh", "-c", "python persona_jailbreak.py && echo '========================================' && python escalation_jailbreak.py && echo '========================================' && python encoding_jailbreak.py"]
