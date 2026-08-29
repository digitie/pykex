# AGENTS.md

## 목표

이 저장소(GitHub/PyPI 이름 `python-krex-api`, import 패키지 이름 `krex`)는 한국도로공사 OpenAPI
(`data.ex.co.kr`, `data.go.kr`)를 Python 환경에서 쉽게 사용할 수 있도록 제공하는 **OpenAPI
클라이언트 라이브러리**다. API 명세 변환, 데이터 정규화, 로컬 유효성 검사 및 에러 매핑을
핵심 가치로 삼으며, Streamlit 등 시각화나 도메인 가시 레이어는 라이브러리 소비자 앱이
담당한다. `pykma`, `pyopinet`과 같은 작업 형태를 따른다.

## Think Before Coding

- 새 endpoint를 추가하기 전 `endpoints.md`에 명세가 있는지, `API_COVERAGE.md`에 구현/미구현
  상태가 이미 표시돼 있는지 먼저 확인한다.
- 응답 shape이 실제 fixture로 검증되지 않았다면 Pydantic 모델을 성급하게 고정하지 말고
  `Page[dict]`로 시작한다(`CONTRIBUTING.md`의 방침과 동일).
- `pykma`, `pyopinet` 같은 sibling 라이브러리에 이미 검증된 provider 연동이 있는지 먼저
  찾아본다.

## Simplicity First

- 새 기능은 `codes.py` → `models.py` → `client.py` 순으로 필요한 계층만 추가한다.
- 검증된 provider endpoint 구현이 sibling library에 있으면 독립 wrapper를 새로 만들지 않고
  기존 `KrexClient` namespace로 포팅한다.
- Streamlit 등 도메인 시각화·디버그 UI 로직은 이 라이브러리에 넣지 않고 소비자 앱에 맡긴다.

## Surgical Changes

- 한 patch는 관련된 module과 문서만 건드린다. 예를 들어 `src/krex/client.py`를 고치면 같은
  patch에서 `endpoints.md`/`API_COVERAGE.md`도 함께 갱신한다.
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.venv` 같은 산출물은 diff에
  포함하지 않는다.
- 기존 enum/모델 필드 이름을 바꿀 때는 하위 호환이 필요한지 확인하고 `CHANGELOG.md`에 남긴다.

## Goal-Driven Execution

- 지시 우선순위는 사용자 요청 > 이 `AGENTS.md` > `README.md`/기존 테스트 순이다.
- 완료 기준은 관련 pytest가 통과하고, 변경된 동작이 `README.md`/`endpoints.md`/
  `API_COVERAGE.md`에 반영된 상태다.
- 애매한 요구사항은 최소한의, 되돌릴 수 있는 가정으로 진행하고 그 가정을 커밋/PR에 남긴다.

## Practical Bias

- 실제 provider 응답(fixture)이 없는 필드는 무리해서 타입을 좁히지 않고 raw로 남긴다.
- Live 검증은 opt-in(`KEX_LIVE=1`)으로 유지하고, 기본 test suite는 항상 네트워크 없이
  통과해야 한다.
- 문서와 코드가 어긋나면 코드를 기준으로 문서를 먼저 고친다.

## 문서 언어 정책

이 저장소의 **모든 Markdown/RST 문서는 한글로 작성한다**. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지한다.

설명 문장, 절제목, 표 column 헤더, 빠른 시작 가이드, 일지 항목은 한글로 적는다. 새 문서를 만들 때 영문 초안을 두지 않는다 — 처음부터 한글로 쓴다.

## 식별자 표

| 항목 | 값 |
|------|----|
| GitHub 저장소 이름 | `python-krex-api` |
| PyPI 패키지 이름 | `python-krex-api` |
| import 경로 | `import krex` / `from krex import KrexClient` |
| 데이터 소스 | 한국도로공사 OpenAPI (`data.ex.co.kr`, `data.go.kr`) |
| API 인증 키 변수 | `KEX_EX_API_KEY`, `DATA_GO_KR_SERVICE_KEY` |

## 개발 환경 정책

- **Python 버전**: Python 3.11+
- **Git 사용**: 이 저장소의 git 작업은 항상 Windows용 `git.exe` 기준으로 수행한다. WSL 셸 안에서도 필요하면 `"/mnt/c/Program Files/Git/cmd/git.exe"`처럼 Windows git을 직접 호출한다.
- **Unit test**: 네트워크를 절대 직접 호출하지 않는다. Fake session 또는 JSON fixture를 사용한다.
- **의존성 관리**: `pyproject.toml`을 기준으로 하며, 개발 및 디버그용 의존성은 명시된 optional-dependencies에 격리한다.

## 절대 하지 말 것 (DO NOT)

1. **`main` 직접 푸시 금지**: 반드시 feature 브랜치 + PR 머지 과정을 거친다.
2. **API key 평문 커밋 및 노출 금지**: `.env`에 키를 관리하되 절대 커밋하지 않는다. `data.ex.co.kr`에는 `KEX_EX_API_KEY`, `data.go.kr`에는 `DATA_GO_KR_SERVICE_KEY` 환경 변수를 사용한다. `KrexClient` 인스턴스 표현식(`__repr__`)이나 실패 메시지, 문서 등에 API 키가 노출되지 않도록 처리한다.
3. **Unit test에서 network 호출 금지**: 가짜 세션(Fake Session)이나 fixture 파일(JSON 등)을 사용한다.
4. **Stable 의미가 있는 반환값을 raw string으로 노출 금지**: raw string보다는 typed Pydantic model 또는 enum을 제공한다.
5. **주소·코드 원문 임의 가공 금지**: 모호한 raw 주소 데이터에서 법정동 코드를 추측하지 않고 provider 원문 문자열 그대로 보존한다. `routeNo`, `unitCode`, branch code, office code 등 앞에 0이 붙는 코드는 반드시 문자열 타입으로 보존하고 leading zero를 제거하지 않는다.
6. **Debug UI 의존성을 이 library에 포함 금지**: Streamlit 등의 디버그 UI 도구는 배포 패키지 코어 의존성에서 철저히 제외한다.

## Module ownership

- `src/krex/_http.py`: transport, retry, API envelope/error mapping
- `src/krex/_convert.py`: 응답 경계의 작은 변환 helper
- `src/krex/codes.py`: enum과 code label
- `src/krex/models.py`: 공개 Pydantic 반환 model
- `src/krex/client.py`: 고수준 endpoint namespace와 parsing
- `src/krex/catalog.py`: 구현 API catalog, dataset 이름, service-key 신청 URL
- `src/krex/debug.py`: `DebugRun`, JSON 변환, redaction, fixture 저장
- `API_COVERAGE.md`: 구현 여부와 live verification 상태의 기준 문서

## Test 기준

새 endpoint wrapper는 query parameter와 enum conversion, 단일/다중 response normalization, required parameter validation, malformed response shape, body-level API error, 성공 model conversion을 test한다. UI에서 capture할 endpoint라면 `tests/runners.py` replay mapping과 JSON fixture를 추가한다.

## Documentation 기준

동작이 바뀌면 같은 patch에서 관련 문서를 갱신한다.

- 사용자 사용법: `README.md`
- endpoint parameter 또는 response field: `endpoints.md`
- coverage/support 상태: `API_COVERAGE.md`
- enum 변경: `codes.md`
- exception/provider error mapping: `error-codes.md`
- 구조적 결정(뒤집힐 수 있는, 재론쟁될 만한 결정): `docs/decisions.md`
- agent workflow/repeated mistakes: `SKILL.md`와 이 파일
- 문서 스타일 규칙: `CONTRIBUTING.md`, `SKILL.md`, 이 파일을 함께 갱신

## 검증

```bash
python -m compileall src/krex tests
python -m pytest
python -m mypy src/krex
ruff check .
```

실제 `data.ex.co.kr` 및 `data.go.kr` 검증은 의도적으로 할 때만 다음 명령어를 사용한다:
```powershell
$env:KEX_LIVE="1"
python -m pytest -m live -vv
```
