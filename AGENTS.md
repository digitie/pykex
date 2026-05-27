# Agent Notes

이 저장소는 `pykma`, `pyopinet`과 같은 작업 형태를 따른다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지한다.

## 반드시 지킬 것

- API key를 commit하지 않는다. `data.ex.co.kr`에는 `KEX_EX_API_KEY`, `data.go.kr`에는 `DATA_GO_KR_SERVICE_KEY`를 사용한다.
- `KrexClient()`는 환경 변수가 없을 때 가까운 local `.env`를 읽을 수 있지만, committed test에서는 temporary fixture를 통하지 않고 의존하지 않는다.
- Unit test는 network를 호출하지 않는다. Fake session 또는 fixture를 사용한다.
- 문서의 파일 위치는 `src/krex/client.py`처럼 프로젝트 기준 상대 경로로 쓴다.
- Python docstring과 설명 주석은 provider 원문이나 code identifier를 보존하는 경우를 제외하고 한글로 쓴다.
- Windows workspace에서 `rg.exe`가 `Access is denied`로 실패하면 PowerShell `Get-ChildItem`과 `Select-String -Encoding UTF8`을 사용한다.
- UTF-8 Markdown은 PowerShell에서 `Get-Content -Encoding utf8`처럼 명시 encoding으로 읽는다.
- 안정된 의미가 있는 공개 반환 값은 raw string보다 typed Pydantic model 또는 enum으로 제공한다.
- 공개 WGS84 좌표는 모델의 `lat`/`lon` field로 노출하고, 모호한 raw 좌표는 따로 노출한다.
- 공개 주소 데이터는 provider 원문 문자열로 보존한다. Free-form 주소에서 법정동 코드를 추측하지 않는다.
- Leading zero가 중요한 `routeNo`, `unitCode`, branch code, office code는 문자열로 보존한다.
- 외부 API 작업을 시작하기 전 direct public API rule을 먼저 적용한다. Provider별 wrapper/adapter/gateway layer를 새로 만들지 않는다.
- TripMate나 `python-krtour-map`에 필요한 endpoint, pagination, cursor, exception, raw payload 계약은 downstream facade가 아니라 이 package의 공개 API로 안정화한다.
- Korean public API가 단일 item일 때 `dict`, 여러 item일 때 `list`를 반환할 수 있음을 항상 처리한다.
- `data.ex.co.kr`의 endpoint-named top-level array(`trafficIc` 등)를 처리한다.
- HTTP status만 믿지 말고 body-level API result code를 확인한다.
- API key가 repr, 실패 message, commit, 문서에 노출되지 않게 한다.
- Debug UI 의존성은 이 library에 넣지 않는다. 재현 가능한 case는 `KrexClient.debug_call()`과 JSON fixture로 관리한다.
- sibling library에 검증된 provider endpoint 구현이 있으면 별도 wrapper가 아니라 기존 `KrexClient` namespace로 port한다.

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
- agent workflow/repeated mistakes: `SKILL.md`와 이 파일
- 문서 스타일 규칙: `CONTRIBUTING.md`, `SKILL.md`, 이 파일을 함께 갱신

## Commit hygiene

- Push 전에 `python -m compileall src/krex tests`와 `python -m pytest`를 실행한다.
- `mypy`가 설치되어 있으면 `python -m mypy src/krex`를 실행한다.
- 실제 `data.ex.co.kr` 검증은 의도적으로 할 때만 `$env:KEX_LIVE="1"; python -m pytest -m live -vv`로 실행한다.
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, 가상환경은 commit하지 않는다.
- 실패 endpoint 하나를 되돌릴 수 있을 만큼 commit scope를 유지한다.
