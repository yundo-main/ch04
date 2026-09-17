# d00-shared 가이드

`ch04/d01`~`d08`이 공유하는 공용 파일 모음이다. 각 디렉터리가 거의 동일한
mock 엔진/Ollama 클라이언트를 각자 복사해 갖고 있다가 서서히 드리프트되던
것(예: 시스템 지시문 문구가 미묘하게 달랐던 것)을 여기 하나로 모았다.
샘플 문서(`documents.json`)와 프롬프트 텍스트(`prompts.py`)는 한때 이
디렉터리에서 공유했지만, 지금은 각 챕터(documents.json은 d05~d08,
prompts.py는 d01~d08)가 로컬 복사본을 쓴다 — d00-shared에는 둘 다 없다.
자세한 경위는 `readme.md`의 "변경이력" 참고.

**설계 원칙 — wrap은 전송만, 콘텐츠는 별도**: 각 챕터에는 `local_llm.py`를
재노출하는 얇은 `real_llm.py`가 하나씩 있다(`script → real_llm.py →
local_llm.py`). 이 `real_llm.py`는 **순수 wrap이다** — `DEFAULT_MODEL`/
`chat_messages`/`ask_real`/`is_ollama_available`을 그대로 다시 내보내기만
하고, 그 이상은 아무것도 모른다. 공격 프롬프트, `SECRET_CODENAME` 같은
**챕터 전용 콘텐츠는 `real_llm.py`에 없다** — 여러 스크립트가 공유하는
콘텐츠는 그 챕터의 `prompts.py`에, 스크립트 하나만 쓰는 콘텐츠는 그
스크립트의 `run_real()` 함수 안에 있다. "wrap은 어떻게 전송하는가만
알고, 무엇을 보내는가는 몰라야 한다"는 원칙을 지키기 위한 구분이다 —
예전에는 이 둘이 `real_llm.py` 한 파일에 섞여 있어서(전송 재노출 + 콘텐츠)
혼란이 있었다.

(참고: "시나리오"라는 말은 이 문서에서 아키텍처 용어로 안 쓴다 — d02
공격 문구 자체에 이미 "역할극/가상 시나리오"라는 뜻으로 쓰이고 있어서
겹친다. 여기서는 그냥 **콘텐츠**라고 부른다.)

## 0단계: LLM 환경 설정 (수업 시작점)

d01부터 진행하기 전에 여기서 Ollama 설치와 모델 준비를 먼저 끝낸다. 이후
각 dNN/guide.md의 "실제 모델(Ollama) 실행 — 기본 실습" 단계는 이 설정이
끝났다는 것을 전제로 한다. 아래 0~3단계는 리포지터리 루트 venv를 활성화한
뒤 그 한 셸 세션 안에서 이어서 진행한다.

```
source venv/bin/activate
```

**주의**: Ollama 자체(서버 데몬 + CLI)는 brew/curl/설치 파일로 까는
시스템 범위 프로그램이라 `pip install`처럼 venv 안에 설치되는 대상이
아니다. 위에서 활성화한 venv는 뒤에 나오는 "3) 설정 확인" 단계의
`python`/`local_llm.py` 실행을 위한 것이고, 아래 설치 명령은 이 세션
안에서 그대로 시스템에 설치된다.

### 1) 설치

macOS:
```
brew install ollama
```

Linux:
```
curl -fsSL https://ollama.com/install.sh | sh
```

Windows: https://ollama.com/download 에서 설치 파일을 받아 실행한다
(winget 사용 시 `winget install Ollama.Ollama`).

설치 확인:
```
ollama --version
```

### 2) 서버 실행 및 모델 준비

```
ollama serve &
ollama pull exaone3.5:2.4b
```
(macOS 앱 형태로 설치해 메뉴바 아이콘이 떠 있는 경우 서버가 이미 실행 중이므로
`ollama serve`는 생략 가능하다.)

`pull`이 실제로 끝났는지는 `ollama list`로 확인한다 — 목록에 `exaone3.5:2.4b`가
보여야 한다. **서버가 떠 있는 것과 모델이 준비된 것은 별개다**: 서버만 뜨고
모델을 안 받으면 연결 자체는 성공하지만 실제 호출 시 `404 Not Found`로
실패한다(아래 트러블슈팅 표 참고).

```
 % ollama list
NAME              ID              SIZE      MODIFIED
exaone3.5:2.4b    13644fc3d28e    1.6 GB    7 minutes ago
```

**`DEFAULT_MODEL`은 기본값으로 `exaone3.5:2.4b`가 지정돼 있다** — LG AI연구원의
한국어·영어 이중언어 모델이라 이 실습의 한국어 프롬프트를 한국어로 자연스럽게
받아친다(다른 소형 모델은 한국어 입력에도 영어로 답하는 경우가 흔하다).
모든 dNN 스크립트가 `d00-shared/local_llm.py`의 이 상수를 그대로 가져다
쓰므로, 한 곳만 고치면 전체에 적용된다.

**주의 — 챕터마다 결과가 다를 수 있다**: 실제로 확인한 바로는 d01(직접
인젝션)/d03/d06에서는 취약 경로가 안정적으로 재현되지만, **d02(페르소나
탈옥)의 취약 경로는 모델이 진짜 비밀 코드명 대신 그럴듯한 가짜 코드명을
지어내서(할루시네이션) `leaked_secret=False`로 잡히는 경우가 있다** —
문자열 정확 일치 기반 판정의 한계를 보여주는 사례이니, d02 취약 경로
결과는 특히 여러 번 반복해서 확인할 것. (예전에는 보안 경로도 방어 설명
중 실제 코드명을 인용해 `leaked_secret=True`로 잘못 잡히는 경우가 있었지만,
`run_real()`에 mock과 동일한 두 겹 방어(identity anchoring + 출력 게이트)를
갖춰서 지금은 해결됐다 — `d02/guide.md` 잔여 위험 참고.)

**다른 모델로 바꿔보고 싶다면 — 선택**: 아래 표는 실제로 pull해서
비교 테스트한 결과다.

| 모델 | 크기 | 한국어 응답 | 인젝션 재현 안정성 |
| --- | --- | --- | --- |
| `exaone3.5:2.4b` (기본) | 2.4B | 자연스러움 | d01/d03/d06 안정적, d02 취약 경로는 할루시네이션으로 False 판정 사례 있음 |
| `tinyllama` | 1.1B | 항상 영어로 답함 | 매우 안정적으로 재현됨(단, 반복 루프 방지를 위해 temperature를 올려둠) |
| `qwen2.5:0.5b` | 0.5B | 가능 | 걸리거나 엉뚱한 응답이거나 불안정 |
| `llama3.2:1b` | 1B | 부분적 | 대부분 저항(안 걸림) — 안전 정렬이 비교적 강함 |

```
ollama pull tinyllama        # 또는
ollama pull qwen2.5:0.5b     # 또는
ollama pull llama3.2:1b
```
사용하려면 `d00-shared/local_llm.py`의 `DEFAULT_MODEL = "exaone3.5:2.4b"`
줄을 원하는 모델 이름으로 바꾼다. 모델마다 지시 순응도·언어 능력·안전
정렬 강도가 달라서 결과가 달라진다 — 어느 모델을 쓰든 그 결과가 다른
모델 기준 설명과 달라질 수 있다는 점을 감안한다.

### 3) 설정 확인 (Python)

이어서(위에서 활성화한 venv 그대로) 확인한다. 빠른 확인은 한 줄이면 된다:
```
cd ch04/d00-shared
python -c "from local_llm import is_ollama_available; print(is_ollama_available())"
```
`True`가 나오면 서버 연결까지는 준비 완료다. `False`면 `ollama serve`가
실행 중인지부터 다시 확인한다 — 이 상태에서 각 dNN 스크립트를 플래그
없이 실행하면 mock 비교조차 실행하지 않고 `LLM 연결 안됨` 메시지만
출력한 뒤 종료한다(mock 결과만이라도 보려면 `--mock`을 명시해야 한다).

`mock_llm.py`/`local_llm.py` 둘 다 실제로 호출해보려면 `smoke_test.py`를
쓴다 — 아래 "smoke_test.py — 단독 동작 확인" 절 참고.

### 4) 종료 (실습 중간에 리소스를 비우고 싶을 때)

```
pkill ollama
```
(또는 `ps aux | grep ollama`로 PID를 찾아 `kill <PID>`.) 서버를 내리면
각 dNN 스크립트는 플래그 없이는 `LLM 연결 안됨` 메시지만 출력하고
종료한다 — mock만 보려면 `--mock`을 명시해야 한다.

### 트러블슈팅

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `is_ollama_available()` → `False` | 서버 미실행 | `ollama serve` 실행, `ollama --version`으로 설치 여부 재확인 |
| HTTP 404 Not Found (`/api/chat` 호출 시) | 서버는 떠 있으나 모델 미설치 | `ollama pull exaone3.5:2.4b` 후 `ollama list`로 재확인 |

**Docker는 mock 전용이다** — 실제 모델 검증은 로컬(venv)에서만
진행하며, Docker 실습에서는 `OLLAMA_HOST` 재정의나 컨테이너-호스트 연결
문제 자체가 발생하지 않는다.

## smoke_test.py — 단독 동작 확인

`mock_llm.py`/`local_llm.py`가 각각 정상 동작하는지 빠르게 확인하는
진단 스크립트다.  
특정 챕터의 취약/보안 시나리오가 아니라 **"이 두 엔진
자체가 살아있는가"만** 본다 — 0단계 설정이 끝났는지 확인할 때 쓴다.

```
source venv/bin/activate
cd ch04/d00-shared
python smoke_test.py
```

**`mock_llm.py` 테스트** (항상 실행, 외부 의존성 없음)
- `naive_generate()`에 인젝션 문구를 넣어 `obeyed_injected_instruction == True`인지 확인
- `guarded_generate()`에 같은 문구를 넣어 `obeyed_injected_instruction == False` + `injection_detected == True`인지 확인
- 각각 `assert`로 검증한다 — 결정론적이라 매번 같은 결과가 나와야 정상이고, 실패하면 `AssertionError`로 즉시 드러난다.

**`local_llm.py` 테스트** (Ollama 상태에 따라 분기)
- `is_ollama_available()`로 서버 연결부터 확인
- 연결 안 되면 `SKIP` 메시지만 출력하고 에러 없이 종료
- 연결되면 `ask_real()`로 간단한 질문을 보내 실제 모델 응답 텍스트를 출력한다(비결정적이라 `assert`는 걸지 않고 결과만 보여준다)

**예상 출력** (Ollama 연결된 경우):
```
mock_llm.py 단독 테스트
...
PASS: mock_llm.py 정상 동작 확인.

local_llm.py 단독 테스트
[ask_real] model=exaone3.5:2.4b text='4'
PASS: local_llm.py 정상 동작 확인(실제 모델 응답 수신).
```
Ollama가 없으면 마지막 줄이 `SKIP: Ollama 서버(...)에 연결할 수 없다`로
바뀔 뿐, `mock_llm.py` 쪽 `PASS`는 그대로 나온다.

**검증 범위의 한계**: 이 스크립트의 `PASS`는 d00-shared 모듈 자체가
동작한다는 뜻이지, d01~d08 각 챕터의 취약/보안 경로가 정상이라는 뜻이
아니다 — 자세한 내용은 아래 "잔여 위험" 참고.

## 구성 파일

| 파일 | 역할 | 사용처 |
| --- | --- | --- |
| `mock_llm.py` | 가중치 기반 규칙 mock LLM 엔진(`PatternRule`/`score_text`/`naive_generate`/`guarded_generate`) | d01 |
| `local_llm.py` | 로컬 Ollama HTTP 클라이언트(`chat_messages`/`ask_real`/`is_ollama_available`) — 각 챕터의 `real_llm.py`(순수 wrap, 내용 없음)가 재노출하고, 메인 스크립트는 그 `real_llm.py`를 import 한다 | d01~d08 |
| `smoke_test.py` | `mock_llm.py`/`local_llm.py` 단독 동작 확인용 진단 스크립트(0단계 검증) | d00-shared 전용, 다른 dNN에서 참조 안 함 |

`mock_llm.py`는 현재 d01의 카탈로그(`INJECTION_PATTERNS`)만 내장하고 있다 —
`PatternRule`/`score_text`/`naive_generate`/`guarded_generate`는 카탈로그를
인자로 받는 범용 엔진이라, 다른 디렉터리도 자신만의 카탈로그를 정의해 같은
엔진을 재사용할 수 있지만 아직 d02/d03 등은 자체 판정 로직을 그대로 쓴다.

## 각 디렉터리가 공유 파일을 찾는 방법

`local_llm.py`/`mock_llm.py`는 **Python 모듈**이라, 각 디렉터리의
`real_llm.py`(local_llm.py 재노출) 또는 d01의 메인 스크립트(mock_llm.py를
직접 쓰는 경우)가 상단에서 아래처럼 `sys.path`에 이 디렉터리를 추가해서
찾는다.

```python
sys.path.append(str(Path(__file__).resolve().parent.parent / "d00-shared"))
```

`insert(0, ...)`가 아니라 **`append()`**를 쓰는 이유: 로컬 디렉터리에 동명
파일이 있으면 그게 항상 우선해야 한다. `append()`는 이미 자동으로 잡혀
있는 스크립트 자신의 디렉터리보다 `d00-shared/`를 뒤에 두므로, 이름이 겹쳐도
로컬 파일이 이긴다.

각 챕터의 `real_llm.py`는 이 sys.path 추가 + 재노출만 한다 — 그 이상은
모른다. 챕터 전용 콘텐츠(예: d01의 태그 기반 격리 프롬프트 조립)는
`real_llm.py`가 아니라 각 메인 스크립트의 `run_real()` 함수 안에 직접
있다. 여러 스크립트가 공유하는 콘텐츠(예: d02의 `SECRET_CODENAME`/
`BASE_SYSTEM_INSTRUCTION` — persona/escalation/encoding 세 스크립트가
공통으로 씀)는 그 챕터의 `prompts.py`에 있다(`REAL_*` 접두사로 mock
전용 상수와 구분).

`prompts.py`와 `documents.json`은 d00-shared에 없다 — d01~d08 각 폴더가
전부 자기 로컬 복사본을 직접 읽는다(`prompts.py`는 같은 규칙으로
`sys.path`에서 스크립트 자신의 디렉터리가 항상 먼저 잡히고, `documents.json`은
`Path(__file__).resolve().parent / path`). `RAG_ANSWER_SYSTEM_INSTRUCTION`
처럼 여러 챕터(d03 예제2/d06/d07/d08)가 똑같은 문구를 쓰는 경우도 각자
로컬 `prompts.py`에 동일한 값으로 중복해서 넣는다 — 왜 d00-shared 공유를
그만뒀는지는 `readme.md`의 "변경이력" 참고.

## Docker에서는 어떻게 동작하는가

Docker `COPY`는 빌드 컨텍스트 밖의 파일을 가져올 수 없다. `d00-shared/`가 각
`dNN/`의 형제 디렉터리이므로, 컨테이너 안에 실제 디렉터리 구조
(`d01/`, `d00-shared/` 분리)를 그대로 재현할 수 없다 — 대신 각 `Dockerfile`이
빌드 컨텍스트를 `ch04/` 루트로 잡고, `d00-shared/`의 필요한 파일과 `dNN/`의
파일을 **같은 `WORKDIR`(`/app`)에 평탄화해서 COPY**한다.

```dockerfile
COPY d00-shared/local_llm.py ./
COPY d06/documents.json d06/prompts.py d06/retrieval_security_mock.py d06/real_llm.py d06/retrieval_authorization_enforcement.py d06/embedding_poisoning.py d06/chunk_sanitization.py ./
```
(`documents.json`/`prompts.py`/`real_llm.py` 모두 d00-shared가 아니라 각
챕터 로컬 파일 — d06처럼 여러 파일을 쓰는 챕터는 COPY 목록에서 자기
자신의 로컬 복사본을 가져온다.)

컨테이너 안에서는 모든 파일이 `/app`에 나란히 있으므로 Python 모듈
import는 스크립트 자신의 디렉터리(`/app`)에서 바로 찾아지고, 위
`sys.path.append(".../d00-shared")` 호출은 존재하지 않는 경로를 추가하는
것이라 조용히 무시된다(에러 없음) — 로컬 실행과 동일한 코드가 그대로
동작한다.

즉 **로더 코드는 로컬(venv)과 Docker 양쪽 레이아웃을 모두 지원하도록
설계돼 있고, 별도의 환경 분기 없이 동일하게 동작한다.** (검증 방법: 실제
Docker 없이도, 각 `Dockerfile`의 `COPY` 목록대로 파일을 한 디렉터리에 모아
스크립트를 실행해보면 동일한 결과를 확인할 수 있다.)

**Ollama는 Docker에서 쓰지 않는다.** `local_llm.py`가 각 `Dockerfile`에
COPY되는 이유는 각 챕터의 `real_llm.py`가 이 파일을 무조건 `import`하기
때문이지(안 넣으면 `ModuleNotFoundError`), 컨테이너 안에서 실제 Ollama
서버에 연결하기 위해서가 아니다. Docker 실습은 mock 전용 정책이라
`--mock` 플래그를 CMD에 명시하고, 그래서 컨테이너 안에서
`local_llm.chat_messages()`가 실제로 호출되는 경로 자체가 없다 —
`OLLAMA_HOST` 재정의나 `host.docker.internal`/`--network host` 같은
컨테이너-호스트 연결 문제는 이 구성에서 아예 발생하지 않는다. 실제 모델
검증은 항상 로컬(venv)에서만 진행한다.

## 빌드 컨텍스트 요약

```
cd ch04
docker build -f d06/Dockerfile -t retrieval-security-demo .
```

`d06/`처럼 각 디렉터리 안에서 `docker build .`로 빌드하던 이전 방식은 더
이상 동작하지 않는다 — `d00-shared/`가 빌드 컨텍스트 밖에 있기 때문이다.

## 잔여 위험

- **콘텐츠는 `real_llm.py`가 아니라 `prompts.py`/스크립트에 있다**: d02의
  `SECRET_CODENAME`/`BASE_SYSTEM_INSTRUCTION`은 `prompts.py`의 `REAL_*`
  상수로 한 번만 정의되고 세 스크립트(persona/escalation/encoding)가
  그걸 가져다 쓴다 — `real_llm.py`(wrap)에 넣지 않으면서도 중복 없이
  공유한 것이다. `real_llm.py`는 여전히 이 콘텐츠를 전혀 모른다.
- d05~d08의 `documents.json`은 지금 전부 **동일한 내용의 로컬 복사본**이다
  (d00-shared 공유를 그만두면서 물리적으로 4벌로 나뉨). 8개 문서 중 일부
  (`restricted-*`)는 canary_token이 붙어 있어, canary와 무관한 챕터(d05,
  d06 일부 예제)에서도 이 필드가 같이 로드된다 — 사용하지 않는 필드일
  뿐 동작에는 영향 없다.
- **드리프트 위험**: 애초에 d00-shared로 문서를 모았던 이유가 "챕터마다
  로컬 복사본을 따로 갖고 있으면 서서히 내용이 달라진다"는 문제였다(맨 위
  소개 참고). 지금은 의도적으로 그 상태로 되돌린 것이므로, 한 챕터의
  `documents.json`만 고치고 나머지 3개를 안 고치면 그 순간부터 다시
  드리프트가 시작된다 — 특히 d08은 "d04/d05/d07 통제를 모두 갖춘 통합
  세트"라는 전제로 설계돼 있어서, 다른 챕터에서만 문서를 바꾸면 d08의
  전제가 깨질 수 있다.
- **`prompts.py`도 같은 드리프트 위험이 있다.** `RAG_ANSWER_SYSTEM_INSTRUCTION`
  은 d03(예제2)/d06/d07/d08 네 곳의 로컬 `prompts.py`에 동일한 문구로
  중복돼 있다 — 한 곳만 고치고 나머지를 안 맞추면 "같은 실제 모델
  테스트인데 시스템 지시문이 챕터마다 다르다"는 상태가 조용히 생길 수
  있다. d01/d02/d03의 나머지 상수(DIRECT_*/PERSONA_* 등)는 챕터별로
  원래 다른 내용이라 이 위험이 없다.
- `mock_llm.py`의 카탈로그(`INJECTION_PATTERNS`)는 d01 전용으로 설계됐다.
  다른 디렉터리가 이 엔진을 재사용하려면 자기 카탈로그를 새로 정의해야
  하며, 아직 이 작업은 d02(jailbreak)/d03(leakage)에 대해 이뤄지지 않았다.
- 세 파일(`local_llm.py` 경유 실제 모델 호출) 모두 결과가 비결정적이다 —
  자세한 잔여 위험은 `local_llm.py` 상단 주석 참고.
- `smoke_test.py`의 `PASS`는 **d00-shared 모듈 자체가 동작한다**는 것만
  보장하지, d01~d08 각 챕터의 취약/보안 경로가 정상이라는 뜻이 아니다 —
  범위가 좁다: mock 쪽은 d01 전용 `INJECTION_PATTERNS` 카탈로그 하나만
  검증하고(d02/d03은 자체 판정 로직을 쓰므로 커버 안 됨), local 쪽은
  "2+2는 몇이야?" 같은 비보안 질문으로 연결/응답 여부만 확인한다 — 실제
  모델이 인젝션/탈옥 문구에 어떻게 반응하는지는 각 dNN 스크립트를
  플래그 없이 직접 돌려봐야 한다.
- `smoke_test.py`의 mock 검증은 `mock_llm.py`의 현재 `OBEY_THRESHOLD`/
  `DETECTION_THRESHOLD`/`INJECTION_PATTERNS` 값에 결합돼 있다. 이 상수들을
  바꾸면 `assert`가 깨지거나, 반대로 의도한 변경인데도 실패로 보일 수
  있다 — 실패 시 코드 버그인지 의도한 튜닝 변경인지부터 구분할 것.
