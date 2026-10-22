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

> The geometric factor K is supplied externally. The current version does not assume or
> calculate a specific electrode-array geometry.

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
- Optional AB/2 spacing metadata.
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

### Sign policy

- $K$ must be positive, as it is for conventional four-electrode arrays.
- AB/2, when supplied, must be positive.
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

## Demonstration Data

[`examples/sample_measurements.csv`](examples/sample_measurements.csv) contains the sample
measurements provided as a small example and reference dataset. The I/O test suite reads this
file to verify its structure and scientific consistency. The current Streamlit application
does not import CSV files.

The bundled sample measurements are synthetic and provided for demonstration and testing
purposes.

## Architecture

```text
GeoResistivity/
├── app/
│   └── app.py              # compatibility entry point for `streamlit run`
├── src/georesistivity/
│   ├── app/                # Streamlit interface
│   │   ├── main.py
│   │   └── state.py
│   ├── cli.py
│   ├── core.py
│   ├── formatting.py
│   ├── io.py
│   ├── models.py
│   ├── plotting.py
│   ├── services.py
│   ├── units.py
│   └── validation.py
├── tests/
├── examples/
├── legacy/
└── docs/
```

| Path | Responsibility |
| --- | --- |
| `src/georesistivity/app/` | Streamlit presentation layer (`main.py`) and typed session state (`state.py`). |
| `src/georesistivity/services.py` | Application use cases shared by the interfaces, without Streamlit. |
| `src/georesistivity/cli.py` | The `georesistivity` command. |
| `app/app.py` | Compatibility entry point for `streamlit run app/app.py`. |
| `src/georesistivity/core.py` | Pure scientific calculation and measurement processing. |
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

The current suite contains **211 automated tests** with branch coverage enforced at 95%,
covering:

- scientific calculation and sign policy;
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

- determine electrode geometry;
- calculate the geometric factor $K$;
- assume Schlumberger, Wenner, dipole-dipole, or any other electrode array;
- implement a specific vertical electrical sounding (SEV) workflow;
- perform inversion;
- construct pseudosections;
- estimate true resistivity;
- perform automatic geological interpretation;
- perform 1D, 2D, or 3D subsurface modeling;
- store measurements in a database;
- persist measurements between Streamlit sessions;
- import CSV files;
- replace acquisition or interpretation software.

AB/2 is treated only as optional spacing metadata for records and visualization. Scientific
use of the results requires appropriate knowledge of acquisition geometry, data quality, and
geological context.

The spacing graph requires at least two measurements containing AB/2. Measurements otherwise
remain available in the session table and CSV export without spacing-based visualization.

## Data & Privacy

The bundled sample measurements are synthetic and provided for demonstration and testing
purposes. The application does not send usage statistics: `.streamlit/config.toml` disables
Streamlit's usage-statistics collection.

## License

GeoResistivity is released under the [MIT License](LICENSE).

## Author

**Paulo Gabriel Xavier Marques**

Geophysicist | M.Sc. in Applied Geophysics

GitHub: [PauloXavi](https://github.com/PauloXavi)
