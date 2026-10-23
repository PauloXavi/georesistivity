"""English texts of the interface."""

TEXT: dict[str, str] = {
    # Application and tabs.
    "app.subtitle": "Apparent Resistivity Calculator",
    "app.intro": (
        "Calculate and record apparent resistivity from the measured potential difference and "
        "current, with the geometric factor entered or calculated from the geometry."
    ),
    "tab.sheet": "Field sheet (VES)",
    "tab.single": "Single measurement",
    "tab.import": "Import CSV",
    "common.cancel": "Cancel",
    # Sidebar.
    "sidebar.caption": "Scientific calculation workspace",
    "sidebar.preferences": "Preferences",
    "sidebar.language": "Language",
    "sidebar.number_format": "Number format",
    "sidebar.number_format_help": (
        "Used to display results. Input accepts either a comma or a period as the decimal "
        "separator; thousands separators are not accepted."
    ),
    "sidebar.csv_format": "CSV export format",
    "csv.standard": "Standard (comma, decimal point)",
    "csv.excel_pt_br": "Excel pt-BR (semicolon, decimal comma)",
    "sidebar.about": "About",
    "sidebar.about_text": (
        "Software for apparent-resistivity measurements and Schlumberger vertical electrical "
        "soundings, in the field and in the office."
    ),
    "sidebar.basis": "Scientific basis",
    "sidebar.basis_terms": (
        "- $\\rho_a$: apparent resistivity [Ω·m]\n"
        "- $K$: geometric factor [m]\n"
        "- $\\Delta V$: potential difference [V]\n"
        "- $I$: injected current [A]"
    ),
    "sidebar.k_info": (
        "K can be entered directly or calculated for the Schlumberger array from AB/2 and MN "
        "with the exact formula. The K calculator covers Wenner, dipole-dipole, pole-dipole, "
        "and any four-electrode layout."
    ),
    "sidebar.units": "Internal units",
    "sidebar.units_text": "Voltage: **V**  \nCurrent: **A**  \nLength: **m**",
    "sidebar.disclaimer": (
        "This application is intended for educational, research and scientific computing "
        "purposes. Interpretation of electrical resistivity data requires knowledge of the "
        "acquisition geometry and geological context."
    ),
    # Field names used in messages.
    "field.delta_v": "Delta V",
    "field.current": "Current",
    "field.geometric_factor": "Geometric factor K",
    "field.spacing_ab2": "AB/2",
    "field.mn": "MN",
    # Single-measurement form.
    "form.title": "Measurement Input",
    "form.k_mode": "Geometric factor K",
    "form.k_mode_external": "Enter K",
    "form.k_mode_schlumberger": "Calculate K (Schlumberger)",
    "form.delta_v": "Delta V",
    "form.delta_v_placeholder": "e.g. 120,5",
    "form.voltage_unit": "Voltage unit",
    "form.current": "Current",
    "form.current_placeholder": "e.g. 20",
    "form.current_unit": "Current unit",
    "form.k": "Geometric Factor K",
    "form.k_placeholder": "e.g. 5,89",
    "form.k_unit": "K unit",
    "form.ab2": "AB/2",
    "form.ab2_optional": "AB/2 — optional",
    "form.ab2_placeholder": "e.g. 20",
    "form.ab2_placeholder_optional": "Leave blank if unknown",
    "form.spacing_unit": "Spacing unit",
    "form.mn": "MN — full M-N spacing",
    "form.mn_optional": "MN — optional",
    "form.mn_placeholder": "e.g. 2",
    "form.mn_unit": "MN unit",
    "form.formula_caption": (
        "Exact Schlumberger formula. MN is the full distance between M and N, as on the field "
        "sheet. The K source is recorded automatically."
    ),
    "form.source": "Geometric factor source — optional",
    "form.source_placeholder": "e.g. equipment, table, field sheet",
    "form.submit": "Calculate and add measurement",
    "form.not_added": "Measurement could not be added.",
    "form.added": "Measurement #{number} added.",
    "form.duplicate": (
        "This measurement is identical to #{number}. If it is not an intentional repeated "
        "reading, remove it with '{remove}'."
    ),
    # Latest result.
    "result.title": "Latest Result",
    "result.metric": "Apparent Resistivity",
    "result.converted": "Converted values",
    "result.k_source": "K source: {source}",
    # K calculator.
    "kcalc.title": "K calculator",
    "kcalc.array": "Array",
    "kcalc.length_unit": "Length unit",
    "kcalc.submit": "Calculate K",
    "kcalc.hint": "To use it, choose '{enter_k}' and type this value with the unit m.",
    "kcalc.failed": "K could not be calculated.",
    "kcalc.failed_error": "K could not be calculated: {error}",
    "array.schlumberger": "Schlumberger",
    "array.wenner": "Wenner-α",
    "array.dipole-dipole": "Dipole-dipole",
    "array.pole-dipole": "Pole-dipole (remote B)",
    "array.general": "General four-electrode",
    "param.ab2": "AB/2",
    "param.mn": "MN (full spacing)",
    "param.a": "a (spacing)",
    "param.n": "n (dimensionless)",
    "param.am": "AM",
    "param.bm": "BM",
    "param.an": "AN",
    "param.bn": "BN",
    # Session measurements.
    "session.title": "Session Measurements",
    "session.count.one": "{n} measurement in this session.",
    "session.count.other": "{n} measurements in this session.",
    "session.empty": "No measurements have been added yet.",
    "session.remove_last": "Remove last measurement",
    "session.clear_all": "Clear all measurements",
    "session.export": "Export CSV",
    "session.clear_question": "Clear every measurement from this session?",
    "session.clear_confirm": "Confirm clear",
    # Table of single measurements (column titles on screen; CSV headers stay in English).
    "table.#": "#",
    "table.Delta V": "Delta V",
    "table.Voltage unit": "Voltage unit",
    "table.Current": "Current",
    "table.Current unit": "Current unit",
    "table.K": "K",
    "table.K unit": "K unit",
    "table.K source": "K source",
    "table.AB/2": "AB/2",
    "table.Spacing unit": "Spacing unit",
    "table.MN": "MN",
    "table.MN unit": "MN unit",
    "table.Delta V [V]": "Delta V [V]",
    "table.I [A]": "I [A]",
    "table.K [m]": "K [m]",
    "table.AB/2 [m]": "AB/2 [m]",
    "table.MN [m]": "MN [m]",
    "table.rho_a [ohm.m]": "rho_a [ohm.m]",
    "table.Warnings": "Warnings",
    # Spacing plot of single measurements.
    "plot.need_two": "Add AB/2 to at least two measurements to display the spacing plot.",
    "plot.title": "Spacing Plot",
    "plot.sort": "Sort by AB/2 for visualization",
    "plot.scale": "Scale",
    "plot.linear": "Linear",
    "plot.loglog": "Log-log",
    "plot.log_incompatible": (
        "Log-log scale requires positive AB/2 and apparent-resistivity values. The following "
        "acquisition rows cannot be represented: {rows}. No points were removed."
    ),
    "plot.sorted_caption": "The plot is sorted by AB/2; the table remains in acquisition order.",
    # Figures.
    "figure.spacing_title": "Apparent Resistivity vs. Electrode Spacing",
    "figure.sounding_title": "Vertical Electrical Sounding (Schlumberger)",
    "figure.ab2_axis": "AB/2 [m]",
    "figure.rho_axis": "Apparent resistivity [Ω·m]",
    "figure.mn_legend": "MN = {mn} m",
    "figure.quality_warning": "Quality warning",
    "figure.error_bars": "±1 standard error of the mean (n ≥ 2)",
    "figure.survey_number": "VES {number}",
    "figure.date_format": "%Y-%m-%d",
    # Report.
    "report.title": "Vertical electrical sounding report (Schlumberger)",
    "report.details": "Survey and acquisition details",
    "report.array": "Array",
    "report.array_schlumberger": "Schlumberger (MN is the full distance between M and N)",
    "report.units": "Units of ΔV / I",
    "report.cv_limit": "CV limit",
    "report.estimator": "Estimator",
    "report.estimator_mean": "mean of ΔV/I over the readings not excluded",
    "report.coordinates": "Coordinates ({crs})",
    "report.summary": "Summary",
    "report.summary_counts": "{positions} at {spacings}: {used} and {excluded}.",
    "count.reading_used.one": "{n} reading used",
    "count.reading_used.other": "{n} readings used",
    "count.reading_excluded.one": "{n} excluded",
    "count.reading_excluded.other": "{n} excluded",
    "report.summary_range": (
        "AB/2 from {ab2_min} to {ab2_max} m; ρa from {rho_min} to {rho_max} Ω·m."
    ),
    "report.summary_warnings.one": "{n} position with a quality warning.",
    "report.summary_warnings.other": "{n} positions with a quality warning.",
    "report.summary_unused.one": "{n} row of the sheet was not used (see below).",
    "report.summary_unused.other": "{n} rows of the sheet were not used (see below).",
    "report.summary_empty": "The sheet has no complete readings yet.",
    "report.curve": "VES curve",
    "report.no_curve": "No position has a positive ρa, so there is no curve.",
    "report.points": "Positions",
    "report.readings": "Readings",
    "report.col_delta_v": "ΔV [{unit}]",
    "report.col_current": "I [{unit}]",
    "report.col_r": "R [Ω]",
    "report.col_rho": "ρa [Ω·m]",
    "report.col_excluded": "Excluded",
    "report.col_reason": "Reason",
    "report.col_entered": "Entered at",
    "report.unused": "Rows of the sheet not used",
    "report.col_row": "Row",
    "report.col_problem": "Reason",
    "report.waiting": "{column}: not typed yet",
    "report.warnings": "Quality warnings",
    "report.col_warning": "Warning",
    "report.col_meaning": "Meaning",
    "report.col_positions": "Positions",
    "report.history": "Change history",
    "report.no_history": "No changes recorded.",
    "report.empty_table": "None.",
    "report.methods": "Methods",
    "report.method_k": (
        "Exact Schlumberger geometric factor: K = π (L² − l²) / (2 l), with L = AB/2 and "
        "l = MN/2, in metres."
    ),
    "report.method_rho": (
        "Apparent resistivity: ρa = K · mean(ΔV_i / I_i) over the readings of the position that "
        "are not excluded, in Ω·m; every reading has the same weight."
    ),
    "report.method_se": (
        "Standard error of ρa: K · s / √n, with s the sample standard deviation of ΔV_i / I_i; it "
        "exists only for n ≥ 2 and is the size of the error bars. CV = s / |mean|, flagged above "
        "{cv_limit}%."
    ),
    "report.method_wide_mn": (
        "Wide-MN warning when (AB/2) / (MN/2) < 4; K stays exact for any MN shorter than AB."
    ),
    "report.method_entered": (
        '"Entered at" is the time the ΔV and I of the row were first both filled in on the '
        "digital sheet. When a paper sheet is typed in later, it is the time of typing, not of "
        "the measurement."
    ),
    "report.method_recomputed": (
        "Calculated values are not stored in the project: this report recomputes them from the "
        "typed values, in the units shown."
    ),
    "report.references": "References",
    "report.footer": "GeoResistivity {version} · generated {time} · project SHA-256: {digest}",
    "report.page": "Page {page} of {pages}",
    "report.format": "Report format",
    "report.download": "Download report ({format})",
    "report.panel": "VES report",
    "report.panel_caption": (
        "Header, curve, positions, readings with exclusions, rows not used, warnings, history, "
        "and methods, in the selected language and number format."
    ),
    # Change history.
    "history.title": "Change history",
    "history.count.one": "{n} change recorded.",
    "history.count.other": "{n} changes recorded.",
    "history.empty": (
        "No changes recorded. Typing into an empty cell does not count; correcting or clearing a "
        "typed value, deleting a row, or replacing the sheet or the units does, with its time."
    ),
    "history.undo": "Undo last change",
    "history.next_undo": "Undo reverts: {change}",
    "history.nothing_to_undo": "Every change has been undone.",
    "history.filter": "Show",
    "history.all_rows": "All changes",
    "history.row_option": "Row {number}: AB/2 {ab2}, MN {mn}",
    "history.deleted_row_option": "Deleted row: AB/2 {ab2}, MN {mn}",
    "history.row_number_option": "Row {number} (not on the current sheet)",
    "history.col_number": "No.",
    "history.col_time": "Time",
    "history.col_row": "Row",
    "history.col_change": "Change",
    "history.time_format": "%Y-%m-%d %H:%M:%S",
    "history.edit": "{field}: {old} → {new}",
    "history.empty_value": "(empty)",
    "history.yes": "yes",
    "history.no": "no",
    "history.delete_row": "Row deleted ({summary})",
    "history.replace_import": "Sheet replaced by the import of {detail}",
    "history.replace_new_sheet": "Sheet replaced by a new sheet",
    "history.replace_template": "Sheet replaced by the template {detail}",
    "history.append_rows": "{rows} added by the import of {detail}",
    "history.units": "Units of ΔV / I: {old} → {new}",
    "history.undo_entry": "Undid entry no. {number}",
    "history.undone": "{change} (undone)",
    "history.export": "Export history (CSV)",
    "history.field_marker": "Marker",
    "history.field_ab2": "AB/2",
    "history.field_mn": "MN",
    "history.field_delta_v": "ΔV",
    "history.field_current": "I",
    "history.field_excluded": "Exclude",
    "history.field_reason": "Exclusion reason",
    # Figure export.
    "export.title": "Export figure",
    "export.format": "Format",
    "export.format_png": "PNG (image, 300 dpi)",
    "export.format_svg": "SVG (vector, editable)",
    "export.format_pdf": "PDF (vector, for printing)",
    "export.size": "Size",
    "export.size_standard": "Standard (17.8 × 17.8 cm)",
    "export.size_scale": "Bilog paper scale",
    "export.decade_mm": "Modulus [mm per decade]",
    "export.decade_help": (
        "Length of one decade on both axes, as on bilog paper and master curves. The default of "
        "{default} mm is provisional: replace it with the modulus of your paper."
    ),
    "export.scale_caption": (
        "Plot area: {width} × {height} cm ({x_decades} × {y_decades} decades). To keep the scale, "
        "print at 100% (no fit to page) and check one decade with a ruler; PDF and SVG keep the "
        "exact size."
    ),
    "export.title_with_survey": "Title with VES no., place, and date",
    "export.download": "Download figure ({format})",
    # Quality warnings.
    "warning.negative_apparent_resistivity": (
        "Negative apparent resistivity. Check the polarity of the potential electrodes, the "
        "current direction, and the cable connections."
    ),
    "warning.schlumberger_wide_mn": (
        "MN is wide for this AB/2: (AB/2)/(MN/2) is below 4. K uses the exact formula and stays "
        "correct, but the reading averages the potential over a wide interval; consider a "
        "smaller MN at this spacing."
    ),
    "warning.stack_high_variation": (
        "Repeated readings vary more than the coefficient-of-variation limit."
    ),
    "warning.stack_mixed_signs": "Repeated readings have both positive and negative values.",
    "warning_short.negative_apparent_resistivity": "negative ρa",
    "warning_short.schlumberger_wide_mn": "wide MN",
    "warning_short.stack_high_variation": "CV above limit",
    "warning_short.stack_mixed_signs": "mixed signs",
    # Field sheet.
    "sheet.title": "Schlumberger field sheet",
    "sheet.caption": (
        "Type ΔV and I in the rows you read; blank rows are ignored. A second row with the "
        "same AB/2 and the next MN is an overlap reading. Add a row with the same AB/2 and MN "
        "to record a repeated reading. K uses the exact formula with MN as the full M-N "
        "spacing. The sheet is autosaved on this computer; use Save project in the sidebar to "
        "keep a file."
    ),
    "sheet.dv_unit": "ΔV unit",
    "sheet.i_unit": "I unit",
    "sheet.cv_limit": "CV limit [%]",
    "sheet.cv_help": (
        "Repeated readings of one position whose coefficient of variation exceeds this limit "
        "are flagged."
    ),
    "sheet.col_marker": "Marker",
    "sheet.col_marker_help": "Cable or reel marker colour of this AB/2",
    "sheet.col_ab2": "AB/2 [m]",
    "sheet.col_mn": "MN [m]",
    "sheet.col_mn_help": "Full M-N spacing",
    "sheet.col_delta_v": "ΔV [{unit}]",
    "sheet.col_current": "I [{unit}]",
    "sheet.col_exclude": "Exclude",
    "sheet.col_reason": "Exclusion reason",
    "sheet.issue_ab2": "AB/2",
    "sheet.issue_mn": "MN",
    "sheet.issue_delta_v": "ΔV",
    "sheet.issue_current": "I",
    "sheet.issue_reason": "Exclusion reason",
    "sheet.waiting": "Waiting for a value in {rows}.",
    "sheet.waiting_row": "row {number} ({column})",
    "sheet.not_used": "These rows were not used:",
    "sheet.row_issue": "**Row {number}** — {details}",
    "sheet.empty": "Type ΔV and I in a row to see the result and the curve.",
    "sheet.summary.one": "{positions} read at {spacings}.",
    "sheet.summary.other": "{positions} read at {spacings}.",
    "sheet.error_bars": "Error bars (±1 standard error)",
    "sheet.error_bars_help": (
        "Standard error of the mean of ΔV/I times K (K·s/√n). It exists only at positions "
        "with two or more valid readings. If a bar goes below zero, its lower part is dotted "
        "down to the edge of the plot."
    ),
    "sheet.error_bars_on.one": (
        "Error bar on {with_bars} of {positions} on the curve (only where there are two or more "
        "valid readings)."
    ),
    "sheet.error_bars_on.other": (
        "Error bars on {with_bars} of {positions} on the curve (only where there are two or more "
        "valid readings)."
    ),
    "sheet.error_bars_none": (
        "No position has two or more valid readings, so the curve has no error bars."
    ),
    "sheet.not_on_curve": "Not on the log-log curve because ρa is not positive: {positions}.",
    "sheet.position": "AB/2 = {ab2} m (MN = {mn} m)",
    "sheet.export_points": "Export points (CSV)",
    "sheet.export_readings": "Export readings (CSV)",
    "points.ab2": "AB/2 [m]",
    "points.mn": "MN [m]",
    "points.marker": "Marker",
    "points.k": "K [m]",
    "points.readings": "Readings",
    "points.readings_excluded": "{used} (+{excluded} excluded)",
    "points.rho": "ρa [Ω·m]",
    "points.se": "ρa standard error [Ω·m]",
    "points.cv": "CV [%]",
    "points.warnings": "Warnings",
    # Templates and new sheet.
    "templates.title": "New sheet and templates",
    "templates.layout": "Layout for a new sheet",
    "templates.standard": "Standard field sheet (45 positions)",
    "templates.new": "New sheet",
    "templates.new_question": (
        "Start a new sheet? Every value typed in this sheet will be discarded."
    ),
    "templates.new_confirm": "Discard and start new sheet",
    "templates.caption": (
        "Save the AB/2, MN, and marker colours of this sheet as a template, without readings, "
        "to start new sheets with them."
    ),
    "templates.name": "Template name",
    "templates.save": "Save template",
    "templates.saved": "Template '{name}' saved in {folder}.",
    "templates.not_saved": "The template was not saved: {error}",
    # Survey details.
    "survey.title": "Survey details",
    "survey.name": "Survey name",
    "survey.sev": "VES no.",
    "survey.date": "Date",
    "survey.area": "Area",
    "survey.place": "Place",
    "survey.operator": "Operator",
    "survey.equipment": "Equipment",
    "survey.azimuth": "Azimuth of AB [°]",
    "survey.azimuth_help": "Direction of the current-electrode line, in degrees from north.",
    "survey.latitude": "Latitude [°]",
    "survey.latitude_help": "WGS 84 decimal degrees; negative south of the equator.",
    "survey.longitude": "Longitude [°]",
    "survey.longitude_help": "WGS 84 decimal degrees; negative west of Greenwich.",
    "survey.notes": "Notes",
    # Project, autosave, and recovery.
    "project.title": "Project",
    "project.open": "Open project",
    "project.open_help": (
        "A .geores.json file saved by GeoResistivity. It replaces the current sheet, survey "
        "details, and single measurements."
    ),
    "project.save": "Save project",
    "project.opened": "Opened {source}.",
    "project.open_failed": "Could not open {source}: {error}",
    "project.not_utf8": "Could not open {name}: not UTF-8 text.",
    "project.autosave_source": "the autosave copy",
    "project.read_failed": "Could not read the autosave copy: {error}",
    "autosave.off": "Autosave is off on this installation.",
    "autosave.failed": "Autosave failed: {error}. Save the project file.",
    "autosave.done": "Autosaved at {time} in {folder}.",
    "autosave.pending": "Autosave starts with the first value typed, in {folder}.",
    "recovery.info": "Work from an earlier session was autosaved. Restore it to continue.",
    "recovery.untitled": "Untitled",
    "recovery.sev": "SEV {number}",
    "recovery.restore": "Restore",
    # CSV import.
    "import.title": "Import CSV",
    "import.caption": (
        "Import readings into the field sheet or single measurements from a CSV file, "
        "including the files GeoResistivity exports (standard or Excel pt-BR). Rows with "
        "problems are listed and left out."
    ),
    "import.file": "CSV file",
    "import.separator": "Separator",
    "import.separator_auto": "Detect",
    "import.separator_semicolon": "Semicolon ;",
    "import.separator_comma": "Comma ,",
    "import.separator_tab": "Tab",
    "import.read_as": "{name}: {encoding}, {separator}, {rows}.",
    "import.first_rows": "First {shown} of {rows}.",
    "import.no_name": "(no name)",
    "import.target": "Import into",
    "import.target_sheet": "Field sheet (readings by AB/2 and MN)",
    "import.target_measurements": "Single measurements (with K)",
    "import.columns": "Columns",
    "import.not_in_file": "— not in the file —",
    "import.decimal": "Decimal separator of the file",
    "import.decimal_auto": "Detect from the numbers ({detected})",
    "import.decimal_point": "Point (1.5)",
    "import.decimal_comma": "Comma (1,5)",
    "import.decimal_strict": "Undecided: reject values such as 1,000",
    "import.units": "Units for columns without a unit column",
    "import.length_unit": "Length unit (K, AB/2, MN)",
    "import.choose_columns": "Choose a column for: {fields}.",
    "import.ready.one": "{ready} of {rows} ready to import.",
    "import.ready.other": "{ready} of {rows} ready to import.",
    "import.problems": "{problems}; these rows will be left out:",
    "import.units_caption": "ΔV in {voltage}, I in {current}; lengths in meters.",
    "import.how": "How",
    "import.replace": "Replace the field sheet",
    "import.append": "Add after the current rows",
    "import.button": "Import {rows}",
    "import.done_sheet.one": "Imported {rows} from {name} into the Field sheet tab.",
    "import.done_sheet.other": "Imported {rows} from {name} into the Field sheet tab.",
    "import.done_measurements.one": (
        "Imported {measurements} from {name} into Single measurement."
    ),
    "import.done_measurements.other": (
        "Imported {measurements} from {name} into Single measurement."
    ),
    "import.nothing": "Nothing was imported: {error}",
    "import.units_differ": "Nothing was imported: the units differ from the sheet's.",
    "import.unreadable": "The file could not be read: {error}",
    "import.issue_line": "Line",
    "import.issue_column": "Column",
    "import.issue_problem": "Problem",
    "importfield.ab2": "AB/2 [m]",
    "importfield.mn": "MN [m]",
    "importfield.delta_v": "ΔV",
    "importfield.current": "I",
    "importfield.voltage_unit": "ΔV unit",
    "importfield.current_unit": "I unit",
    "importfield.marker": "Marker",
    "importfield.excluded": "Excluded",
    "importfield.reason": "Exclusion reason",
    "importfield.geometric_factor": "K",
    "importfield.geometric_factor_unit": "K unit",
    "importfield.spacing_ab2": "AB/2",
    "importfield.spacing_unit": "AB/2 unit",
    "importfield.mn_unit": "MN unit",
    "importfield.source": "K source",
    # Counts.
    "count.row.one": "{n} row",
    "count.row.other": "{n} rows",
    "count.data_row.one": "{n} data row",
    "count.data_row.other": "{n} data rows",
    "count.problem.one": "{n} problem",
    "count.problem.other": "{n} problems",
    "count.measurement.one": "{n} measurement",
    "count.measurement.other": "{n} measurements",
    "count.position.one": "{n} position",
    "count.position.other": "{n} positions",
    "count.spacing.one": "{n} AB/2 spacing",
    "count.spacing.other": "{n} AB/2 spacings",
    "count.reading.one": "{n} reading",
    "count.reading.other": "{n} readings",
}
