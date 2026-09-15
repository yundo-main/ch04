# 프롬프트 인젝션 실습 — 실제 로컬 LLM 버전

이 폴더는 mock 없이 **항상 실제 로컬 소형 LLM**(Qwen2.5-0.5B-Instruct, llama.cpp 백엔드)만
사용합니다. 별도 데몬(Ollama)이나 Docker 없이 파이썬 프로세스 안에서 직접 모델을 로드합니다.

## mock과 real, 실행 시 구분

이 폴더 안에는 mock 자체가 없어서 "구분"할 게 없습니다 — `python direct_injection.py`,
`python indirect_injection.py` 를 실행하면 **항상** `local_llm.py` 를 통해 실제 모델을 호출합니다.
실행 로그에 다음 줄이 보이면 실제 모델이 로드되고 있다는 뜻입니다.

```
[local_llm] 모델 로드 중: qwen2.5-0.5b-instruct-q4_k_m.gguf (최초 1회, 수 초 소요)
```

mock과 비교해가며 돌려보고 싶다면 옆 폴더를 참고하세요:

| 폴더 | mock | real |
|---|---|---|
| `ch04/local-llm/` (이 폴더) | 없음 | 항상 사용 |
| `ch04/d01-docker/` | `python direct_injection.py` (기본) | `python direct_injection.py --real` (mock 검증 후 추가 실행) |

자세한 구성/실행 방법/실험 결과는 [guide.md](guide.md) 참고.
