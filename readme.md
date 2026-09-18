# ch04 정책

## 문서 규칙

- 각 일차 디렉터리(`d01`~`d08`)와 `d00-shared/`는 **`guide.md` 하나만** 문서로 둔다.
  그 외 별도 문서 파일(설계 노트, README 등)은 작성하지 않는다.
- 각 디렉터리의 `readme.md`(사용자 작성 브리프)는 이 규칙의 예외다 — 사용자
  본인 계획 공간이며 Claude가 작성하는 `guide.md`와는 별개다.
- `plan.md`는 더 이상 쓰지 않는다. `d01/plan.md`는 과거 기록으로만 남겨두고
  (git에는 올리지 않음), 그 자리는 다른 디렉터리와 동일하게 `readme.md`로
  대체했다.

## d00-shared/ — 0단계 (수업 시작점, d01~d08 공유)

여러 디렉터리가 거의 동일한 파일을 각자 복사해 갖고 있던 것을 하나로 모은
공용 디렉터리다. 각 디렉터리는 필요한 파일만 골라 참조하며, 로컬(venv)
실행 시에는 `sys.path`로, Docker 실행 시에는 빌드 시점에 같은 디렉터리로
평탄화(COPY)해서 찾는다. **단, `documents.json`과 `prompts.py`는 여기
없다** — d01~d08 전부가 각자 자기 폴더에 로컬 복사본을 갖고 쓴다(아래
"변경이력" 참고).

**수업은 여기서 시작한다**: d01에 들어가기 전에 이 디렉터리 기준으로 Ollama
설치·모델 pull을 먼저 끝낸다 — 아래 각 dNN/guide.md의 "실제 모델(Ollama)
실행 — 기본 실습" 단계가 이 사전 설정을 전제로 한다.

| 파일 | 역할 |
| --- | --- |
| `local_llm.py` | 실제 로컬 Ollama 모델을 호출하는 클라이언트. 각 챕터의 메인 스크립트가 **직접** import 한다(챕터별 wrapper 파일 없음) — 로컬(venv)에서는 플래그 없이도 기본으로 호출된다(`--mock`이면 건너뜀) — **기본 실습 경로(로컬 venv 전용)**. Docker 실습은 mock 전용 정책이라 이 파일의 네트워크 호출 자체가 컨테이너 안에서 쓰이지 않는다(COPY되는 건 각 스크립트의 import 요구 때문). |
| `mock_llm.py` | 규칙 기반 mock LLM 엔진. API 키나 외부 서비스 없이 항상 동일하게 재현되는 결정론적 판정을 담당(assert 자동 검증의 기준선). **Ollama 미연결 시 자동으로 대체 실행되지 않는다** — 플래그 없이 실행하면 Ollama가 없을 때 `LLM 연결 안됨` 메시지만 뜨고 mock도 생략되며, mock만 보려면 `--mock`을 명시해야 한다. |
| `smoke_test.py` | `mock_llm.py`/`local_llm.py` 단독 동작 확인용 진단 스크립트 — `python smoke_test.py`로 0단계 설정이 끝났는지 검증한다(Ollama 미연결 시 해당 부분만 `SKIP`). |
| `guide.md` | 위 공유 구조, Ollama 설치/모델 pull 절차, sys.path/Docker 평탄화 메커니즘에 대한 상세 설명. |

`prompts.py`는 d01~d08 각자 로컬 복사본을 쓴다(d01/d02/d03/d06/d07/d08 —
d04/d05는 프롬프트 텍스트 자체가 없다). `RAG_ANSWER_SYSTEM_INSTRUCTION`처럼
d03(예제2)/d06/d07/d08 네 곳이 똑같이 쓰는 상수도 각자 로컬 파일에
동일한 값으로 중복해서 넣는다. 왜 d00-shared 공유를 그만뒀는지는 아래
"변경이력" 절 참고.

## 각 일차 디렉터리

| 디렉터리 | 주제 |
| --- | --- |
| `d00-shared` | 0단계: LLM 환경 설정 (위 절 참고) |
| `d01` | 프롬프트 인젝션 (직접/간접) |
| `d02` | Jailbreak 방어 전략 |
| `d03` | LLM 데이터 유출 위험 |
| `d04` | RAG 권한 필터링 설계 |
| `d05` | 문서 보안 등급 체계 설계 |
| `d06` | Retrieval 보안 구현 |
| `d07` | Canary Token 활용 |
| `d08` | End-to-End 보안 통합 |

각 디렉터리는 3개 예제(또는 Lab) + 공용 mock 타입 + `Dockerfile` + `readme.md`
(사용자 브리프) + `guide.md`(상세 설명) 구성을 따른다(`d00-shared`는 예제/Lab
대신 공유 모듈 + 0단계 설정 절차로 구성됨).

## Docker 관련 (선택 실습)

- 기본 실습 경로는 로컬(venv) + 실제 Ollama 모델 실행이다(플래그 없이 기본
  실행, `--mock`이면 건너뜀). Docker는 CMD에 `--mock`을 명시해 항상
  mock만 재현하는 선택 실습이다.
- 디렉터리별로 실습용 이미지를 **별도로** 빌드한다(하나로 합치지 않는다).
- 단, `d00-shared/`의 파일을 `COPY`해야 하므로 **빌드 컨텍스트는 항상 `ch04/`
  루트**다 — 각 디렉터리 안에서 `docker build .`로 빌드하던 방식은 더 이상
  쓸 수 없다.
  ```
  cd ch04
  docker build -f d01/Dockerfile -t <이미지명> .
  ```
- 정확한 이미지명/실행 명령은 각 디렉터리의 `guide.md`를 따른다.

## 변경이력

### prompts.py 이름 충돌 — local_prompts.py를 썼다가 그만둔 이유

한때 d02/d03은 "로컬 전용 프롬프트도 있고, 그중 일부는 d00-shared 상수
(`SAFETY_POLICY_PREFIX`, `RAG_ANSWER_SYSTEM_INSTRUCTION`)를 가져와 조합도
해야 하는" 상태였다. 그때는 로컬 파일 이름을 `prompts.py`로 두면 안 됐다 —
두 가지 문제가 동시에 났다: (1) 로컬 `prompts.py` 안에서
`from prompts import ...`를 쓰면 자기 자신을 다시 가져오는 Python 순환
참조가 나고, (2) Docker 빌드 시 `COPY d00-shared/prompts.py ./`와
`COPY d02/prompts.py ./`가 이미지 안의 같은 경로(`/app/prompts.py`)를
가리켜서 나중 COPY가 앞선 걸 덮어써버렸다. 그래서 로컬 파일을
`local_prompts.py`로 이름 지어 우회했다.

그 뒤 한동안 "중복 여부와 무관하게 모든 프롬프트를 d00-shared로 모은다"는
원칙으로 바뀌어서 d01~d03 어디에도 로컬 prompts 파일이 없던 시기가
있었다. **지금은 아래 "prompts.py — d00-shared 공유를 완전히 그만둠"
항목대로 반대 방향으로 다시 바뀌어서, d00-shared/prompts.py 자체가
없다** — 그래서 이 절이 설명하는 이름 충돌 문제(로컬 `prompts.py`와
d00-shared `prompts.py`가 같은 이름으로 부딪히는 문제) 자체가 구조적으로
발생할 수 없다.

### shared → d00-shared 리네임 + 0단계 매뉴얼화

`shared/` 디렉터리를 `d00-shared/`로 리네임하고, d01에 들어가기 전 "0단계:
LLM 환경 설정"으로 자리잡도록 `guide.md`에 Ollama 설치/서버 실행/모델
준비/저사양 대안 모델/트러블슈팅을 정리했다. 함께 정책을 하나 확정했다:
**Ollama(실제 모델)는 로컬(venv)에서만 쓰고, Docker 실습은 mock 전용이다**
— 각 dNN `guide.md`에서 "Docker에서 `--real` 실행 시" 관련 절을 전부
제거했다.

### --real → --mock: 플래그 기본값 전환

기존에는 `python direct_injection.py`(플래그 없음) = mock만, `--real` =
mock + 실제 모델 추가 호출이었다. 이를 뒤집었다 — `real_llm.py`가 있는
모든 스크립트(d01/d02/d03/d06 일부/d07 일부/d08 일부, 총 13개 파일)의
`if "--real" in sys.argv:` 게이트를 `if "--mock" not in sys.argv:`로
바꿔서, **로컬(venv)에서는 플래그 없이 실행해도 mock + 실제 모델이 둘 다
자동으로 돈다.** `--mock`을 주면 실제 모델 호출을 건너뛰고 mock만 본다.
Docker 이미지의 CMD는 전부 `--mock`을 명시하도록 각 `Dockerfile`을
수정했다 — Docker 실습이 실제로 mock 전용이 되도록 강제한 것이다(이전
에는 "Docker는 원래 `--real`을 안 줘서 우연히 mock만 나왔던" 상태였다).

### documents.json — d00-shared 공유를 그만두고 챕터별 로컬 복사본으로 되돌림

d05~d08은 `d00-shared/documents.json`(8개 문서, classification/
allowed_roles/canary_token 태깅) 하나를 공유했었다. d01의 `documents.json`
(3개 문서, `{doc_id, text}`만 있는 인젝션 데모용)도 여기에 합쳐서 "전부
공유"하는 방향을 검토했지만, d05의 로더가 문서마다
`doc["classification"]`을 무조건 조회(`.get()`이 아니라 대괄호 접근)하기
때문에 `classification` 필드가 없는 d01 스타일 문서를 하나라도 섞으면
d05~d08 전부가 `KeyError`로 즉시 깨진다는 걸 확인했다(실제로 재현해서
검증함). 스키마 통일(d01 문서에 의미 없는 RBAC 필드를 채워 넣기) 대신,
**반대 방향으로 결정** — d05/d06/d07/d08 각자에게 `documents.json` 로컬
복사본을 만들어주고, `d00-shared/documents.json` 자체를 삭제했다. 각
로더의 `shared_candidate`(d00-shared 우선 탐색) 분기도 제거해서 이제
전부 자기 폴더만 본다. d08은 원래 "d04/d05/d07 통제를 모두 갖춘 통합
세트"라는 전제로 설계돼 있어서, 4개 로컬 복사본은 전부 리네임 시점
기준 동일한 내용으로 맞춰뒀다 — 이후 한 챕터에서만 문서를 고치면 다시
드리프트가 생긴다는 잔여 위험은 `d00-shared/guide.md`에 기록해뒀다.

### prompts.py — d00-shared 공유를 완전히 그만둠

`documents.json`과 같은 이유로, `prompts.py`도 d00-shared 공유를 그만두고
d01/d02/d03/d06/d07/d08 각자 로컬 `prompts.py`로 나눴다(d04/d05는
프롬프트 텍스트 자체가 없어서 해당 없음). 계기: d01의 실제 모델(`--real`)
테스트 프롬프트를 영어로 바꿔보는 실험을 하다가, "mock용 한국어 상수와
실제 모델용 텍스트가 같은 파일에 섞여 있어서 헷갈린다"는 피드백을 받았다.
문서 재분배 방식은 `documents.json` 때와 동일하다 — 각 디렉터리가 실제로
쓰는 상수만 추려서 로컬 `prompts.py`에 넣고, `d00-shared/prompts.py`
자체를 삭제했다. 유일하게 여러 챕터가 공유하던 상수 `RAG_ANSWER_SYSTEM_
INSTRUCTION`(d03 예제2/d06/d07/d08)은 4개 로컬 파일에 동일한 값으로
중복 배치했다 — `documents.json`과 마찬가지로 이후 드리프트 위험이
`d00-shared/guide.md`에 기록돼 있다. `local_llm.py`/`mock_llm.py`는
계속 d00-shared에서 공유한다(변경 없음) — Ollama 클라이언트/mock 엔진은
챕터 간 진짜 동일 코드라 이 재분배 대상이 아니다.

### Ollama 미연결 시 mock 자동 폴백 제거 — "LLM 연결 안됨"으로 명시

기존에는 `--mock` 없이 실행하면 mock 비교(취약/보안 대조, `assert` PASS)
가 Ollama 연결 여부와 무관하게 항상 먼저 실행되고, 그 다음 실제 모델
호출을 시도했다 — 연결이 안 되면 그 시점에만 안내 메시지를 찍고
끝났다. 이게 "mock으로 조용히 폴백된다"는 인상을 줘서, 실제로는 무슨
일이 일어났는지(연결이 안 됐다는 것)가 mock의 PASS 출력에 묻혔다.
`real_llm.py`가 있는 13개 스크립트 전부의 `main()` 맨 앞에 게이트를
추가했다 — `--mock`이 없고 Ollama도 연결 안 되어 있으면 mock 비교 자체를
실행하지 않고 `LLM 연결 안됨: Ollama 서버(...)에 연결할 수 없습니다.`
한 줄만 출력하고 종료한다. `run_real()` 안에 있던 중복된
`is_ollama_available()` 체크(및 그 안의 `brew install ollama...` 안내
문구)는 이제 `main()`에서 먼저 걸러지므로 전부 제거했다. `--mock`은
그대로 Ollama 연결 여부와 무관하게 항상 동작한다 — Docker CMD가 전부
`--mock`을 쓰므로 이 변경으로 Docker 실습은 영향받지 않는다.

### DEFAULT_MODEL 탐색: llama3.2:1b → qwen2.5:0.5b → tinyllama → exaone3.5:2.4b

실제 모델 실습에 쓸 기본 모델을 여러 번 바꿔가며 실측했다. 순서대로:

1. **`llama3.2:1b`(최초 기본값)**: instruct 튜닝 + 안전 정렬이 있어서, d01의
   단순 인젝션 문구엔 대부분 저항한다 — 취약 경로 재현이 잘 안 됨.
2. **`qwen2.5:0.5b`(저사양 대안으로 도입)**: 한국어 응답은 가능하지만
   인젝션에 걸리거나 엉뚱한 무판정 응답을 내는 경우가 뒤섞여 나와
   불안정했다.
3. **`tinyllama`**: 취약 경로는 매번 안정적으로 재현됐지만(핵심 목표
   달성), 한국어 학습이 거의 없어 입력이 한국어여도 응답은 항상 영어로
   나왔다. 게다가 `temperature=0.2`가 낮아서 같은 문장을 반복하는 생성
   루프에 종종 빠졌다 — `local_llm.py`의 `temperature`를 0.2 → 0.7로
   올려서 이 반복 루프는 해결했다(재현성은 그만큼 더 흔들림).
4. **`exaone3.5:2.4b`(현재 기본값)**: LG AI연구원의 한국어·영어 이중언어
   모델. 한국어로 자연스럽게 응답하면서 d01/d03/d06에서 취약 경로가
   안정적으로 재현되는 걸 확인했다. 단, **d02(페르소나 탈옥)에서는
   `leaked_secret` 판정이 뒤집히는 사례**를 발견했다 — 취약 경로가 가짜
   코드명을 지어내 유출 판정을 피하고, 보안 경로가 설명 중 실제 코드명을
   언급해 유출 판정을 받는 역설적인 경우다(`d02/guide.md`의 "잔여 위험"에
   기록). 문자열 정확 일치 기반 판정의 한계를 보여주는 사례로 남겨뒀다.

결론적으로 "한국어 응답"과 "인젝션 재현 안정성"을 동시에 만족하는 모델은
아직 못 찾았고, `exaone3.5:2.4b`가 그중 가장 균형 잡힌 선택이었다.

### real_llm.py 경로 전체 제거 — mock 전용 랩으로 전환

위 "DEFAULT_MODEL 탐색" 항목까지는 `--real`(이후 플래그 없이 기본 실행)
경로로 실제 Ollama 모델을 호출해 mock과 비교하는 것이 이 랩의 핵심
설계였다. 그런데 d02(페르소나 탈옥)에서 `leaked_secret` 판정이 모델
할루시네이션 때문에 뒤집히는 사례가 나온 뒤, "판정 로직을 프롬프트로
더 정교하게 다듬어서 안정시키자"는 방향을 검토하는 과정에서 더 근본적인
질문이 나왔다 — 그렇게 프롬프트를 정교화해서 결과를 안정시키면, 그건
"실제 모델이 자연 상태에서 취약한가"를 관찰하는 게 아니라 "우리가 원하는
답이 나오도록 프롬프트로 유도"하는 것이 되어 mock과 실질적으로 같아진다는
점이었다. 이 논의 끝에 **real_llm.py 경로 자체를 6개 챕터
(d01/d02/d03/d06/d07/d08) 전부에서 제거**하기로 결정했다 — 판정을
정교화하는 대신, "실제 모델은 비결정적이라 mock과 다른 결과가 나올 수
있다"는 사실 자체를 랩의 범위 밖(mock 기반 결정론적 시뮬레이션이라는
한계)으로 명시하는 쪽을 택한 것이다.

구체적으로 제거된 것:
- 6개 챕터의 `real_llm.py` 전부 삭제, 각 스크립트의 `run_real()`/
  `--mock` 플래그 분기/`is_ollama_available()` 게이트 전부 제거 — 모든
  스크립트가 플래그 없이 mock 경로만 실행한다.
- `d00-shared/local_llm.py`(Ollama HTTP 클라이언트), `d00-shared/
  smoke_test.py` 삭제 — 소비하는 코드가 없어졌다.
- `d02/d03/d06/d07/d08`의 `prompts.py` 중 real 경로 전용으로만 쓰이던
  상수(`d02`의 `real_llm.py` 전용 시나리오, `RAG_ANSWER_SYSTEM_
  INSTRUCTION`)가 죽은 코드가 되어, `d06/d07/d08`은 `prompts.py` 자체를
  삭제했다(d03은 `RAG_ANSWER_SYSTEM_INSTRUCTION`만 제거하고 파일은 유지).
- d02/d06/d07/d08은 이제 d00-shared 의존성이 전혀 없다(d01만 `mock_llm.py`
  공유가 남음). Dockerfile들도 `d00-shared/local_llm.py` COPY와 `--mock`
  CMD 인자를 제거했다 — 다만 빌드 명령 규칙(빌드 컨텍스트 = `ch04/`
  루트)은 d01과의 일관성을 위해 그대로 유지했다.
- `d00-shared/guide.md`의 "0단계: LLM 환경 설정"(Ollama 설치/모델 pull/
  DEFAULT_MODEL 비교표), 각 dNN `guide.md`의 "실제 모델 검증(기본 실습)"
  절과 "Docker — 선택 실습(mock 전용)" 구분을 전부 제거했다 — 이제
  로컬(venv)과 Docker 실행은 동일한 결과를 낸다.

**잔여 위험(승계)**: 위 항목들에서 "실제 모델은 비결정적이다" / "mock
판정이 실제 모델의 취약성을 보장하지 않는다"는 잔여 위험 문구는 각
dNN `guide.md`에 여전히 남아 있다 — 실제 모델 호출 경로가 없어졌다고
그 경고 자체가 무의미해지는 게 아니라, 오히려 "이 랩은 mock 만으로는
확인 안 되는 부분이 있다"는 한계를 더 명확히 드러내는 쪽으로 문구를
다듬었다.

### real_llm.py 복원 — 단, wrapper 없이 직접 호출하는 구조로

바로 위 항목("real_llm.py 경로 전체 제거")을 실행에 옮긴 직후, 원래
의도가 "mock으로 전환해달라"가 아니라 "real_llm.py *wrapper 구조* 없이
실제 LLM으로 실습하게 해달라"는 것이었음을 확인했다 — mock 전환은
질문("wrap을 왜 하냐")에 대한 과도한 해석이었다. 그래서 실제 모델 호출
자체는 되살리고, 없앤 것은 **`script → real_llm.py → local_llm.py`로
이어지는 2단 간접화**만이다.

구체적으로 되살린 것과 그대로 유지한 것:
- `d00-shared/local_llm.py`(Ollama HTTP 클라이언트), `d00-shared/
  smoke_test.py` 복원. `DEFAULT_MODEL=exaone3.5:2.4b`, `temperature=0.7`
  등 이전 세션에서 실측으로 정한 값을 그대로 유지했다.
- 6개 챕터(d01/d02/d03/d06/d07/d08) 각각의 메인 스크립트가 `d00-shared/
  local_llm.py`를 **직접** import 한다 — 챕터 전용 `real_llm.py`는
  되살리지 않았다. 예전에 `real_llm.py`에 있던 시나리오 구성 함수
  (`persona_jailbreak_real()` 등)와 판정 로직은 각 스크립트 자신의
  `run_real()` 함수 안으로 그대로 옮겼다.
- d02는 세 스크립트(persona/escalation/encoding)가 `SECRET_CODENAME`/
  `BASE_SYSTEM_INSTRUCTION`을 각자 로컬로 동일하게 중복 보유한다 — 예전엔
  `d02/real_llm.py` 하나에 모아뒀던 것을 wrapper 없이 가져오면서 생긴
  트레이드오프다(드리프트 위험은 `d00-shared/guide.md`에 기록).
- d06/d07/d08의 `prompts.py`(`RAG_ANSWER_SYSTEM_INSTRUCTION`)도 복원했다.
- `--mock`/`is_ollama_available()` 게이트, Docker CMD의 `--mock`, 각
  `guide.md`의 "기본 실습(로컬+실제 모델)"/"선택 실습(Docker, mock
  전용)" 구분을 전부 되돌렸다 — "real_llm.py 경로 전체 제거" 항목 이전
  상태와 동작은 동일하고, 파일 구조만 한 계층 얕아졌다.

**검증**: 이 세션에서 실제로 Ollama 서버가 떠 있는 환경이었어서, 복원한
13개 스크립트 전부를 플래그 없이(실제 모델 경로) 한 번씩 실행해 정상
동작을 확인했다 — d02는 이전에 기록된 `leaked_secret` 판정 역전 사례가
그대로 재현됐고, d06은 `sanitize_chunk()`가 마커만 지우고 명령 본문은
남겨서 실제 모델이 잔존 지시를 따르는 사례도 재현됐다.

### real_llm.py 재도입 — 순수 wrap으로만, 시나리오 콘텐츠는 계속 스크립트에

바로 위 항목("real_llm.py 복원")에서 `real_llm.py` 자체는 없애고
`d00-shared/local_llm.py`를 메인 스크립트가 직접 import하는 구조로
갔었다. 대화를 더 나눠본 결과, "wrap을 왜 없앴냐"는 질문의 실제 취지는
"wrap과 시나리오 콘텐츠가 한 파일에 섞여 있던 것"에 대한 문제 제기였고,
"real_llm.py라는 이름의 파일 자체"를 없애자는 뜻은 아니었다. 그래서
6개 챕터(d01/d02/d03/d06/d07/d08) 전부에 `real_llm.py`를 다시 만들었다 —
단, 이번엔 역할을 명확히 좁혔다:

- `real_llm.py` = **순수 wrap**. `d00-shared/local_llm.py`의
  `DEFAULT_MODEL`/`chat_messages`(또는 `ask_real`)/`is_ollama_available`을
  그대로 재노출하고, `sys.path.append` 상용구를 담을 뿐이다. 시나리오
  콘텐츠(공격 프롬프트, `SECRET_CODENAME` 등)는 **여기 없다**.
- 시나리오 콘텐츠 + `run_real()` 호출부는 계속 메인 스크립트에 있다 —
  "real_llm.py 경로 전체 제거"/"real_llm.py 복원" 두 항목에서 옮겨둔
  위치 그대로 유지했다.
- 메인 스크립트는 `local_llm`이 아니라 `real_llm`을 import 한다. d02처럼
  d00-shared 의존성이 로컬 mock 타입만 있던 챕터(d02/d03/d06/d07/d08)는
  `real_llm.py`가 `sys.path.append`를 전담하므로, 메인 스크립트에서
  그 상용구(`sys.path.append`/`from pathlib import Path`)를 제거했다 —
  파일이 그만큼 짧아졌다. d01은 `mock_llm.py`도 d00-shared에서 가져오므로
  메인 스크립트의 `sys.path.append`를 그대로 유지했다.
- Dockerfile들도 각 챕터의 `real_llm.py`를 COPY 목록에 추가했다.

**핵심 구분(반복해서 확인한 원칙)**: wrap은 "어떻게 전송하는가"만 알고
"무엇을 보내는가"는 몰라야 한다. `real_llm.py`에 `SECRET_CODENAME` 같은
콘텐츠를 넣으면 이 원칙이 깨진다 — 그래서 d02의 세 스크립트(persona/
escalation/encoding)는 `SECRET_CODENAME`을 `real_llm.py`가 아니라 각자
로컬로 중복해서 갖고 있다(드리프트 위험은 `d00-shared/guide.md`에
기록). 검증: 6개 챕터 13개 스크립트 전부 `--mock`/실제 모델 양쪽 경로로
재실행해 정상 동작 확인.

### d02의 SECRET_CODENAME 중복 제거 — prompts.py로 이동 + 용어 정리

바로 위 항목에서 "d02 세 스크립트가 `SECRET_CODENAME`을 각자 중복
보유"를 잔여 위험으로 남겨뒀는데, 이 중복은 `real_llm.py`(wrap)를
건드리지 않고도 없앨 수 있다는 걸 확인해서 정리했다. `d02/prompts.py`에
`REAL_SECRET_CODENAME`/`REAL_BASE_SYSTEM_INSTRUCTION`을 새 섹션("REAL
전용")으로 추가하고, persona/escalation/encoding 세 스크립트는 이제
이 상수를 직접 정의하는 대신 `prompts.py`에서 import 한다. `prompts.py`는
원래도 "콘텐츠만 담고 로직은 없는 파일"이었으므로 새 계층을 만든 게
아니라 기존 계층의 역할을 넓힌 것이다 — `real_llm.py`(전송 wrap)는 여전히
이 콘텐츠를 전혀 모른다.

같이 짚은 용어 문제: "시나리오"라는 말을 이 문서와 코드 주석에서 아키텍처
용어("wrap이 모르는 콘텐츠 전체")로 써왔는데, d02 공격 문구 자체에 이미
"역할극/가상 시나리오"라는 의미로 쓰이고 있어서 겹쳤다. 이후로는 아키텍처
설명에는 "콘텐츠"만 쓰고, "시나리오"는 코드에 원래 있던 뜻(탈옥 기법의
프레이밍 문구)으로만 남겨뒀다.

### d02 run_real()에 출력 게이트 추가 — mock과 동일한 두 겹 방어로

실제 모델로 `persona_jailbreak.py`를 반복 실행하다가, 보안 경로(identity
anchoring)가 "왜 코드명을 알려줄 수 없는지" 설명하는 과정에서 진짜
코드명을 그대로 언급해 `leaked_secret=True`로 잡히는 사례가 실제로
나왔다. 원인을 보니 mock의 `secure_respond()`는 (1) identity anchoring +
(2) 출력 단 하드 게이트, 두 겹 방어인데 `run_real()`은 (1)만 재현하고
있었다 — 애초에 "identity anchoring 하나만으로는 부족하다"는 전제로
mock에 (2)를 넣어둔 것이므로, 이건 새로운 취약점 발견이 아니라 real
경로가 mock이 이미 설계해둔 방어 하나를 빠뜨리고 있었던 것이었다.

세 스크립트(persona/escalation/encoding) 모두의 `run_real()` "보안 경로"
에 출력 게이트를 추가했다 — 응답에 `SECRET_CODENAME`이 있으면 원문을
출력하지 않고 `[차단됨]`으로 대체한 뒤 `[출력 게이트] ... 차단함`을
로그로 남긴다(d07의 canary 스캔과 동일한 패턴). 취약 경로에는 이 게이트를
넣지 않았다 — 취약 경로는 의도적으로 무방비 상태를 보여주는 게 목적이라,
거기에 게이트를 넣으면 "취약"이라는 이름이 무색해진다.

이걸로 판정 역전 잔여 위험의 절반(보안 경로가 실수로 코드명을 언급해서
False positive처럼 True로 잡히는 쪽)은 해소됐다. 나머지 절반(취약 경로가
할루시네이션으로 가짜 코드명을 지어내서 False negative처럼 False로 잡히는
쪽)은 그대로 남아 있다 — 취약 경로에 손대지 않기로 한 결정과 일치한다.
검증: 반복 실행해서 게이트가 실제로 작동하는 사례(`[출력 게이트] 응답에
비밀 코드명이 포함되어 차단함`)를 직접 확인했다.

### 부분 일치 유출 탐지 — SECRET_CODENAME_CORE로 판정 정확도 개선

바로 위 항목에서 "취약 경로의 할루시네이션은 그대로 남는다"고 했는데,
반복 실행하다가 그와는 다른 세 번째 실패 유형을 발견했다: 모델이 완전히
다른 가짜 이름을 지어낸 게 아니라, 진짜 코드명(`PROJECT-NEBULA-7`)에서
흔한 접두사 "PROJECT-"만 빼고 "NEBULA-7"을 그대로 말한 경우다. 사람이
보면 명백히 같은 코드명을 유출한 것인데, `SECRET_CODENAME in text` 전체
문자열 완전일치 판정은 "PROJECT-"가 없다는 이유로 `False`를 냈다 — 이건
할루시네이션(완전히 다른 값을 지어냄)과는 다른, "부분 재현"이라는 별도
실패 유형이었다.

이건 방어를 추가하는 게 아니라 판정(측정) 정확도를 높이는 문제라고 정리해서,
`d02/prompts.py`에 `REAL_SECRET_CODENAME_CORE = "NEBULA-7"`(코드명의 고유
부분만)을 추가하고, 세 스크립트 모두 유출 판정을 `SECRET_CODENAME_CORE.lower()
in text.lower()`로 바꿨다(대소문자·접두사 누락에 영향을 안 받도록). 취약
경로에는 여전히 아무 방어도 안 넣었다 — 판정 로직만 더 정확해졌을 뿐이다.
검증: 반복 실행해서 완전 유출/부분 유출/완전 할루시네이션 세 가지 경우가
각각 True/True/False로 올바르게 갈리는 것을 직접 확인했다.

### real_llm.py → wrapper.py 파일명 변경

지금까지 여러 차례 확인한 것처럼 이 파일은 순수 wrap(전송 재노출, 콘텐츠
없음)이다. "real_llm"이라는 이름은 애초에 "옆의 mock 파일(`jailbreak_mock.py`
등)과 짝을 이루는 이름"이라는 근거로 유지해왔는데, 다시 보니 그 짝 관계가
정확하지 않았다 — mock 쪽 파일은 챕터마다 도메인을 반영한 다른 이름
(`jailbreak_mock.py`/`leakage_mock.py`/`canary_mock.py`/
`retrieval_security_mock.py`)인 반면, 이 파일은 6개 챕터 전부 똑같은
이름·내용(콘텐츠 없는 전송 재노출)이다. 오히려 "6개 챕터가 다 똑같다"는
사실 자체가 "이건 도메인 로직이 아니라 배관(wrap)일 뿐"이라는 신호이므로,
파일 역할을 그대로 이름에 반영해 `real_llm.py` → `wrapper.py`로 바꿨다.

6개 챕터(d01/d02/d03/d06/d07/d08) 전부에서 파일명, `from real_llm import`
→ `from wrapper import`, Dockerfile의 `COPY ... real_llm.py` →
`wrapper.py`, 각 `guide.md`/`d00-shared/guide.md`/`d00-shared/local_llm.py`
헤더 주석의 자기참조를 함께 고쳤다. 동작은 이름만 바뀐 것이므로 변경 없음 —
13개 스크립트 전부 `--mock`/실제 모델 양쪽 재실행해 회귀 없음을 확인했다.

## 수정 계획
1. local_llm.py 를 실행이 기본 실습 
- mock_llm 은 docker 로만 진행 , 선택 실습
- local_llm.py , mock_llm.py 를 테스트 실행 할수 있는  방법을 추가

2. shared 디렉터리 이름 d00-shared 로 수정
- llm 설정을 하는 것 부터 시작 하고 싶음 
- guide.md 에 설정 메뉴얼 작성
- llm 버전 낮은 메모리 용도 미리 선택으로 추가

3. guide.md
- 과정보다 실습 방법만 기록 해놓고
- 변경이력은 readme.md 에 별도 section 으로 이동