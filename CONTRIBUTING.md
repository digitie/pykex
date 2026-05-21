# Contributing

`python-krex-api` is built to stay boring in the best way: small modules, explicit
models, network-free tests, and documentation that captures every sharp edge we
discover.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Before You Change Code

Read the documents that match your task:

- `endpoints.md` for endpoint path, parameters, and response fields.
- `codes.md` for code tables and enum names.
- `error-codes.md` for provider error mapping.
- `SKILL.md` and `AGENTS.md` for implementation rules and repeated mistakes.

## Adding An Endpoint

1. Add or confirm the endpoint entry in `endpoints.md`.
2. Add code enums in `src/krex/codes.py` if the endpoint uses stable public codes.
3. Add a Pydantic model in `src/krex/models.py` only when the response schema is known.
4. Add the client method in the correct namespace in `src/krex/client.py`.
5. Add tests for query parameters, response parsing, single-object normalization,
   provider errors, malformed shapes, and local validation.
6. Update README examples only for endpoints that users should call directly.

If the path or schema is not verified, return `Page[dict]` and document that
status clearly. We can always make a typed model later; removing a wrong public
model is harder.

## Debug Fixtures

The debug UI workflow is fixture-first:

- Keep Streamlit or other UI dependencies outside this library.
- Use `KrexClient.debug_call()` to capture input, request, response, parsed,
  processed, trace, catalog, and error fields in a `DebugRun`.
- Keep `src/krex/catalog.py` updated so debug UIs can show human-readable
  dataset names and service-key request links.
- Save meaningful cases with `krex.save_fixture()` under
  `tests/fixtures/{function}/{case}.json`.
- Never store API keys, Authorization headers, or token values. The fixture
  writer redacts known sensitive keys, but review generated files before
  committing them.
- Add or update `tests/runners.py` when a fixture targets a new function.
- Let `tests/test_generated_fixtures.py` replay fixture raw responses; do not
  generate one pytest file per case.

## Porting From Sibling Libraries

When `pykma`, `pyopinet`, or another sibling project already has a tested
implementation for the same provider endpoint, prefer porting that behavior
directly into the existing `KrexClient` namespace. Do not add an extra standalone
wrapper/client just to mirror the source library if the endpoint already fits
`src/krex/client.py`.

This may be a larger patch than the smallest local edit, but it keeps proven
field mappings, sentinel handling, and validation rules intact while avoiding
duplicated abstractions.

## Testing

Required for ordinary changes:

```bash
python -m compileall src/krex tests
python -m pytest
python -m mypy src/krex
```

For broader changes:

```bash
python -m pytest --cov=krex --cov-fail-under=90
ruff check .
```

`ruff` may not be installed in every local environment. If it is unavailable,
say that in the PR or commit notes.

## Live API Tests

Default tests must not call real APIs. Live tests should be marked:

```python
@pytest.mark.live
def test_real_endpoint(...):
    ...
```

Live tests must skip cleanly when `KEX_EX_API_KEY` or `DATA_GO_KR_SERVICE_KEY` is not
set. Never commit real response files that contain keys, account details, or
other sensitive values.

## Documentation Expectations

Any behavior change should update documentation in the same patch. This keeps
the project useful for humans and for future agent sessions.

Common placements:

- `README.md`: public usage, architecture, validation status.
- `endpoints.md`: endpoint contracts.
- `codes.md`: public code tables.
- `error-codes.md`: exception mapping.
- `SKILL.md` / `AGENTS.md`: workflow rules and repeated mistakes.

Style rules:

- Document file locations as project-root-relative paths such as
  `src/krex/client.py`, not local absolute paths.
- Write Python docstrings and explanatory comments in Korean unless quoting
  provider text or preserving public code/protocol identifiers.
- In the Windows workspace, `rg.exe` may fail with `Access is denied`; use
  PowerShell enumeration with `Select-String` as the fallback.
- Read UTF-8 Markdown with explicit PowerShell encoding, for example
  `Get-Content -Path README.md -Encoding utf8`, before assuming Korean text is
  corrupted.

## Security

- Do not commit `.env` files.
- Do not paste API keys into tests or examples.
- If a key is accidentally committed, remove it and rotate it.
