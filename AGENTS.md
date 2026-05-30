# AGENTS.md

이 저장소는 `pykma`, `pyopinet`과 같은 작업 형태를 따른다.

## 문서 언어 정책

이 저장소의 **모든 Markdown/RST 문서는 한글로 작성한다**. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지한다.

설명 문장, 절제목, 표 column 헤더, 빠른 시작 가이드, 일지 항목은 한글로 적는다. 새 문서를 만들 때 영문 초안을 두지 않는다 — 처음부터 한글로 쓴다.

## 역할

이 저장소(GitHub/PyPI 이름 `python-krex-api`, import 패키지 이름 `krex`)는 한국도로공사 OpenAPI (`data.ex.co.kr`, `data.go.kr`)를 Python 환경에서 쉽게 사용할 수 있도록 제공하는 **OpenAPI 클라이언트 라이브러리**다. API 명세 변환, 데이터 정규화, 로컬 유효성 검사 및 에러 매핑을 핵심 가치로 삼으며, Streamlit 등 시각화나 도메인 가시 레이어는 라이브러리 소비자 앱이 담당한다.

## 식별자 (혼동 방지)

| 항목 | 값 |
|------|----|
| GitHub 저장소 이름 | `python-krex-api` |
| PyPI 패키지 이름 | `python-krex-api` |
| import 경로 | `import krex` / `from krex import KrexClient` |
| 데이터 소스 | 한국도로공사 OpenAPI (`data.ex.co.kr`, `data.go.kr`) |
| API 인증 키 변수 | `KEX_EX_API_KEY`, `DATA_GO_KR_SERVICE_KEY` |

## 개발 환경 정책

PC 개발은 Windows 호스트에서 직접 진행한다.
- **Python 버전**: Python 3.11+
- **Unit test**: 네트워크를 절대 직접 호출하지 않는다. Fake session 또는 JSON fixture를 사용한다.
- **의존성 관리**: `pyproject.toml`을 기준으로 하며, 개발 및 디버그용 의존성은 명시된 optional-dependencies에 격리한다.

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `SKILL.md`
4. `API_COVERAGE.md`, `endpoints.md`
5. `codes.md`, `error-codes.md`
6. 기존 코드와 테스트
7. 최소한의, 되돌릴 수 있는 가정

## 절대 하지 말 것 (DO NOT)

1. **`main` 직접 푸시 금지**: 반드시 feature 브랜치 + PR 머지 과정을 거친다.
2. **API key 평문 커밋 금지**: `.env`에 키를 관리하되 절대 커밋하지 않는다. `data.ex.co.kr`에는 `KEX_EX_API_KEY`, `data.go.kr`에는 `DATA_GO_KR_SERVICE_KEY` 환경 변수를 사용한다. `KrexClient` 인스턴스 표현식(`__repr__`)이나 실패 메시지, 문서 등에 API 키가 노출되지 않도록 처리한다.
3. **Unit test에서 network 호출 금지**: 가짜 세션(Fake Session)이나 fixture 파일(JSON 등)을 사용한다.
4. **Stable 의미가 있는 반환값을 raw string으로 노출 금지**: raw string보다는 typed Pydantic model 또는 enum을 제공한다.
5. **모호한 raw 주소 데이터에서 법정동 코드 추측 금지**: 공개 주소 데이터는 provider 원문 문자열 그대로 보존한다.
6. **`routeNo`, `unitCode`, branch code, office code 등의 leading zero 제거 금지**: 0이 앞에 붙는 코드는 반드시 문자열 타입으로 보존한다.
7. **Debug UI 의존성을 이 library에 포함 금지**: Streamlit 등의 디버그 UI 도구는 배포 패키지 코어 의존성에서 철저히 제외한다.
8. **임시/캐시 파일 커밋 금지**: `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.venv` 및 가상환경 관련 파일은 절대 커밋하지 않는다.
9. **독립된 wrapper 신규 작성 남발 금지**: sibling library에 검증된 provider endpoint 구현이 있으면 기존 `KrexClient` namespace로 포팅하여 재사용성을 극대화한다.

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

## 작업 후 체크리스트

- [ ] `python -m compileall src/krex tests` 통과
- [ ] `python -m pytest` 통과
- [ ] `python -m mypy src/krex` 통과 (설치되어 있는 경우)
- [ ] `ruff check .` 통과 (설치되어 있는 경우)
- [ ] `.pytest_cache`, `.mypy_cache`, `.ruff_cache` 등이 커밋 대상에서 제외되었는지 확인

## 검증

```bash
python -m compileall src/krex tests
python -m pytest
```

실제 `data.ex.co.kr` 및 `data.go.kr` 검증은 의도적으로 할 때만 다음 명령어를 사용한다:
```powershell
$env:KEX_LIVE="1"
python -m pytest -m live -vv
```
