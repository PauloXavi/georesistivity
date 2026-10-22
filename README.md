# GeoResistivity

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.62%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![CI](https://github.com/PauloXavi/georesistivity/actions/workflows/ci.yml/badge.svg)](https://github.com/PauloXavi/georesistivity/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

GeoResistivity is a scientific Python application for apparent resistivity calculation,
unit-aware measurement handling, validation, visualization, and CSV export.

The application implements:

$$
\rho_a = K \frac{\Delta V}{I}
$$

where:

- $\rho_a$ is apparent resistivity $[\Omega\cdot m]$;
- $K$ is the geometric factor $[m]$;
- $\Delta V$ is the potential difference $[V]$;
- $I$ is the injected current $[A]$.

> The geometric factor K is either entered by the user or calculated from the electrode
> geometry: Schlumberger in the measurement form, and Schlumberger, Wenner, dipole-dipole,
> pole-dipole, or any four-electrode layout in the K calculator and the command line.

## Overview

GeoResistivity provides a traceable workflow for entering independent measurements,
parsing and validating numeric input, converting units to SI, calculating apparent
resistivity, and preserving both original and converted values. Results can be reviewed in
acquisition order, visualized against optional electrode-spacing metadata, and exported as
CSV.

```text
Measurement input
      |
      v
Parsing & validation
      |
      v
Unit conversion to SI
      |
      v
rho_a = K * DeltaV / I
      |
      +--> measurement table (with quality warnings)
      +--> visualization
      +--> CSV export (standard or Excel pt-BR)
```

## Features

- Apparent resistivity calculation.
- Explicit voltage-unit selection.
- Explicit current-unit selection.
- Explicit length-unit selection for the geometric factor $K$.
- Geometric factor $K$ entered directly or calculated from AB/2 and MN with the exact
  Schlumberger formula, with the geometry recorded as the K source.
- K calculator for Schlumberger, Wenner-α, dipole-dipole, pole-dipole, and any four-electrode
  layout.
- Optional AB/2 and MN spacing metadata.
- Decimal-point and decimal-comma parsing.
- Rejection of ambiguous numeric formats, including thousands-like values such as `1,000`
  or `3.134`.
- Explicit conversion to SI units before calculation, exact to the typed decimal value.
- Rejection of non-positive geometric factors and AB/2 values.
- Quality warning for negative apparent resistivity.
- Error messages that name the offending field.
- Preservation of original inputs and converted values.
- Multiple independent measurements in one session.
- Preservation of acquisition order.
- Results displayed with four significant digits in pt-BR or en number format.
- Tabular result display and CSV export in standard or Excel pt-BR format.
- Protection of exported CSV files against spreadsheet formula injection.
- Apparent resistivity versus electrode spacing visualization.
- Optional visualization sorting by AB/2 without reordering the table.
- Linear and log-log plotting.
- Explicit warnings for values incompatible with log-log visualization.
- Removal of the most recent measurement.
- Confirmed clearing of all session measurements.
- Synthetic demonstration dataset provided as an example and used by the I/O test suite.

## Scientific Basis

Apparent resistivity is calculated from the externally supplied geometric factor, measured
potential difference, and injected current:

$$
\rho_a = K \frac{\Delta V}{I}
$$

Dimensionally:

$$
[K] = m
$$

$$
\left[\frac{\Delta V}{I}\right] = \frac{V}{A} = \Omega
$$

Therefore:

$$
[\rho_a] = \Omega\cdot m
$$

The scientific core works internally in volts, amperes, and meters. Values entered in other
supported units are converted explicitly to SI before the calculation is performed. The
conversion shifts the typed decimal value by an exact power of ten, so `9 mV` becomes exactly
`0.009 V` rather than `0.009000000000000001 V`.

The optional geometric factor source records where the externally supplied value of $K$ came
from, such as equipment, a table, or a field sheet. It is metadata only and does not affect the
calculation.

### Geometric factor

$K$ can be typed, as before, or calculated in meters from the geometry. The measurement form
calculates the Schlumberger $K$ from AB/2 and MN:

$$
K = \pi \, \frac{(AB/2)^2 - (MN/2)^2}{MN}
$$

MN is the **full** distance between M and N, as on the standard Schlumberger field sheet, and
must be smaller than AB. The formula is exact, so $K$ stays correct for any MN < AB. A
measurement with $(AB/2)/(MN/2) < 4$ is accepted with the `schlumberger_wide_mn` warning; the
standard field sheet itself goes down to 4.0 (AB/2 = 1.0 m with MN = 0.5 m). The test suite
reproduces all 45 values of that sheet's pre-computed K table to their last printed digit.

The K calculator and `georesistivity k` also cover:

| Array | Parameters | $K$ |
| --- | --- | --- |
| Wenner-α | spacing $a$ | $2\pi a$ |
| Dipole-dipole | dipole length $a$, factor $n$ | $\pi n (n+1)(n+2) a$ |
| Pole-dipole (remote B) | dipole length $a$, factor $n$ | $2\pi n (n+1) a$ |
| General | distances AM, BM, AN, BN | $2\pi / (1/AM - 1/BM - 1/AN + 1/BN)$ |

Each shortcut is tested against the general formula. MN is recorded with the measurement and
exported, but, like AB/2, it does not enter $\rho_a = K \Delta V / I$ once $K$ is known.

### Sign policy

- $K$ must be positive, as it is for conventional four-electrode arrays.
- AB/2 and MN, when supplied, must be positive.
- $\Delta V$ and $I$ keep their sign because the sign convention depends on the acquisition
  setup. A negative $\rho_a$ is kept and flagged with the `negative_apparent_resistivity`
  warning, shown in the interface and recorded in the `Warnings` column. It usually indicates
  reversed polarity, swapped cables, or a reading error.

## Supported Units

The core library supports the following units:

| Quantity | Core/library units | Internal unit |
| --- | --- | --- |
| Voltage | `V`, `mV`, `uV`, `µV` | `V` |
| Current | `A`, `mA`, `uA`, `µA` | `A` |
| Length | `m`, `cm`, `mm`, `km` | `m` |

The Streamlit interface offers `V`, `mV`, and `µV` for voltage; `A`, `mA`, and `µA` for
current; and `m`, `cm`, `mm`, and `km` for length. The core library also accepts the ASCII
forms `uV` and `uA`, and both the micro sign (U+00B5) and the Greek letter mu (U+03BC). Unit
names are case-sensitive, so `mV` (millivolt) is never confused with `MV`.

The geometric factor $K$ is converted to meters. When AB/2 is supplied, it is also converted
to meters and retained as spacing metadata, but it does not participate in the apparent
resistivity equation.

## Numeric Input and Validation

Numeric text input uses ASCII digits, an optional sign, at most one decimal separator, and an
optional exponent:

| Input | Result |
| --- | --- |
| `10.5`, `10,5` | 10.5 |
| `0,125`, `0.125` | 0.125 |
| `1,5e-3` | 0.0015 |
| `1000`, `1000,25` | 1000, 1000.25 |
| `1,000`, `3.134`, `12,500` | rejected as ambiguous |
| `1.234,5`, `1,000,000` | rejected: thousands separators are not accepted |
| `1_000`, non-ASCII digits | rejected |

A value with a single separator after a one-to-three-digit non-zero integer part and exactly
three fractional digits is rejected because it reads equally well as a thousands separator
(`1,000` = 1000) or as a decimal separator (`1,000` = 1.0). The error message suggests both
unambiguous spellings: `1000` for the integer, or `1,0000` for the decimal value.

NaN and infinite values are rejected. A zero current is rejected because it does not produce
a valid calculation. Values that overflow or underflow to zero during unit conversion are
rejected with an explicit message.

## Displayed Results

The latest result is shown with four significant digits in the number format selected in the
sidebar: `pt-BR` (default, `2.232 Ω·m`) or `en` (`2,232 Ω·m`). Very small or very large values
use scientific notation (`2,947 × 10⁻⁴`). The **Converted values** panel shows the SI values
with up to 12 significant digits.

## CSV Export

The sidebar selects the export format:

| Format | Encoding | Separator | Decimal |
| --- | --- | --- | --- |
| Standard | UTF-8 | `,` | `.` |
| Excel pt-BR | UTF-8 with BOM | `;` | `,` |

Use **Excel pt-BR** to open the file directly in Microsoft Excel configured for Brazilian
Portuguese. Free-text cells that start with `=`, `+`, `-`, `@`, a tab, or a carriage return are
prefixed with an apostrophe so that spreadsheet applications do not evaluate them as formulas.

## Field Sheet (VES)

The **Field sheet (VES)** tab is a digital version of the paper Schlumberger sounding sheet:

- The table starts with the 45 (AB/2, MN) positions of the standard sheet, AB/2 from 1.0 to
  320 m and MN from 0.5 to 100 m, with K calculated for each position.
- Type ΔV and I in the rows you read; blank rows are ignored. The units of ΔV and I are
  selected above the table.
- **Overlap readings:** the same AB/2 read with the next MN is a separate row. Each MN forms
  its own segment of the curve, so the shift between segments stays visible.
- **Repeated readings:** add a row with the same AB/2 and MN. Readings at one position are
  combined as $\rho_a = K \cdot \text{mean}(\Delta V_i / I_i)$, so every reading has the
  same weight. The coefficient of variation is shown and flagged above a selectable limit (5% by
  default), as are readings that mix signs.
- **Exclusion:** a reading can be excluded only with a reason. It stays in the readings export
  but not in the result.
- The **Marker** column records the cable or reel marker colour of each AB/2.
- Invalid rows are listed by row number and column without blocking the other rows.
- The table of positions and the curve update as values are typed. The curve uses log-log
  axes with whole decades (at least 1-1000 m and 1-10 000 Ω·m) and equal decade lengths on
  both axes, as on bilog paper, so it can be compared with master curves. Points with quality
  warnings are circled in red.
- **Export points (CSV)** gives one row per position with its statistics; **Export readings
  (CSV)** gives every reading, including excluded ones and their reasons.

- A row with only ΔV or only I is shown as waiting for its other value, not as an error.
- **Survey details** above the sheet record the header of the paper sheet: survey name,
  SEV nº, date, area, place, operator, equipment, azimuth of the AB line, WGS 84 latitude and
  longitude, and notes.

## Projects, Autosave, and Templates

Everything typed in a session (survey details, the field sheet exactly as typed, its units and
CV limit, and the single measurements) can be saved as a project file and is autosaved on this
computer.

- **Save project** in the sidebar downloads a `.geores.json` file named after the SEV number
  and place, for example `SEV-03-Fazenda_Teste.geores.json`. **Open project** loads one and
  replaces the current session; a file that cannot be read or shown changes nothing and the
  message names the problem, for example `sheet.rows[3].delta_v: must be text`.
- **Autosave** writes this session's own copy under `~/GeoResistivity/autosave/` whenever the
  content changes. Each session has its own file, so a laptop and a tablet connected in LAN
  mode never overwrite each other. Files are written atomically, so a crash never leaves a
  half-written copy.
- After a reload or a crash, the sidebar of a new session lists the most recent autosave
  copies (place, number of readings, time) with a **Restore** button.
- **New sheet and templates**, below the sheet, saves the AB/2, MN, and marker colours of the
  current sheet as a template (without readings) and starts new sheets from the standard
  layout or a saved template. Templates live in `~/GeoResistivity/templates/`.

The project file is plain, indented JSON with a `schema_version`. Calculated values are not
stored; they are recomputed from the original values when the file is opened, and files from
older versions are migrated automatically. Set `GEORESISTIVITY_HOME` to keep the local files
in another folder, and start the interface with `--no-autosave` (or set
`GEORESISTIVITY_AUTOSAVE=0`) to turn autosave off, for example on a shared server.

## Importing CSV Files

The **Import CSV** tab brings readings into the field sheet, or measurements with a known K
into the single measurements, from a CSV file. It reads the files GeoResistivity exports, in
both formats, and other spreadsheets:

- **Reading:** UTF-8 (with or without BOM) or Windows-1252, as saved by Excel on Portuguese
  systems; `;`, `,`, or tab as separator, including Excel's `sep=` line. The first rows are
  shown before anything is imported.
- **Decimal separator:** one convention for the whole file, as in the form (D-1). A
  comma-separated file uses a point; otherwise the numbers declare it, for example `1,5` with
  `;`. When the numbers do not settle it, values such as `1,000` are rejected as ambiguous.
  The detected convention is shown and can be changed.
- **Columns:** the target and the column of each field are proposed from the header (English
  export names and common Portuguese names such as Cor, ΔV, Excluir, Motivo) and can be
  changed. Units come from unit columns when present, otherwise from the selectors.
- **Problems:** every row that cannot be imported is listed with its line in the file, its
  column, and the reason, and is left out; the others can be imported.
- **Field sheet:** the import replaces the sheet, using the file's units, or adds the rows
  after the current ones (only with the same units if the sheet already has readings).

Exporting readings or measurements and importing them back gives exactly the same data, in
both CSV formats; the test suite checks this round trip. The bundled
[`examples/sample_measurements.csv`](examples/sample_measurements.csv) imports as eight single
measurements.

## Visualization Behavior

The **Apparent Resistivity vs. Electrode Spacing** graph is displayed only when at least two
recorded measurements contain AB/2. AB/2 remains optional spacing metadata and is not part of
the apparent-resistivity equation. Optional sorting by AB/2 changes only the visualization;
the measurement table remains in acquisition order. Log-log scale requires positive AB/2 and
$\rho_a$ values.

## Quick Start

GeoResistivity requires Python 3.11 or newer.

From the project root:

```bash
git clone https://github.com/PauloXavi/georesistivity.git
cd georesistivity

python -m venv .venv
source .venv/bin/activate

python -m pip install -e ".[app]"
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

Start the application:

```bash
georesistivity app
```

The command works from any directory and opens the interface in the browser. It listens on
this computer only. Useful options:

| Option | Effect |
| --- | --- |
| `--lan` | Also accept connections from other devices on the local network, for example a tablet connected to the laptop's hotspot in the field. Use it only on a trusted network. |
| `--port 8600` | Use another port (default `8501`). |
| `--no-browser` | Do not open a browser window. |
| `--no-autosave` | Do not keep autosave copies; save project files instead. |

`python -m georesistivity app` is equivalent. During development, `python -m streamlit run
app/app.py` from the repository root reloads the interface when files change.

To use only the scientific library, without the web interface, install it without extras:

```bash
python -m pip install -e .
```

### Troubleshooting on macOS

If `import georesistivity` fails with `ModuleNotFoundError` right after an editable install on
Python 3.13, check whether the environment's `.pth` files are marked as hidden:

```bash
ls -lO .venv/lib/python3.*/site-packages/*.pth
```

Python 3.13 ignores hidden `.pth` files. Some synced folders, such as an iCloud Desktop, mark
everything inside dot-directories as hidden. Create the environment in a directory without a
leading dot (for example `python -m venv venv`) or outside the synced folder.

## Example Calculation

Consider the following entirely synthetic measurement:

| Input | Value |
| --- | ---: |
| Delta V | `125 mV` |
| Current | `35 mA` |
| K | `625 m` |
| AB/2 | `20 m` |

The application converts the values to SI:

```text
Delta V = 0.125 V
I       = 0.035 A
K       = 625 m
```

The calculated result is:

```text
rho_a = 2232.142857... ohm.m
```

The interface displays `2.232 Ω·m` in pt-BR format or `2,232 Ω·m` in en format. AB/2 is
metadata associated with the measurement record and is not used in this equation.

With **Calculate K (Schlumberger)**, AB/2 = `20 m` and MN = `2 m` give
$K = \pi (20^2 - 1^2) / 2 = 626.7477...$ m and $\rho_a$ = `2.238 Ω·m` for the same ΔV and I.

## Command Line

```bash
georesistivity k schlumberger --ab2 20m --mn 2m
```

```text
K = 626,747734391 m
```

```bash
georesistivity calc --dv 125mV --i 35mA --ab2 20m --mn 2m
```

```text
rho_a = 2238,38476568 ohm.m
K = 626,747734391 m (calculated: schlumberger (AB/2 = 20 m, MN = 2 m))
```

| Command | Purpose |
| --- | --- |
| `georesistivity app` | Start the interface (see Quick Start). |
| `georesistivity k ARRAY ...` | K for `schlumberger`, `wenner`, `dipole-dipole`, `pole-dipole`, or `general`. |
| `georesistivity k table` | Schlumberger K table by AB/2 and MN; defaults to the standard field-sheet spacings. |
| `georesistivity calc ...` | $\rho_a$ for one reading, with `--k` or with `--ab2` and `--mn`. |

Every length or electrical value takes its unit (`20m`, `2000cm`, `125mV`); write negative
values with an equals sign (`--dv=-125mV`). `--number-format en` prints a decimal point.
`georesistivity COMMAND --help` lists every option.

## Demonstration Data

[`examples/sample_measurements.csv`](examples/sample_measurements.csv) contains the sample
measurements provided as a small example and reference dataset. The I/O test suite reads this
file to verify its structure and scientific consistency, and it can be loaded in the
**Import CSV** tab.

The bundled sample measurements are synthetic and provided for demonstration and testing
purposes.

## Architecture

```text
GeoResistivity/
├── app/
│   └── app.py              # compatibility entry point for `streamlit run`
├── src/georesistivity/
│   ├── app/                # Streamlit interface
│   │   ├── common.py
│   │   ├── field_sheet_view.py
│   │   ├── import_view.py
│   │   ├── main.py
│   │   ├── project_view.py
│   │   └── state.py
│   ├── cli.py
│   ├── core.py
│   ├── csv_import.py
│   ├── field_sheet.py
│   ├── formatting.py
│   ├── geometry.py
│   ├── io.py
│   ├── models.py
│   ├── plotting.py
│   ├── project.py
│   ├── services.py
│   ├── stacking.py
│   ├── storage.py
│   ├── survey.py
│   ├── units.py
│   └── validation.py
├── tests/
├── examples/
├── legacy/
└── docs/
```

| Path | Responsibility |
| --- | --- |
| `src/georesistivity/app/` | Streamlit presentation layer (`main.py`, `field_sheet_view.py`), shared labels (`common.py`), and typed session state (`state.py`). |
| `src/georesistivity/services.py` | Application use cases shared by the interfaces, without Streamlit. |
| `src/georesistivity/cli.py` | The `georesistivity` command. |
| `app/app.py` | Compatibility entry point for `streamlit run app/app.py`. |
| `src/georesistivity/core.py` | Pure scientific calculation and measurement processing. |
| `src/georesistivity/geometry.py` | Geometric factor $K$ of four-electrode arrays and the field-sheet K table. |
| `src/georesistivity/survey.py` | Sounding points (AB/2, MN), readings, exclusions, and their combined result. |
| `src/georesistivity/stacking.py` | Statistics of repeated readings. |
| `src/georesistivity/project.py` | Versioned `.geores.json` project files and sheet templates. |
| `src/georesistivity/storage.py` | Local autosave copies and templates, written atomically. |
| `src/georesistivity/csv_import.py` | CSV reading, column mapping, and row validation for import. |
| `src/georesistivity/spreadsheet.py` | Protection of CSV text against formula injection, and its inverse. |
| `src/georesistivity/field_sheet.py` | Rows of the digital field sheet turned into sounding points. |
| `src/georesistivity/models.py` | Immutable measurement and result models, warnings, and field errors. |
| `src/georesistivity/units.py` | Explicit conversion of supported units to SI. |
| `src/georesistivity/validation.py` | Safe numeric parsing and finite-value validation. |
| `src/georesistivity/formatting.py` | Locale-aware, significant-digit presentation of results. |
| `src/georesistivity/io.py` | Tabular representation and CSV serialization. |
| `src/georesistivity/plotting.py` | Plot-point preparation, scale validation, and Matplotlib figures. |
| `tests/` | Automated scientific, property-based, and interface tests. |
| `examples/` | Synthetic demonstration data. |
| `legacy/` | Historical academic prototypes, not imported by the modern application. |
| `docs/` | Project documentation, including the [technical audit](docs/AUDIT.md). |

The modern application keeps the Streamlit presentation layer separate from the scientific
and data-processing modules: the interface only renders widgets and forwards actions to
`services.py`, so the scientific calculation and the input rules are tested without the web
interface, and the library does not depend on Streamlit. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the layered design and the roadmap. Importing the package loads
pandas and Matplotlib only when a tabular or plotting function is used.

## Project History

GeoResistivity originated as an academic software prototype developed during a geophysics
internship. The modern version was subsequently refactored into a modular, tested scientific
Python application with explicit validation, unit conversion, tabular export, and
visualization. Historical prototypes are preserved under `legacy/` to document the project's
development history and are not executed by the modern application.

See [`CHANGELOG.md`](CHANGELOG.md) for the changes in each version.

## Tests and Code Quality

Install the application and development tools with:

```bash
python -m pip install -e ".[app,dev]"
```

Run the automated tests and code-quality checks from the repository root:

```bash
python -m pytest --cov
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pip_audit --skip-editable
```

The current suite contains **583 automated tests** with branch coverage enforced at 95%,
covering:

- scientific calculation and sign policy;
- sounding points, repeated readings, exclusions, and the digital field sheet;
- project files, migrations, autosave, recovery, and templates;
- CSV import, including round trips of both export formats;
- geometric factors, including the field-sheet K table and every array against the general
  formula;
- unit conversions;
- numeric parsing and validation;
- measurement and result models;
- result formatting;
- tabular and CSV transformations, including CSV dialects and formula-injection protection;
- plotting-data preparation and scale validation;
- application use cases, without the interface;
- the command line;
- the Streamlit interface, through Streamlit's `AppTest`;
- properties checked with Hypothesis, such as rejection of every thousands-like pattern.

CI runs the tests on Python 3.11, 3.12, and 3.13 on Linux, Windows, and macOS, plus Ruff,
mypy in strict mode, and pip-audit. An optional [pre-commit](https://pre-commit.com/)
configuration runs Ruff before each commit:

```bash
python -m pip install pre-commit
pre-commit install
```

## Tech Stack

- Python 3.11 or newer
- Streamlit
- pandas
- Matplotlib
- pytest, Hypothesis, and pytest-cov
- Ruff and mypy

## Limitations

GeoResistivity deliberately keeps its scientific scope narrow. The current version does not:

- determine electrode geometry automatically;
- calculate $K$ in the measurement form for arrays other than Schlumberger (use the K
  calculator or `georesistivity k`, then enter $K$);
- perform inversion;
- construct pseudosections;
- estimate true resistivity;
- perform automatic geological interpretation;
- perform 1D, 2D, or 3D subsurface modeling;
- store measurements in a database;
- replace acquisition or interpretation software.

AB/2 is treated only as optional spacing metadata for records and visualization. Scientific
use of the results requires appropriate knowledge of acquisition geometry, data quality, and
geological context.

The spacing graph requires at least two measurements containing AB/2. Measurements otherwise
remain available in the session table and CSV export without spacing-based visualization.

## Data & Privacy

The bundled sample measurements are synthetic and provided for demonstration and testing
purposes. Survey data stays on the computer that runs the interface: autosave copies and
templates are local files under `~/GeoResistivity`, and project files are saved where the
browser downloads them. In LAN mode, other devices on the network can open the interface and
see its data. The application does not send usage statistics: `.streamlit/config.toml` and
`georesistivity app` disable Streamlit's usage-statistics collection.

## License

GeoResistivity is released under the [MIT License](LICENSE).

## Author

**Paulo Gabriel Xavier Marques**

Geophysicist | M.Sc. in Applied Geophysics

GitHub: [PauloXavi](https://github.com/PauloXavi)
