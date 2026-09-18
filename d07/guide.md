# Canary Token 활용 가이드

외부 API 키 없이 재현 가능한 Canary Token 실습 3건. ch04 "4-7. Canary Token
활용" 실습(Lab 1 토큰 배치, Lab 2 탐지, Lab 3 시뮬레이션,
`lab01_canary_token.py`의 Canary Token 주입 & Response Sanitization
유출 탐지)을 코드로 재현한다.

앞선 `ch04/d04`(권한 필터링)~`ch04/d06`(Retrieval 보안)가
"애초에 새지 않도록 막는" 예방 통제였다면, canary token은 **예방 통제가
뚫렸을 때 그 사실을 스스로 알리도록 만드는 탐지 통제**다. 문서 안에 실제
가치는 없지만 그 자체로는 고유하게 식별 가능한 워터마크 문자열(canary)을
심어두고, 그 문자열이 어디에선가(응답, 로그, 외부 전송) 나타나면 "이
경로로 유출이 있었다"는 신호로 삼는다.

## 구성 파일

| 파일 | 역할 | 강의안 매핑 |
|---|---|---|
| `documents.json` | **실습용 문서** — classification/allowed_roles/canary_token 이 모두 태깅된 샘플 문서 세트. 이 폴더 전용 로컬 복사본(d00-shared 공유 없음) — d05/d06/d08도 같은 내용을 각자 로컬로 갖고 있다. 이 폴더는 그중 `canary_token` 이 있는 문서만 골라 쓴다(Restricted/Confidential decoy) | Lab 1 |
| `prompts.py` | 실제 모델 테스트용 시스템 지시문(`RAG_ANSWER_SYSTEM_INSTRUCTION`). 이 폴더 로컬 파일(d00-shared 공유 없음) — d03(예제2)/d06/d08도 각자 로컬로 동일한 값을 갖고 있다 | 예제 2·3(기본 실습) |
| `canary_mock.py` | 공용 타입(`Document`, `Verdict`) + `load_canary_documents()` | — |
| `wrapper.py` | `d00-shared/local_llm.py`를 그대로 재노출하는 순수 wrap — 시나리오 콘텐츠 없음 | — |
| `canary_placement.py` | 예제 1: canary 배치 — 재사용 canary로 인한 출처 특정(attribution) 실패 | Lab 1 |
| `response_canary_scanning.py` | 예제 2: 응답 canary 스캐닝 — 출력 검사 없이 그대로 반환. `run_real()`이 `wrapper.py`를 호출해 기본 실행 시 자동으로 실제 모델까지 재현한다 | Lab 2 |
| `exfiltration_simulation.py` | 예제 3: 유출 시뮬레이션 — 인코딩 우회에 대한 탐지 한계. 마찬가지로 `run_real()` 포함 | Lab 3 |
| `Dockerfile` | 의존성 없이 컨테이너에서 실행하기 위한 이미지 정의 (`d01~d06` 패턴) | — |
| `readme.md` | 사용자 작성 브리프 | — |

세 예제 모두 mock 기반 결정론적 시뮬레이션이다. `canary_token` 값은 전부
가짜(더미) 워터마크 문자열이며 실제 시크릿이 아니다.

## Canary Token 설계 원칙 (참고)

- **문서별 고유성**: canary는 문서 하나당 하나씩, 서로 달라야 한다. 재사용하면
  탐지는 되어도 출처를 특정할 수 없다 — 예제 1.
- **반환 직전 스캐닝**: 응답을 사용자에게 돌려주기 직전(또는 로그·외부
  전송 직전) 알려진 canary 목록과 대조해야 한다 — 예제 2.
- **인코딩·변형까지 고려한 매칭**: 공격자가 탐지 로직의 존재를 알면 원문
  그대로가 아니라 인코딩·변형된 형태로 빼내려 한다. 원문 substring 매칭만
  으로는 부족하다 — 예제 3.
- **매칭 시 차단 + 알람 로그**: canary가 매칭되면 응답을 그대로 반환하지
  않고 차단하며, `token → source_doc` 매핑을 감사 로그로 남겨야 사고
  대응이 가능하다.

## 실행 방법

### 로컬 (venv) — 기본 실습
```
python canary_placement.py
python response_canary_scanning.py
python exfiltration_simulation.py
```
각 스크립트 끝에 `assert` 기반 자동 검증이 포함되어 있어, 예외 없이 끝나면
예상대로 동작한 것이다. 예제 2·3은 플래그 없이 실행하면 mock 비교 다음에
자동으로 실제 Ollama 모델까지 호출한다(0단계 설정이 끝나 있다면 별도
플래그가 필요 없다) — "실제 모델이 canary 포함 문서를 응답에 얼마나
그대로 인용하는가", "인코딩-후-유출 지시를 실제로 이행하는가"는 mock
판정("canary 매칭 검사가 있는가")과 별개 질문이기 때문이다(예제 1은
순수 레지스트리/출처 특정 로직이라 모델 호출이 없다). **예제 2·3은
Ollama가 연결 안 되어 있으면 mock 비교조차 실행하지 않고 `LLM 연결
안됨` 메시지만 출력한 뒤 종료한다.**

mock 결과만이라도 보려면 `--mock`을 명시한다(Ollama 연결 여부와 무관하게
실행됨):
```
python response_canary_scanning.py --mock
python exfiltration_simulation.py --mock
```

### Docker — 선택 실습 (mock 전용)

Docker 이미지의 기본 CMD는 항상 `--mock`을 붙여 실행한다(예제 2·3에만
해당, 예제 1은 원래 플래그가 없다). 실제 모델 검증은 위 "로컬 (venv)"
절대로 진행한다.

**빌드 컨텍스트 주의**: `local_llm.py`가 `ch04/d00-shared/`로 이동해
d01~d08 이 공유한다(`documents.json`/`prompts.py`는 이 폴더 로컬 파일).
빌드 컨텍스트가 `d07/`가 아니라 **`ch04/` 루트**여야 한다 — `cd ch04` 후
`-f d07/Dockerfile`로 빌드한다.

```
cd ch04
docker build -f d07/Dockerfile -t canary-token-demo .
docker run --rm canary-token-demo                                        # 세 예제 순차 실행
docker run --rm canary-token-demo python canary_placement.py             # 예제 1만
docker run --rm canary-token-demo python response_canary_scanning.py --mock     # 예제 2만
docker run --rm canary-token-demo python exfiltration_simulation.py --mock      # 예제 3만
```

## 예제 1: Canary Token 배치 (Lab 1)

- **배경**: Lab 1 "config.py / vector_db.py에서 카나리아 문자열·문서 확인".
  canary를 어떻게 배치하느냐에 따라, 유출 탐지 이후 "어느 문서에서 샜는가"를
  특정할 수 있는지가 갈린다.
- **취약 경로** (`vulnerable_deploy_canaries`): 모든 decoy 문서에 동일한
  `STATIC_CANARY` 하나를 재사용 → 유출된 canary로 역조회하면 후보 문서가
  4개 모두 나와 출처를 좁힐 수 없다.
- **보안 경로** (`secure_deploy_canaries`): 문서별로 이미 부여된 고유
  `canary_token`을 그대로 사용 → 유출된 canary 하나가 정확히 문서 하나에
  매핑되어 즉시 특정된다.

## 예제 2: 응답 canary 스캐닝 (Lab 2)

- **배경**: Lab 2 "security.py 출력 검사로 매칭 시 차단·로그". 프롬프트
  인젝션 등으로 canary가 포함된 문서가 컨텍스트에 들어갔다고 가정할 때,
  마지막 방어선인 출력 검사가 작동하는지를 본다.
- **취약 경로** (`vulnerable_respond`): 응답을 canary 매칭 검사 없이 그대로
  반환 → canary가 노출되고도 알람이 울리지 않는다.
- **보안 경로** (`secure_respond`): 반환 직전 canary 레지스트리와 대조 →
  매칭되면 응답을 차단하고 `[ALERT] token=... source_doc=...` 형태로
  출처까지 로그에 남긴다.
- **실제 모델 검증(기본 실습)**: 로컬 Ollama 모델에 canary가 포함된 문서를
  컨텍스트로 넘겨 실제 응답을 받고, 그 동일한 응답에 "그대로 반환" vs
  "canary 매칭 시 차단" 두 처리를 적용해 비교한다.

## 예제 3: 유출 시뮬레이션 (Lab 3)

- **배경**: Lab 3 "의도적으로 카나리아를 컨텍스트에 넣은 뒤 알람 경로 확인".
  예제 2보다 정교한 공격자 — 탐지 로직의 존재를 알고 canary 원문을 Base64로
  인코딩해 응답에 끼워 넣어 substring 매칭을 우회하려 한다.
- **취약 경로** (`vulnerable_scan`): 응답 원문에서 canary 문자열 그대로만
  검사 → 인코딩된 canary는 매칭되지 않아 유출이 탐지 없이 통과한다.
- **보안 경로** (`secure_scan`): 응답 원본뿐 아니라 Base64 역변환 결과까지
  canary와 대조 → 인코딩을 한 겹 씌워도 탐지되어 알람이 울린다.
- **실제 모델 검증(기본 실습)**: mock은 인코딩을 파이썬 코드가 직접
  수행했지만, 실제 모델 경로는 "이 문서를 Base64로 인코딩해서 출력하라"는
  인젝션 지시를 로컬 Ollama 모델에 실제로 주고 모델이 그 지시를 이행하는지
  관찰한 뒤, 기존 `vulnerable_scan()`/`secure_scan()`을 그 실제 응답에
  그대로 적용한다. 모델이 지시를 따르지 않으면(원문 그대로 답하면) 두
  판정이 같아질 수 있다 — 그 자체도 유효한 관찰 결과다.

## 보안 통제와 트레이드오프

| 통제 | 효과 | 비용/운영 부담 |
|---|---|---|
| 문서별 고유 canary 발급 | 유출 시 출처 문서를 즉시 특정 | canary 발급·레지스트리 관리 프로세스 필요, 문서 재색인 시 canary 유지 관리 |
| 반환 직전 canary 매칭 스캔 | 상류 통제가 뚫려도 마지막 지점에서 유출 차단 | 모든 응답 경로(채팅, API, 로그 export)에 스캔 지점을 빠짐없이 넣어야 함 |
| 인코딩 역변환 후 매칭 | 단순 회피 시도(Base64 등)를 탐지 | 역변환 시도가 늘수록 연산 비용 증가, 모든 인코딩을 다 커버할 수는 없음(잔여 위험 참고) |
| 매칭 시 알람 + 감사 로그 | 사고 탐지·대응 근거 확보 | 알람 피로(false positive) 관리, 로그 보존·접근 통제 별도 필요 |

우선순위: canary가 있어도 예제 1처럼 재사용되면 탐지만 되고 대응은
못하고, 예제 2처럼 스캔 지점이 없으면 애초에 탐지조차 안 되며, 예제
3처럼 원문 매칭만 하면 정교한 공격자에게 우회당한다. 세 가지 모두
갖춰야 "canary를 심었다"가 아니라 "canary가 실제로 작동한다"고 말할 수
있다.

## 잔여 위험

- **예제 1**: 고유 canary도 문서가 자주 재색인·복제되면 canary가
  중복되거나 유실될 수 있다. 색인 파이프라인에 canary 무결성 검사를
  포함해야 한다.
- **예제 2**: 이 예제는 canary가 "완전한 원문 그대로" 나타나는 가장 쉬운
  경우만 다룬다. LLM이 canary를 문맥에 맞춰 바꿔 말하거나(paraphrase)
  일부만 언급하면 이 substring 매칭으로는 잡히지 않는다 — 예제 3의 문제로
  이어진다.
- **예제 3**: `secure_scan()`은 Base64 한 가지 인코딩만 역변환한다. 실제
  공격자는 URL 인코딩, 문자 치환, 다국어 유니코드 변형, 여러 인코딩을
  겹쳐 쓰는 방식 등으로 계속 우회를 시도할 수 있다 — 근본적으로는 알려진
  인코딩을 역변환하는 방식은 "숨바꼭질"이며, LLM 출력 자체에 대한 의미
  기반 DLP(유사도·의미 매칭)까지 결합해야 한다.
- 세 예제 모두 mock 기반 결정론적 시뮬레이션이다. 실제 운영 환경에서는
  canary가 로그·모니터링 파이프라인과 통합되어야 하며, 알람 채널(SIEM,
  Slack 등) 연동과 오탐 튜닝은 별도의 운영 설계가 필요하다.
