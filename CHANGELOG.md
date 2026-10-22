# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Audit finding
IDs refer to [`docs/AUDIT.md`](docs/AUDIT.md).

## [0.2.0] - 2026-10-22

### Added

- `AmbiguousNumberError` for thousands-like input such as `1,000` or `3.134`, with a message
  suggesting both unambiguous spellings (V-01).
- `MeasurementWarning.NEGATIVE_APPARENT_RESISTIVITY` on `MeasurementResult.warnings`, shown in
  the interface and recorded in a new `Warnings` table and CSV column (C-01).
- `MeasurementFieldError`, raised by `calculate_measurement` with the name of the offending
  field (U-01).
- `georesistivity.formatting` with `format_significant` and `format_full_precision` for
  pt-BR and en number formats (C-04).
- Number-format and CSV-format preferences in the interface sidebar.
- `excel-pt-br` CSV dialect: UTF-8 with BOM, semicolon separator, decimal comma (I-01).
- Warning when a measurement is identical to the previous one (U-02).
- Unit aliases for the Greek letter mu (`μV`, `μA`) next to the micro sign (V-03).
- `.streamlit/config.toml`, `LICENSE` (MIT), `py.typed`, `CHANGELOG.md`, Dependabot, and
  pre-commit configuration.
- Interface tests with Streamlit `AppTest` and property-based tests with Hypothesis
  (T-02, T-03).

### Changed

- **Breaking:** a negative geometric factor $K$ is now rejected ("must be positive"). It was
  previously accepted and produced a negative $\rho_a$ (C-01).
- **Breaking:** a zero or negative AB/2 is now rejected (C-01).
- **Breaking:** `parse_number` rejects thousands-like values, Python digit separators
  (`1_000`), and non-ASCII digits that were previously accepted (V-01, V-02).
- **Breaking:** the distribution is renamed from `georesistivity-calculator` to
  `georesistivity`, and Streamlit moves to the optional `[app]` extra. Install the
  interface with `pip install -e ".[app]"` (Q-02).
- Unit conversion shifts the typed decimal value by an exact power of ten, so SI values no
  longer carry float artifacts such as `0.009000000000000001` (C-03).
- Results are displayed with four significant digits in the selected number format, pt-BR by
  default, instead of two decimals in English format (C-04).
- Numeric fields are cleared after a measurement is added; units and K source are kept
  (U-02).
- Unit notation is `Ω·m` in the interface and plot (U-06).
- The sidebar starts collapsed on small screens, and the developer toolbar is hidden (U-04).
- `import georesistivity` no longer loads pandas or Matplotlib (Q-04).
- CI runs on Python 3.11 to 3.13 on Linux, Windows, and macOS, with mypy strict, coverage
  gate, and pip-audit; actions are pinned to commit SHAs (T-04).

### Fixed

- Values that overflow to infinity or underflow to zero during unit conversion are rejected
  instead of being stored (C-02).
- CSV export neutralizes spreadsheet formula injection in free-text columns (S-01).
- The plot-scale selector can no longer be left without a selection (U-07).
- The sample-dataset test no longer depends on the working directory (T-01).
- Two strict type-checking errors (Q-01).

### Security

- Streamlit usage-statistics collection is disabled (S-02).

## [0.1.0]

- Initial modular release: apparent-resistivity calculation, unit conversion to SI, numeric
  validation, session table, spacing plot, and CSV export.
