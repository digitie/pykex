# 기여 가이드

`python-krex-api`는 작은 module, 명시적 model, network-free test, 발견한 위험 지점을 남기는 문서를 지향한다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. API field, code identifier, 명령어, URL, provider 원문은 필요한 경우 원문을 유지한다.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

git 명령은 Windows용 `git.exe` 기준으로 사용한다. WSL 셸에서 작업할 때도 `"/mnt/c/Program Files/Git/cmd/git.exe"` 호출을 우선한다.

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 코드를 바꾸기 전에

작업과 맞는 문서를 먼저 읽는다.

- `endpoints.md`: endpoint path, parameter, response field
- `codes.md`: code table과 enum 이름
- `error-codes.md`: provider error mapping
- `SKILL.md`, `AGENTS.md`: 구현 규칙과 반복 실수

## Endpoint 추가

1. `endpoints.md`에 endpoint entry가 있는지 확인하거나 추가한다.
2. 안정된 public code가 있으면 `src/krex/codes.py`에 enum을 추가한다.
3. response schema가 확인된 경우에만 `src/krex/models.py`에 Pydantic model을 추가한다.
4. 올바른 namespace의 `src/krex/client.py`에 client method를 추가한다.
5. Query parameter, response parsing, single-object normalization, provider error, malformed shape, local validation test를 추가한다.
6. 사용자가 직접 호출할 endpoint만 README 예시에 추가한다.

Path나 schema가 검증되지 않았으면 `Page[dict]`를 반환하고 상태를 명확히 문서화한다. 잘못된 공개 model을 제거하는 것보다 나중에 typed model로 승격하는 편이 안전하다.

## Debug fixture

Debug UI 흐름은 fixture-first다.

- Streamlit 등 UI 의존성은 이 library 밖에 둔다.
- `KrexClient.debug_call()`로 input, request, response, parsed, processed, trace, catalog, error를 담은 `DebugRun`을 만든다.
- 의미 있는 case는 `krex.save_fixture()`로 `tests/fixtures/{function}/{case}.json`에 저장한다.
- API key, Authorization header, token 값을 저장하지 않는다. Writer가 민감 key를 redaction하더라도 commit 전 직접 확인한다.
- 새 function fixture에는 `tests/runners.py`를 추가/갱신한다.
- `tests/test_generated_fixtures.py`가 raw response를 replay하게 두고, case마다 pytest file을 생성하지 않는다.

## Sibling library에서 port하기

`pykma`, `pyopinet` 등 sibling project에 같은 provider endpoint의 검증된 구현이 있으면 기존 `KrexClient` namespace로 직접 port한다. 별도 standalone wrapper/client를 만들지 않는다. 이 방식은 최소 diff보다 클 수 있지만 field mapping, sentinel 처리, validation rule을 보존하고 중복 abstraction을 줄인다.

## Test

일반 변경에 필요하다.

```bash
python -m compileall src/krex tests
python -m pytest
python -m mypy src/krex
```

넓은 변경에는 다음도 고려한다.

```bash
python -m pytest --cov=krex --cov-fail-under=90
ruff check .
```

`ruff`가 설치되어 있지 않으면 PR 또는 commit note에 남긴다.

## Live API test

기본 test는 실제 API를 호출하지 않는다. Live test에는 marker를 붙인다.

```python
@pytest.mark.live
def test_real_endpoint(...):
    ...
```

`KEX_EX_API_KEY` 또는 `DATA_GO_KR_SERVICE_KEY`가 없으면 live test는 깨끗하게 skip해야 한다. Key, 계정 정보, 민감값이 포함된 실제 response file은 commit하지 않는다.

## 문서 기대치

동작 변경은 같은 patch에서 문서를 갱신한다.

- `README.md`: 공개 사용법, architecture, validation status
- `endpoints.md`: endpoint contract
- `codes.md`: 공개 code table
- `error-codes.md`: exception mapping
- `SKILL.md`/`AGENTS.md`: workflow rule과 repeated mistake

Style rule:

- 파일 위치는 `src/krex/client.py`처럼 프로젝트 기준 상대 경로로 쓴다.
- Python docstring과 설명 주석은 provider 원문이나 public code/protocol identifier를 보존하는 경우를 제외하고 한글로 쓴다.
- Windows workspace에서 `rg.exe`가 막히면 PowerShell enumeration과 `Select-String`을 사용한다.
- Windows workspace의 git worktree는 WSL 기본 `git` 대신 Windows용 `git.exe`로 다룬다.
- Korean text가 깨져 보이면 먼저 `Get-Content -Encoding utf8`로 확인한다.

## Security

- `.env` file을 commit하지 않는다.
- API key를 test나 example에 붙여넣지 않는다.
- Key가 실수로 commit되면 제거하고 rotate한다.
