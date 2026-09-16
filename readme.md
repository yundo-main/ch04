# ch04 정책

## 문서 규칙

- 각 일차 디렉터리(`d01`~`d08`)와 `shared/`는 **`guide.md` 하나만** 문서로 둔다.
  그 외 별도 문서 파일(설계 노트, README 등)은 작성하지 않는다.
- 각 디렉터리의 `readme.md`(사용자 작성 브리프)는 이 규칙의 예외다 — 사용자
  본인 계획 공간이며 Claude가 작성하는 `guide.md`와는 별개다.
- `plan.md`는 더 이상 쓰지 않는다. `d01/plan.md`는 과거 기록으로만 남겨두고
  (git에는 올리지 않음), 그 자리는 다른 디렉터리와 동일하게 `readme.md`로
  대체했다.

## 각 일차 디렉터리

| 디렉터리 | 주제 |
| --- | --- |
| `d01` | 프롬프트 인젝션 (직접/간접) |
| `d02` | Jailbreak 방어 전략 |
| `d03` | LLM 데이터 유출 위험 |
| `d04` | RAG 권한 필터링 설계 |
| `d05` | 문서 보안 등급 체계 설계 |
| `d06` | Retrieval 보안 구현 |
| `d07` | Canary Token 활용 |
| `d08` | End-to-End 보안 통합 |

각 디렉터리는 3개 예제(또는 Lab) + 공용 mock 타입 + `Dockerfile` + `readme.md`
(사용자 브리프) + `guide.md`(상세 설명) 구성을 따른다.

## shared/ (d01~d08 공유)

여러 디렉터리가 거의 동일한 파일을 각자 복사해 갖고 있던 것을 하나로 모은
공용 디렉터리다. 각 디렉터리는 필요한 파일만 골라 참조하며, 로컬(venv)
실행 시에는 `sys.path`로, Docker 실행 시에는 빌드 시점에 같은 디렉터리로
평탄화(COPY)해서 찾는다.

| 파일 | 역할 |
| --- | --- |
| `mock_llm.py` | 규칙 기반 mock LLM 엔진. **로컬/Docker 어디서든 기본 실행 경로** — API 키나 외부 서비스 없이 항상 동일하게 재현되는 결정론적 판정을 담당한다. |
| `local_llm.py` | 실제 로컬 Ollama 모델을 호출하는 클라이언트. `--real` 플래그로만 켜지는 선택 경로 — **로컬(venv)에서 가장 간편**하고(호스트에서 바로 `localhost:11434` 접근), Docker에서는 `OLLAMA_HOST` 환경변수 재정의가 필요하다(컨테이너 안의 `localhost`는 컨테이너 자신이라서). |
| `prompts.py` | 공통 프롬프트 조각. `RAG_ANSWER_SYSTEM_INSTRUCTION`(d03/d06/d07/d08 이 실제 모델 `--real` 테스트에서 공통으로 씀), `SAFETY_POLICY_PREFIX`(d02의 세 mock 탈옥 예제가 시스템 지시문 첫 문장으로 공통으로 씀). 문구가 의도적으로 다른 부분(예: d02의 위험 카테고리 나열)은 억지로 합치지 않고 각 디렉터리 자체 파일에 남긴다. |
| `documents.json` | classification/owner/allowed_roles/canary_token 이 태깅된 공용 샘플 문서 세트(d05~d08 사용). |
| `guide.md` | 위 공유 구조와 sys.path/Docker 평탄화 메커니즘에 대한 상세 설명. |

**주의**: 자기 프롬프트도 있고 그중 일부는 `shared/prompts.py`의 상수를
가져와 조합해야 하는 폴더(d02, d03)는, 로컬 파일 이름을 `prompts.py`로
두면 안 된다 — Python 순환 참조(자기 자신을 다시 import)와 Docker `COPY`
경로 충돌(`shared/prompts.py`와 같은 `/app/prompts.py`로 COPY되어 서로
덮어씀)이 동시에 난다. 그래서 이런 폴더는 로컬 파일을 `local_prompts.py`로
따로 이름 짓고, 그 안에서 `shared/prompts.py`의 상수를 가져와 재노출한다.
자세한 내용은 `shared/guide.md` 참고.

## Docker 관련

- 디렉터리별로 실습용 이미지를 **별도로** 빌드한다(하나로 합치지 않는다).
- 단, `shared/`의 파일을 `COPY`해야 하므로 **빌드 컨텍스트는 항상 `ch04/`
  루트**다 — 각 디렉터리 안에서 `docker build .`로 빌드하던 방식은 더 이상
  쓸 수 없다.
  ```
  cd ch04
  docker build -f d01/Dockerfile -t <이미지명> .
  ```
- 정확한 이미지명/실행 명령은 각 디렉터리의 `guide.md`를 따른다.
