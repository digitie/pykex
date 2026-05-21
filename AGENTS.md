# Agent Notes

This repository follows the same working shape as `pykma` and `pyopinet`.

## Non-negotiables

- Do not commit API keys. Use `KEX_EX_API_KEY` for `data.ex.co.kr` and
  `DATA_GO_KR_SERVICE_KEY` for `data.go.kr`.
- `KrexClient()` may read the nearest local `.env` when those environment
  variables are absent; never rely on that in committed tests except through
  temporary `.env` fixtures.
- Unit tests must not call the network. Use fake sessions or fixtures.
- In documents, write file locations as project-root-relative paths such as
  `src/krex/client.py`; do not use local absolute paths.
- Write Python docstrings and explanatory comments in Korean unless quoting
  provider text or preserving code identifiers.
- In this Windows workspace, `rg.exe` can fail with `Access is denied`; when it
  does, search with PowerShell file enumeration and `Select-String` instead.
- Read UTF-8 Markdown with explicit encoding, for example
  `Get-Content -Path README.md -Encoding utf8`, so Korean text does not look
  corrupted in PowerShell output.
- Keep public return values typed Pydantic models or enum values, not raw strings,
  whenever the field has a stable meaning.
- Use `kraddr.base.PlaceCoordinate(lat, lon)` for public WGS84 coordinates and
  expose raw ambiguous coordinates separately.
- Use `kraddr.base.Address` for public address data. Do not guess a 10-digit
  legal-dong code from free-form address text; preserve it only when the
  provider row or a verified geocoder/boundary lookup supplies it.
- Preserve code-like identifiers exactly as strings when leading zeroes matter
  (`routeNo`, `unitCode`, branch codes, office codes).
- Before starting external API work, apply the direct public API rule first:
  do not create provider-specific wrapper/adapter/gateway layers.
- Provide stable public clients, typed models, enums, and helpers that downstream
  users can call directly.
- If TripMate or `python-krtour-map` needs missing endpoints, pagination,
  cursors, exceptions, or raw payload contracts, stabilize them in this package
  instead of adding a temporary facade downstream.
- Remove long-lived compatibility aliases and pass-through wrappers when the
  calling code can be updated to the stable public API.
- Handle `list` and single `dict` item shapes. Korean public APIs often switch
  between them when only one item is returned.
- Handle endpoint-named top-level arrays from `data.ex.co.kr`, such as
  `trafficIc`.
- Always inspect body-level API result codes. `data.go.kr` commonly returns
  HTTP 200 for application errors.
- Keep API keys out of repr strings, failure messages, commits, and docs.
- Keep debug UI dependencies out of this library. Use `KrexClient.debug_call()`
  and JSON fixtures for replayable UI-discovered cases.
- When a sibling library such as `pykma` or `pyopinet` already has a verified
  implementation for the same provider endpoint, port that behavior directly
  into the existing `KrexClient` namespace instead of adding a separate wrapper
  layer. This preference can outweigh a narrowly minimal diff when it prevents
  duplicated abstractions and preserves proven parsing rules.

## Module Ownership

- `src/krex/_http.py`: transport, retries, API envelope/error mapping.
- `src/krex/_convert.py`: small conversion helpers at the response boundary.
- `src/krex/codes.py`: enums and code labels.
- `src/krex/models.py`: public Pydantic return models.
- `src/krex/client.py`: high-level endpoint namespaces and parsing.
- `src/krex/catalog.py`: implemented API catalog, human-readable dataset names,
  and service-key request URLs for debug UIs.
- `src/krex/debug.py`: `DebugRun`, JSON conversion, redaction, fixture writing.
- `API_COVERAGE.md`: source-of-truth for implemented vs live-verified API
  status.

## Test Bar

Every new endpoint wrapper should include tests for:

- query parameter names and enum conversion;
- list and single-object response normalization;
- required parameter validation;
- malformed response shape;
- body-level API errors;
- at least one successful typed model conversion.
- debug/fixture support when the endpoint is intended to be captured from a UI:
  add a `tests/runners.py` replay mapping and JSON fixture instead of generated
  one-off pytest files.

## Documentation Bar

When behavior changes, update the matching document in the same patch:

- User-facing usage changes: `README.md`.
- Endpoint parameters or response fields: `endpoints.md`.
- Coverage/support status: `API_COVERAGE.md`.
- Code enum changes: `codes.md`.
- Exception or provider error mapping changes: `error-codes.md`.
- Agent workflow or repeated mistakes: `SKILL.md` and this file.
- Documentation style changes: update `CONTRIBUTING.md`, `SKILL.md`, and this
  file together when the rule affects future contributors or agents.

## Commit Hygiene

- Run `python -m compileall src/krex tests` and `python -m pytest` before
  pushing.
- Run `python -m mypy src/krex` when `mypy` is installed.
- Run `$env:KEX_LIVE="1"; python -m pytest -m live -vv` only when deliberately
  validating against the real `data.ex.co.kr` server.
- Do not include `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, or
  virtual environments.
- Keep commits focused enough that a failing endpoint can be reverted without
  losing unrelated documentation.
