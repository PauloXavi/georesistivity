# GeoResistivity

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.62%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

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
      +--> measurement table
      +--> visualization
      +--> CSV export
```

## Features

- Apparent resistivity calculation.
- Explicit voltage-unit selection.
- Explicit current-unit selection.
- Explicit length-unit selection for the geometric factor $K$.
- Optional AB/2 spacing metadata.
- Decimal-point and decimal-comma parsing.
- Rejection of ambiguous numeric formats.
- Explicit conversion to SI units before calculation.
- Preservation of original inputs and converted values.
- Multiple independent measurements in one session.
- Preservation of acquisition order.
- Tabular result display and CSV export.
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
supported units are converted explicitly to SI before the calculation is performed.

The optional geometric factor source records where the externally supplied value of $K$ came
from, such as equipment, a table, or a field sheet. It is metadata only and does not affect the
calculation.

## Supported Units

The core library supports the following units:

| Quantity | Core/library units | Internal unit |
| --- | --- | --- |
| Voltage | `V`, `mV`, `uV`, `µV` | `V` |
| Current | `A`, `mA`, `uA`, `µA` | `A` |
| Length | `m`, `cm`, `mm`, `km` | `m` |

The Streamlit interface offers `V`, `mV`, and `µV` for voltage; `A`, `mA`, and `µA` for
current; and `m`, `cm`, `mm`, and `km` for length. The ASCII forms `uV` and `uA` are aliases
accepted by the core library, while the interface presents the `µ` symbol in its selectors.

The geometric factor $K$ is converted to meters. When AB/2 is supplied, it is also converted
to meters and retained as spacing metadata, but it does not participate in the apparent
resistivity equation.

## Numeric Input and Validation

Numeric text input accepts either a decimal point (`10.5`) or a decimal comma (`10,5`). A value
containing both separators is rejected as ambiguous, and thousands separators are not
explicitly supported. This is intentionally narrow numeric parsing rather than complete
locale-aware formatting.

NaN and infinite values are rejected. A zero current and a zero geometric factor are also
rejected because they do not produce a valid calculation. The library preserves negative
signs: negative potential difference or current values are not rejected automatically, and
their physical sign convention depends on the acquisition context.

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
python -m venv .venv
source .venv/bin/activate

python -m pip install -e .
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

Start the application with:

```bash
python -m streamlit run app/app.py
```

Streamlit will print the local application URL after startup.

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

The interface displays the rounded value `2,232.14 ohm·m`. AB/2 is metadata associated with
the measurement record and is not used in this equation.

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
│   └── app.py
├── src/georesistivity/
│   ├── core.py
│   ├── io.py
│   ├── models.py
│   ├── plotting.py
│   ├── units.py
│   └── validation.py
├── tests/
├── examples/
├── legacy/
└── docs/
```

| Path | Responsibility |
| --- | --- |
| `app/` | Streamlit presentation layer and session interaction. |
| `src/georesistivity/core.py` | Pure scientific calculation and measurement processing. |
| `src/georesistivity/models.py` | Immutable measurement and result data models. |
| `src/georesistivity/units.py` | Explicit conversion of supported units to SI. |
| `src/georesistivity/validation.py` | Safe numeric parsing and finite-value validation. |
| `src/georesistivity/io.py` | Tabular representation and CSV serialization. |
| `src/georesistivity/plotting.py` | Plot-point preparation, scale validation, and Matplotlib figures. |
| `tests/` | Automated scientific and software tests. |
| `examples/` | Synthetic demonstration data. |
| `legacy/` | Historical academic prototypes, not imported by the modern application. |
| `docs/` | Project documentation assets. |

The modern application keeps the Streamlit presentation layer separate from the scientific
and data-processing modules. The scientific calculation can therefore be tested without the
web interface.

## Project History

GeoResistivity originated as an academic software prototype developed during a geophysics
internship. The modern version was subsequently refactored into a modular, tested scientific
Python application with explicit validation, unit conversion, tabular export, and
visualization. Historical prototypes are preserved under `legacy/` to document the project's
development history and are not executed by the modern application.

## Tests and Code Quality

Install the development tools with:

```bash
python -m pip install -e ".[dev]"
```

Run the automated tests and code-quality checks from the repository root:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

The current suite contains **53 automated tests** covering:

- scientific calculation;
- unit conversions;
- numeric parsing and validation;
- measurement and result models;
- tabular and CSV transformations;
- plotting-data preparation and scale validation.

## Tech Stack

- Python 3.11 or newer
- Streamlit
- pandas
- Matplotlib
- pytest
- Ruff

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
purposes.

## Author

**Paulo Gabriel Xavier Marques**

Geophysicist | M.Sc. in Applied Geophysics

GitHub: [PauloXavi](https://github.com/PauloXavi)
