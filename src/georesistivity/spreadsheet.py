"""Protection of text cells against spreadsheet formula injection, and its inverse."""

# Spreadsheet applications evaluate cells starting with these characters as formulas.
# See OWASP "CSV Injection".
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralize_spreadsheet_formula(value: object) -> object:
    """Prefix text that a spreadsheet would evaluate as a formula with an apostrophe."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def restore_spreadsheet_text(text: str) -> str:
    """Undo :func:`neutralize_spreadsheet_formula` for text read back from a CSV file."""
    if len(text) > 1 and text[0] == "'" and text[1:].startswith(FORMULA_PREFIXES):
        return text[1:]
    return text
