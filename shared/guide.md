# shared 가이드

`ch04/d01`~`d08`이 공유하는 공용 파일 모음이다. 각 디렉터리가 거의 동일한
mock 엔진/Ollama 클라이언트/샘플 문서를 각자 복사해 갖고 있다가 서서히
드리프트되던 것(예: 같은 문서인데 폴더마다 canary_token 유무가 달랐던 것,
시스템 지시문 문구가 미묘하게 달랐던 것)을 여기 하나로 모았다.

## 구성 파일

| 파일 | 역할 | 사용처 |
| --- | --- | --- |
| `mock_llm.py` | 가중치 기반 규칙 mock LLM 엔진(`PatternRule`/`score_text`/`naive_generate`/`guarded_generate`) | d01 |
| `local_llm.py` | 로컬 Ollama HTTP 클라이언트(`chat_messages`/`ask_real`/`is_ollama_available`) | d01~d08 (`real_llm.py` 경유) |
| `prompts.py` | 공통 프롬프트 조각 — `RAG_ANSWER_SYSTEM_INSTRUCTION`(실제 모델 `--real` 테스트용), `SAFETY_POLICY_PREFIX`(mock 탈옥 예제 시스템 지시문 첫 문장) | `RAG_ANSWER_SYSTEM_INSTRUCTION`: d03(예제 2), d06, d07, d08 / `SAFETY_POLICY_PREFIX`: d02 |
| `documents.json` | classification/owner/allowed_roles/canary_token 태깅된 공용 샘플 문서 8건 | d05, d06, d07, d08 |

(참고: `local_prompts.py`는 `shared/`가 아니라 `d02/`, `d03/` 안에 있다 — 각
폴더 자체 프롬프트 + shared 상수를 함께 재노출하는 파일이다. 아래
"폴더가 자기 프롬프트 + shared 프롬프트를 둘 다 필요로 할 때" 참고.)

`mock_llm.py`는 현재 d01의 카탈로그(`INJECTION_PATTERNS`)만 내장하고 있다 —
`PatternRule`/`score_text`/`naive_generate`/`guarded_generate`는 카탈로그를
인자로 받는 범용 엔진이라, 다른 디렉터리도 자신만의 카탈로그를 정의해 같은
엔진을 재사용할 수 있지만 아직 d02/d03 등은 자체 판정 로직을 그대로 쓴다.

## 각 디렉터리가 공유 파일을 찾는 방법

`local_llm.py`/`mock_llm.py`/`prompts.py`는 **Python 모듈**이라 각 디렉터리의
`real_llm.py`(또는 d01의 경우 `direct_injection.py`/`indirect_injection.py`)
상단에서 아래처럼 `sys.path`에 이 디렉터리를 추가해서 찾는다.

```python
sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))
```

`insert(0, ...)`가 아니라 **`append()`**를 쓰는 이유: 로컬 디렉터리에 동명
파일이 있으면(예: d01은 자체 `prompts.py`를 갖고 있다) 그게 항상 우선해야
한다. `append()`는 이미 자동으로 잡혀 있는 스크립트 자신의 디렉터리보다
`shared/`를 뒤에 두므로, 이름이 겹쳐도 로컬 파일이 이긴다.

### 폴더가 자기 프롬프트 + shared 프롬프트를 **둘 다** 필요로 할 때

d01처럼 로컬 `prompts.py`가 shared 와 아예 무관하면 위 `append()` 규칙만으로
충분하다. 하지만 d02/d03 처럼 **로컬 프롬프트도 있고 그중 일부는 shared의
상수(`SAFETY_POLICY_PREFIX`, `RAG_ANSWER_SYSTEM_INSTRUCTION`)를 가져와
조합**해야 하는 경우, 로컬 파일 이름을 `prompts.py`로 두면 안 된다 — 두
가지 문제가 동시에 난다.

1. **Python 순환 참조**: 로컬 `prompts.py` 안에서 `from prompts import
   SAFETY_POLICY_PREFIX`를 쓰면, `import prompts`가 지금 로딩 중인 자기
   자신을 다시 가져오려는 순환 참조가 된다(로컬 디렉터리가 항상 먼저
   검색되므로).
2. **Docker COPY 경로 충돌**: 빌드 시 `COPY shared/prompts.py ./`와
   `COPY d02/prompts.py ./`가 이미지 안의 **같은 경로**(`/app/prompts.py`)를
   가리킨다 — 나중 COPY가 앞선 걸 덮어써서, 컨테이너 안에는 둘 중 하나만
   남는다.

그래서 d02/d03은 로컬 파일을 `local_prompts.py`로 이름 짓고, 그 안에서
`from prompts import ...`로 shared 상수를 가져와 자기 것과 조합해 재노출한다
(`sys.path` 검색에서 "prompts"라는 이름이 이제 shared 파일만 가리키므로
충돌이 없다). 각 예제 스크립트는 `from local_prompts import ...`로 최종
조합된 상수만 가져온다.

`documents.json`은 **Python 모듈이 아니라 파일 경로로 직접 여는 데이터
파일**이라 `sys.path`의 영향을 받지 않는다. 대신 각 로더 함수가 두 경로를
순서대로 확인한다.

```python
here = Path(__file__).resolve().parent
shared_candidate = here.parent / "shared" / path
doc_path = shared_candidate if shared_candidate.exists() else here / path
```

## Docker에서는 어떻게 동작하는가

Docker `COPY`는 빌드 컨텍스트 밖의 파일을 가져올 수 없다. `shared/`가 각
`dNN/`의 형제 디렉터리이므로, 컨테이너 안에 실제 디렉터리 구조
(`d01/`, `shared/` 분리)를 그대로 재현할 수 없다 — 대신 각 `Dockerfile`이
빌드 컨텍스트를 `ch04/` 루트로 잡고, `shared/`의 필요한 파일과 `dNN/`의
파일을 **같은 `WORKDIR`(`/app`)에 평탄화해서 COPY**한다.

```dockerfile
COPY shared/local_llm.py shared/prompts.py shared/documents.json ./
COPY d06/retrieval_security_mock.py d06/real_llm.py ... ./
```

컨테이너 안에서는 모든 파일이 `/app`에 나란히 있으므로:
- Python 모듈 import는 스크립트 자신의 디렉터리(`/app`)에서 바로 찾아지고,
  위 `sys.path.append(".../shared")` 호출은 존재하지 않는 경로를 추가하는
  것이라 조용히 무시된다(에러 없음) — 로컬 실행과 동일한 코드가 그대로
  동작한다.
- `documents.json` 로더의 `shared_candidate`도 존재하지 않으므로 두 번째
  분기(같은 디렉터리)로 자연히 폴백된다.

즉 **로더 코드는 로컬(venv)과 Docker 양쪽 레이아웃을 모두 지원하도록
설계돼 있고, 별도의 환경 분기 없이 동일하게 동작한다.** (검증 방법: 실제
Docker 없이도, 각 `Dockerfile`의 `COPY` 목록대로 파일을 한 디렉터리에 모아
스크립트를 실행해보면 동일한 결과를 확인할 수 있다.)

## 빌드 컨텍스트 요약

```
cd ch04
docker build -f d06/Dockerfile -t retrieval-security-demo .
```

`d06/`처럼 각 디렉터리 안에서 `docker build .`로 빌드하던 이전 방식은 더
이상 동작하지 않는다 — `shared/`가 빌드 컨텍스트 밖에 있기 때문이다.

## 잔여 위험

- `documents.json`의 8개 문서 중 일부(`restricted-*`)는 canary_token이
  붙어 있어, canary와 무관한 디렉터리(d05, d06 일부 예제)에서도 이 필드가
  같이 로드된다 — 사용하지 않는 필드일 뿐 동작에는 영향 없지만, 새 예제를
  추가할 때 이 문서 세트를 그대로 재사용하면 의도치 않게 canary 관련 필드에
  의존하게 될 수 있다.
- `mock_llm.py`의 카탈로그(`INJECTION_PATTERNS`)는 d01 전용으로 설계됐다.
  다른 디렉터리가 이 엔진을 재사용하려면 자기 카탈로그를 새로 정의해야
  하며, 아직 이 작업은 d02(jailbreak)/d03(leakage)에 대해 이뤄지지 않았다.
- 세 파일(`local_llm.py` 경유 실제 모델 호출) 모두 결과가 비결정적이다 —
  자세한 잔여 위험은 `local_llm.py` 상단 주석 참고.
