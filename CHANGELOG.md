# Changelog

All notable changes to this project are recorded here.

## 0.1.0 - 2026-04-30

Initial package scaffold and first implementation pass.

### Added

- `KrexClient` with `traffic`, `tollfee`, `restarea`, `facility`, `admin`, and
  `reference` namespaces.
- `data.ex.co.kr` and `data.go.kr` HTTP helpers with retry handling and
  provider error-code mapping.
- Public response models for key response types:
  `TrafficByIc`, `TrafficFlow`, `Incident`, `TollFee`, `Tollgate`,
  `RestArea`, `FoodPrice`, `Route`, and `Page`.
- Stable enum code tables for car type, TCS type, road operator, direction,
  traffic time unit, congestion level, and discount type.
- Conversion helpers for API string values: dates, numbers, Y/N flags, and
  single-item response normalization.
- Network-free pytest suite covering query construction, parsing, local
  validation, body-level provider errors, retry behavior, and malformed
  responses.
- Documentation set:
  `README.md`, `endpoints.md`, `codes.md`, `error-codes.md`, `SKILL.md`,
  `AGENTS.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`.
- Existing remote `LICENSE` preserved and package metadata aligned to
  GPL-3.0-or-later.

### Validation

- `python -m compileall src/krex tests`
- `python -m pytest`
- `python -m pytest --cov=krex --cov-fail-under=90`
- `python -m mypy src/krex`

`ruff` was not available in the initial local environment.

## Unreleased

### Added

- Live `data.ex.co.kr` tests gated by `KEX_LIVE=1` and local `KEX_EX_API_KEY`.
- `KrexCode` enum base with `values()`, `labels()`, `choices()`, and
  `from_label()` helpers for external forms and validators.
- `restarea.disabled_facility()` and `restarea.bus_transit()` raw wrappers.
- `API_COVERAGE.md` to track documented, implemented, typed, raw, and
  live-verified API status.
- `CoordinateSystem`, `kraddr.base.PlaceCoordinate`, and `RawCoordinate` public
  coordinate types.
- `kraddr.base.Address` public address type on rest-area address models. Krex
  address strings populate the `Address` display value and region names, while
  provider legal-dong codes are preserved when present.
- `Page` sequence-like helpers: iteration, `len(page)`, truthiness, `first`,
  and `is_empty`.
- Standard `coordinate: PlaceCoordinate | None` fields for rest areas,
  tollgates, and rest-area weather while preserving existing `lat`/`lon` and
  `x`/`y` fields.
- Pydantic v2 public response models with frozen instances, validation,
  `model_dump()`, and JSON schema support.
- Korean Python docstrings and documentation rules requiring project-relative
  file paths.
- Agent workflow notes for the Windows `rg.exe` access-denied fallback and
  explicit UTF-8 PowerShell reads.
- `restarea.route_facilities()`, `restarea.fuel_prices()`, and
  `restarea.convenience_facilities()` for Krex 휴게소 master 후보, 휴게소
  주유소 가격, 노선별 편의시설 조회.
- `RestAreaRouteFacility` and `RestAreaFuelPrice` Pydantic models.

### Fixed

- `KrexHttp` now creates a real httpx client when `session=None` is passed
  explicitly through `KrexClient`.
- API keys are hidden from `KrexHttp` repr output.
- `data.ex.co.kr` default base URL now uses HTTPS.
- `data.ex.co.kr` responses with endpoint-named top-level arrays, such as
  `trafficIc`, are normalized.
- `trafficIc` parsing now handles real field variants: `sumDate`, `sumTm`,
  `inoutType`, and `trafficAmout`.
- Empty successful `data.ex.co.kr` responses preserve `count=0` as
  `Page.total_count == 0`.
- Conversion helpers now accept common unit-suffixed numeric values such as
  `1,994원` and O/X boolean flags observed in Krex rest-area APIs.
- Rest-area route facility parsing now tolerates real records where
  `serviceAreaName` is empty while code and facility metadata are present.
