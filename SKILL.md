---
name: python-krex-api
description: Build, extend, test, or troubleshoot the Python client for Korea Expressway Corporation OpenAPIs exposed through data.ex.co.kr and data.go.kr.
---

# python-krex-api Skill

Use this guide when working on the `python-krex-api` Python library.

## Scope

This project wraps Korea Expressway Corporation public APIs from:

1. `data.ex.co.kr` with `key` and `type=json`
2. `data.go.kr` / `api.data.go.kr` with `serviceKey` and JSON response options

The public package import name is `krex`; the distribution name is
`python-krex-api`.

## Repository Rules

- Read `endpoints.md`, `codes.md`, and `error-codes.md` before changing endpoint behavior.
- Read `API_COVERAGE.md` before claiming an API is supported or live-verified.
- Keep the implementation shape aligned with `pykma` and `pyopinet`:
  `src/krex/client.py`, `src/krex/_http.py`, `src/krex/_convert.py`,
  `src/krex/codes.py`, `src/krex/models.py`, `src/krex/catalog.py`,
  `src/krex/exceptions.py`, `src/krex/debug.py`.
- Do not add live network calls to ordinary tests.
- Do not commit API keys or generated caches.
- Write file locations in documents as project-root-relative paths, for example
  `src/krex/client.py`; avoid local absolute paths.
- Write Python docstrings and explanatory comments in Korean unless preserving
  provider text, public code identifiers, or protocol literals.
- In this Windows workspace, `rg.exe` may be present but fail with
  `Access is denied`. Use PowerShell enumeration as the fallback:
  `Get-ChildItem -Recurse -File | Select-String -Pattern "..."`.
- When reading Markdown or other UTF-8 text in PowerShell, pass
  `-Encoding utf8` to `Get-Content` or `Select-String` to avoid garbled Korean
  output.
- Prefer immutable Pydantic models for public return models and `StrEnum` for
  stable code values.
- If an endpoint path is uncertain, expose it as `Page[dict]` first and document
  the uncertainty instead of pretending the schema is stable.
- When `pykma`, `pyopinet`, or another sibling library already contains a
  working implementation for the same provider endpoint, port the tested
  behavior into the existing `KrexClient` namespace. Avoid a new standalone
  wrapper/client unless the provider, authentication model, or response shape
  truly needs a separate abstraction. This direct-port preference may be more
  important than keeping the patch to the smallest possible local edit.

## API Key Rules

- `KEX_EX_API_KEY`: `data.ex.co.kr` key.
- `KEX_GO_API_KEY`: `data.go.kr` key. Prefer the decoded key when using
  `httpx` query params.
- `KrexClient()` falls back to the nearest local `.env` when environment
  variables are absent, and normalizes copy-paste whitespace out of keys.
- If a user pastes a key into chat or a file, tell them to rotate it and remove
  the key from the working tree.

## URL and Parameter Rules

`data.ex.co.kr`:

- Base URL: `http://data.ex.co.kr`
- Auth parameter: `key`
- JSON parameter: `type=json`
- Pagination: `numOfRows`, `pageNo`
- Common result shape: `{"code": "SUCCESS", "list": [...]}`

`data.go.kr`:

- Auth parameter: `serviceKey`
- Many service APIs use `_type=json`
- Some standard data APIs use `type=json`
- Common result shape:
  `{"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [...]}}}}`

## Error Mapping

Never rely on HTTP status alone. Inspect body-level result codes.

- Auth: `INVALID_KEY`, `EXPIRED_KEY`, `NO_REGISTERED_KEY`, `20`, `21`, `30`, `31`, `32`, `33`
- Quota: `EXCEEDED_LIMIT`, `22`, HTTP `429`
- Missing parameter: `INVALID_REQUEST_PARAMETER`, `11`
- Invalid parameter: `INVALID_PARAMETER_VALUE`, `10`
- No data: `NO_DATA`, `03`
- Server/transient: `SYSTEM_ERROR`, `SERVICE_TIMEOUT`, `SERVICE_UNAVAILABLE`, `01`, `02`, `04`, `05`, HTTP `5xx`

## Conversion Rules

- Preserve route, tollgate, office, and code values as strings.
- Convert API dates only at the model boundary.
- Convert numeric metrics (`speed`, `tollFee`, `trafficVol`) to `float` or `int`.
- Convert Y/N fields to `bool | None`.
- Keep public models based on `KrexModel` so external callers can rely on
  `model_dump()`, `model_validate()`, and `model_json_schema()`.
- Expose standard WGS84 positions as `kraddr.base.PlaceCoordinate(lat, lon)`. Keep legacy
  `lat`/`lon` and `x`/`y` fields when already public, but prefer `coordinate`
  for new code.
- Expose address data as `kraddr.base.Address`. Free-form address strings may fill
  display text and region names, but legal-dong codes must come from provider
  fields or verified external lookup results such as VWorld boundary data.
- Preserve ambiguous raw coordinates as `RawCoordinate` with a
  `CoordinateSystem`.
- Normalize single-item `dict` and multi-item `list[dict]` to the same internal list shape.

## Tests Required For New Endpoints

Every new endpoint wrapper should include:

- query parameter test, including enum to raw API code conversion;
- success parsing test with string numeric/date inputs;
- single-item `dict` normalization test when applicable;
- body-level provider error mapping test;
- malformed response shape test;
- missing required local parameter test.

## Documentation Required For New Endpoints

Update documentation in the same change:

- `README.md`: add user-facing usage only when the endpoint is meant to be public.
- `endpoints.md`: add source portal, path, method name, parameters, and known response fields.
- `API_COVERAGE.md`: update implementation state and live verification status.
- `src/krex/catalog.py`: update human-readable dataset names, provider,
  endpoint, fixture status, and service-key request URLs.
- `codes.md`: add any stable code table used by public parameters or models.
- `error-codes.md`: add newly observed provider error codes.
- `AGENTS.md` or this `SKILL.md`: add any repeated mistake discovered during implementation.
- `CONTRIBUTING.md`, `AGENTS.md`, and this `SKILL.md`: update documentation
  style rules such as path notation or Python docstring language.

## Repeated Mistakes To Avoid

- Do not use `_type` for `tn_pubr_public_rest_area_api`; it uses `type`.
- Do not convert `routeNo="0010"` or `unitCode="101"` to integers.
- Do not treat `NO_DATA` as success unless `strict_no_data=False`.
- Do not let raw API strings leak for stable code values that have enums.
- Do not add endpoint paths from guesses without documenting that they are unverified.
- Do not make tests depend on current public portal data.
- Do not add Streamlit or debug UI dependencies to this library. UI projects
  should import the wheel or editable install and use `KrexClient.debug_call()`.
- Do not generate one pytest file per saved API case. Save JSON under
  `tests/fixtures/` and replay it through `tests/test_generated_fixtures.py`.
- Do not commit fixture files until API keys, Authorization headers, and token
  fields are visibly redacted.
- Do not parse money or traffic values by hand at call sites. Keep conversion in
  `src/krex/_convert.py` or model parser helpers.
- Do not expose a new Pydantic model until at least one realistic fixture or fake
  response locks the expected field names.
- Do not introduce ad-hoc `(lat, lon)` tuples in public models. Use
  `PlaceCoordinate.latlon` only as a convenience alias.
- Do not assume `data.ex.co.kr` always uses `list`; real responses can use an
  endpoint-named top-level array such as `trafficIc`.
- Do not create a second wrapper layer for a provider endpoint that already fits
  the existing `KrexClient` namespace; port the sibling-library parser/model
  behavior directly and document any intentional differences.
- Do not use `payload.get("count") or ...` for counts. Real empty responses use
  `count=0`, and that must stay `0`.
- Do not let API keys appear in model repr output.
- Do not use dataclass-only helpers such as `asdict()` or `__post_init__`;
  use Pydantic validators and `model_dump()` instead.
- Do not retry `rg` repeatedly after an `Access is denied` failure in this
  workspace; switch to PowerShell file enumeration immediately.
- Do not diagnose Korean Markdown as broken before checking it with explicit
  UTF-8 encoding in PowerShell.

## Release Checklist

Before pushing a release branch or first public commit:

```bash
python -m compileall src/krex tests
python -m pytest
python -m pytest --cov=krex --cov-fail-under=90
python -m mypy src/krex
```

`ruff check .` is also expected when the environment has Ruff installed.

Live `data.ex.co.kr` tests:

```powershell
$env:KEX_LIVE="1"
python -m pytest -m live -vv
```

Live tests may read `KEX_EX_API_KEY` from local `.env`, which is ignored by Git.

## Verification

Run at minimum:

```bash
python -m compileall src/krex tests
python -m pytest
```

When type tooling is installed:

```bash
python -m mypy src/krex
ruff check .
```
