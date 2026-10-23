# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Audit finding
IDs refer to [`docs/AUDIT.md`](docs/AUDIT.md).

## [Unreleased]

### Added

- P2 proposal (milestones M7 to M10 and decisions D-10 to D-15) in `docs/ARCHITECTURE.md`.
- Error bars on the VES curve (D-10): one standard error of the mean, $K \cdot s / \sqrt{n}$,
  at positions with two or more valid readings, in the colour of their MN segment, with a
  legend entry and a switch above the curve. A bar that reaches zero is dotted down to the
  bottom of the plot and its point is circled. The axes extend to include the bar ends.
- `plotting.SoundingErrorBar`, `plotting.sounding_error_bar`, and the `error_bars` option of
  `create_sounding_figure`.
- Standard-error column in the table of positions, and a caption with the number of
  positions that have an error bar.

## [0.3.0] - 2026-10-22

### Added

- `georesistivity app` command (also `python -m georesistivity app`) that starts the interface
  from any directory, with `--lan`, `--port`, and `--no-browser` options.
- `georesistivity.services`: Streamlit-free use cases for evaluating a measurement
  submission (`MeasurementInput`, `SubmissionOutcome`, `evaluate_submission`).
- Phase 3 architecture in `docs/ARCHITECTURE.md`.
- `georesistivity.geometry`: geometric factor K for Schlumberger (exact formula, MN as the full
  spacing), Wenner-alpha, dipole-dipole, pole-dipole, and the general four-electrode layout,
  plus the standard field-sheet spacings and `schlumberger_k_table`.
- Measurement form option **Calculate K (Schlumberger)**: K from AB/2 and MN, with the
  geometry recorded as the K source.
- K calculator in the interface for every supported array.
- `georesistivity k` (K per array and the field-sheet K table) and `georesistivity calc` (rho_a
  of one reading).
- MN on measurements (`Measurement.mn_original`, `MeasurementResult.mn_m`) and MN columns in
  the table and CSV (C-05).
- `MeasurementWarning.SCHLUMBERGER_WIDE_MN` for (AB/2)/(MN/2) below 4.
- `units.split_quantity` and `format_significant(grouping=False)`.
- **Field sheet (VES)** tab: a digital Schlumberger sheet pre-filled with the 45 positions of
  the standard paper sheet, overlap readings by MN segment, repeated readings combined as the
  mean of DeltaV/I (D-7), exclusions with a mandatory reason, marker colours, live table of
  positions and log-log curve with equal decades, and points and readings CSV exports.
- `georesistivity.stacking`, `georesistivity.survey`, and `georesistivity.field_sheet` for
  repeated-reading statistics, sounding points, and the sheet rows.
- `plotting.create_sounding_figure` and `io.sounding_points_to_csv` /
  `io.sounding_readings_to_csv`.
- `MeasurementWarning.STACK_HIGH_VARIATION` and `STACK_MIXED_SIGNS`.
- Project files (`*.geores.json`, schema version 1, `georesistivity.project`): survey details,
  the field sheet as typed, its settings, and the single measurements, validated on load with
  the JSON path of each problem, and migrated from older versions.
- **Survey details** form, **Open project** and **Save project**, per-session **autosave**
  under `~/GeoResistivity/autosave`, and **Restore** of earlier sessions (U-03).
- Field-sheet **templates** with AB/2, MN, and marker colours (`georesistivity.storage`).
- `georesistivity app --no-autosave`, `GEORESISTIVITY_HOME`, and `GEORESISTIVITY_AUTOSAVE`.
- Field-sheet rows with only DeltaV or only I are reported as incomplete instead of invalid.
- **Import CSV** tab (`georesistivity.csv_import`): UTF-8 or Windows-1252 files with `;`, `,`,
  or tab, one decimal convention per file (D-1), automatic and editable column mapping,
  every rejected row reported with line, column, and reason, and import into the field sheet
  (replace or add) or the single measurements. Exports round-trip exactly.
- `validation.parse_number_with_decimal`, `validation.is_ambiguous_number_text`, and
  `formatting.format_for_input` for values that read back unambiguously.
- **Bilingual interface**, Brazilian Portuguese by default, with a Language selector
  (`georesistivity.app.i18n`); catalogs are checked for the same entries and placeholders (U-05).
- `georesistivity.messages`: every input error carries a message code (`Problem`) so it can be
  translated; `str(error)` keeps the same English text.
- Translatable figure labels (`SpacingFigureLabels`, `SoundingFigureLabels`).
- `examples/synthetic_ves_excel_pt_br.csv`, a synthetic sounding in Excel pt-BR format, and its
  curve in `docs/images/`.

### Changed

- `GeometricFactorOutcome.issues` holds `ParameterIssue` objects instead of tuples.
- An invalid date in a project file reads "must be a date written as YYYY-MM-DD".
- The interface opens on the field sheet; the single-measurement form, K calculator, and
  session list moved to the **Single measurement** tab.
- The Streamlit interface moved into the package as `georesistivity.app`, with typed session
  access in `georesistivity.app.state`. `app/app.py` remains as a compatibility entry point.
- The table and CSV gain `MN`, `MN unit`, and `MN [m]` columns.
- **Security:** the interface started with `georesistivity app` listens on `localhost` only.
  Streamlit's default listens on every network interface; network access now requires
  `--lan`.

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
