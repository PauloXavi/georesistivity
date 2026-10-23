"""Change history of the field sheet (decision D-13) and reading times (decision D-14).

The history is append-only. Every change to a value that was already typed, every deleted
row, every replacement or extension of the sheet, and every change of the DeltaV or I unit is
recorded with its time; typing into an empty cell is data entry, not a change, and is not
recorded. Undo reverts the latest change that has not been undone and records that too, so
nothing is ever erased from the history.

Rows are followed by their ``id``. The table editor returns the rows it was given with their
ids, but rows the user adds come back without one; those are matched to the previous rows by
content and position (:func:`reconcile_sheet`), so deleting a row in the middle is not mistaken
for a change of the rows below it. This module does not import Streamlit or pandas.
"""

import dataclasses
import datetime as dt
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal

from georesistivity.field_sheet import SheetRow
from georesistivity.messages import GeoValueError

HistoryAction = Literal["edit", "delete_row", "replace_sheet", "append_rows", "units", "undo"]
HISTORY_ACTIONS: tuple[HistoryAction, ...] = (
    "edit",
    "delete_row",
    "replace_sheet",
    "append_rows",
    "units",
    "undo",
)
HistorySource = Literal["", "import", "new_sheet", "template"]
HISTORY_SOURCES: tuple[HistorySource, ...] = ("", "import", "new_sheet", "template")
RowField = Literal["marker", "ab2", "mn", "delta_v", "current", "excluded", "reason"]
ROW_FIELDS: tuple[RowField, ...] = (
    "marker",
    "ab2",
    "mn",
    "delta_v",
    "current",
    "excluded",
    "reason",
)


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One recorded change. Which fields are filled depends on ``action``.

    - ``edit``: ``row``, ``row_number``, ``field``, ``old``, ``new``.
    - ``delete_row``: ``row``, ``row_number`` (position before deletion), ``old_row``.
    - ``replace_sheet``: ``source``, ``detail`` (file or template name), ``old_rows``,
      ``old_units``.
    - ``append_rows``: ``source``, ``detail``, ``row_ids``.
    - ``units``: ``old`` and ``new`` as ``"mV / mA"``, ``old_units``.
    - ``undo``: ``undoes`` (1-based number of the entry it reverts).
    """

    at: str
    """ISO 8601 time with offset."""
    action: HistoryAction
    row: str = ""
    row_number: int | None = None
    field: RowField | None = None
    old: str = ""
    new: str = ""
    source: HistorySource = ""
    detail: str = ""
    old_row: SheetRow | None = None
    old_rows: tuple[SheetRow, ...] = ()
    old_units: tuple[str, str] | None = None
    row_ids: tuple[str, ...] = ()
    undoes: int | None = None


@dataclass(frozen=True, slots=True)
class SheetUpdate:
    """Rows of the sheet with their ids and reading times, and the changes found."""

    rows: tuple[SheetRow, ...]
    entries: tuple[HistoryEntry, ...]


@dataclass(frozen=True, slots=True)
class UndoResult:
    """The sheet after undoing one change, and the entry that records the undo."""

    rows: tuple[SheetRow, ...]
    units: tuple[str, str]
    entry: HistoryEntry


def now_text() -> str:
    """The current local time as ISO 8601 text with offset, to the second."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def new_row_id() -> str:
    """A random row identifier such as ``r3fa9c2d1``."""
    return f"r{secrets.token_hex(4)}"


def field_text(row: SheetRow, name: RowField) -> str:
    """The value of one field as text; ``excluded`` is ``"true"`` or ``"false"``."""
    value = getattr(row, name)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def has_content(row: SheetRow) -> bool:
    """Whether anything beyond the AB/2 and MN of the layout was typed in ``row``."""
    return bool(
        row.marker.strip()
        or row.delta_v.strip()
        or row.current.strip()
        or row.excluded
        or row.reason.strip()
    )


def with_ids(
    rows: Sequence[SheetRow], *, new_id: Callable[[], str] = new_row_id
) -> tuple[SheetRow, ...]:
    """``rows`` with a unique id each, keeping the ids they already have."""
    used: set[str] = set()
    result = []
    for row in rows:
        row_id = row.id
        while not row_id or row_id in used:
            row_id = new_id()
        used.add(row_id)
        result.append(row if row_id == row.id else dataclasses.replace(row, id=row_id))
    return tuple(result)


def _edits(old: SheetRow, new: SheetRow, number: int, now: str) -> list[HistoryEntry]:
    entries = []
    for name in ROW_FIELDS:
        before, after = field_text(old, name), field_text(new, name)
        # Typing into an empty cell is data entry; the exclusion flag always counts.
        if before != after and (name == "excluded" or before.strip()):
            entries.append(
                HistoryEntry(
                    at=now,
                    action="edit",
                    row=old.id,
                    row_number=number,
                    field=name,
                    old=before,
                    new=after,
                )
            )
    return entries


def reconcile_sheet(
    previous: Sequence[SheetRow],
    edited: Sequence[SheetRow],
    *,
    now: str,
    new_id: Callable[[], str] = new_row_id,
) -> SheetUpdate:
    """Follow every row from ``previous`` to ``edited`` and record what changed.

    ``previous`` are the rows as last recorded (with ids); ``edited`` are the rows returned by
    the editor, in its order. Edited rows whose id is known keep it; the others are aligned
    with the previous rows that the editor did not return, by content and then by position: an
    equal row is the same row, a different row in the same place was changed, and leftovers
    were added or deleted. A row gets its reading time when DeltaV and I are first both filled.
    """
    by_id = {row.id: row for row in previous if row.id}
    claimed: dict[int, SheetRow] = {}
    for index, row in enumerate(edited):
        if row.id in by_id and row.id not in {old.id for old in claimed.values()}:
            claimed[index] = by_id[row.id]
    claimed_ids = {old.id for old in claimed.values()}

    unclaimed = [
        (number, row)
        for number, row in enumerate(previous, start=1)
        if not row.id or row.id not in claimed_ids
    ]
    loose = [index for index in range(len(edited)) if index not in claimed]
    matcher = SequenceMatcher(
        a=[row.content() for _, row in unclaimed],
        b=[edited[index].content() for index in loose],
        autojunk=False,
    )
    pairs: dict[int, SheetRow] = {}
    deleted: list[tuple[int, SheetRow]] = []
    for _tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        old_rows = unclaimed[a_start:a_end]
        new_indices = loose[b_start:b_end]
        for (_, matched), index in zip(old_rows, new_indices, strict=False):
            pairs[index] = matched
        deleted.extend(old_rows[len(new_indices) :])

    used = set(claimed_ids) | {old.id for old in pairs.values() if old.id}
    rows: list[SheetRow] = []
    entries: list[HistoryEntry] = []
    for index, row in enumerate(edited):
        old = claimed.get(index) or pairs.get(index)
        row_id = old.id if old is not None and old.id else ""
        while not row_id:
            candidate = new_id()
            if candidate not in used:
                row_id = candidate
                used.add(row_id)
        entered_at = old.entered_at if old is not None and old.entered_at else ""
        if not entered_at and row.has_reading():
            entered_at = now
        current = dataclasses.replace(row, id=row_id, entered_at=entered_at)
        if old is not None:
            entries.extend(_edits(dataclasses.replace(old, id=row_id), current, index + 1, now))
        rows.append(current)

    for number, old in deleted:
        if has_content(old) or old.ab2.strip() or old.mn.strip():
            entries.append(
                HistoryEntry(
                    at=now, action="delete_row", row=old.id, row_number=number, old_row=old
                )
            )
    return SheetUpdate(tuple(rows), tuple(entries))


def replacement_entry(
    old_rows: Sequence[SheetRow],
    old_units: tuple[str, str],
    *,
    source: HistorySource,
    detail: str,
    now: str,
) -> HistoryEntry | None:
    """The record of replacing the whole sheet, or ``None`` if nothing was typed in it yet."""
    if not any(has_content(row) for row in old_rows):
        return None
    return HistoryEntry(
        at=now,
        action="replace_sheet",
        source=source,
        detail=detail,
        old_rows=tuple(old_rows),
        old_units=old_units,
    )


def append_entry(
    added: Sequence[SheetRow], *, source: HistorySource, detail: str, now: str
) -> HistoryEntry:
    """The record of rows added at the end of the sheet (they must already have ids)."""
    return HistoryEntry(
        at=now,
        action="append_rows",
        source=source,
        detail=detail,
        row_ids=tuple(row.id for row in added),
    )


def units_text(units: tuple[str, str]) -> str:
    """``"mV / mA"``."""
    return f"{units[0]} / {units[1]}"


def units_entry(old: tuple[str, str], new: tuple[str, str], *, now: str) -> HistoryEntry:
    """The record of a change of the DeltaV or I unit of the sheet."""
    return HistoryEntry(
        at=now, action="units", old=units_text(old), new=units_text(new), old_units=old
    )


def undoable_entry(history: Sequence[HistoryEntry]) -> int | None:
    """1-based number of the latest change that has not been undone, if any."""
    undone = {entry.undoes for entry in history if entry.action == "undo"}
    for number in range(len(history), 0, -1):
        if history[number - 1].action != "undo" and number not in undone:
            return number
    return None


def _position(rows: Sequence[SheetRow], row_id: str) -> int:
    for index, row in enumerate(rows):
        if row.id == row_id:
            return index
    raise GeoValueError("history.row_missing")


def undo_last(
    rows: Sequence[SheetRow],
    units: tuple[str, str],
    history: Sequence[HistoryEntry],
    *,
    now: str,
) -> UndoResult | None:
    """Revert the latest change that has not been undone; ``None`` if there is none."""
    number = undoable_entry(history)
    if number is None:
        return None
    entry = history[number - 1]
    result = list(rows)
    if entry.action == "edit":
        assert entry.field is not None
        index = _position(result, entry.row)
        value: Any = entry.old == "true" if entry.field == "excluded" else entry.old
        result[index] = dataclasses.replace(result[index], **{entry.field: value})
    elif entry.action == "delete_row":
        assert entry.old_row is not None and entry.row_number is not None
        result.insert(min(entry.row_number - 1, len(result)), entry.old_row)
    elif entry.action == "replace_sheet":
        assert entry.old_units is not None
        result = list(entry.old_rows)
        units = entry.old_units
    elif entry.action == "append_rows":
        removed = set(entry.row_ids)
        result = [row for row in result if row.id not in removed]
    else:
        assert entry.action == "units" and entry.old_units is not None
        units = entry.old_units
    undo = HistoryEntry(
        at=now,
        action="undo",
        row=entry.row,
        row_number=entry.row_number,
        field=entry.field,
        undoes=number,
    )
    return UndoResult(tuple(result), units, undo)
