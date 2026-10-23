"""Tests for the change history of the field sheet."""

import dataclasses
import datetime as dt
import itertools
import re
from collections.abc import Callable

import pytest

from georesistivity.field_sheet import SheetRow
from georesistivity.messages import GeoValueError
from georesistivity.sheet_history import (
    HistoryEntry,
    append_entry,
    new_row_id,
    now_text,
    reconcile_sheet,
    replacement_entry,
    undo_last,
    undoable_entry,
    units_entry,
    with_ids,
)

NOW = "2026-10-23T09:00:00-03:00"
LATER = "2026-10-23T09:05:00-03:00"


def ids() -> Callable[[], str]:
    counter = itertools.count(1)
    return lambda: f"n{next(counter)}"


def row(row_id: str, **values: object) -> SheetRow:
    return SheetRow(id=row_id, **values)  # type: ignore[arg-type]


def unsaved(*rows: SheetRow) -> list[SheetRow]:
    """The rows as the editor returns rows the user added: without ids."""
    return [dataclasses.replace(r, id="") for r in rows]


SHEET = (
    row("a", ab2="1", mn="0,5", delta_v="80", current="40", entered_at=NOW),
    row("b", ab2="1,3", mn="0,5"),
    row("c", ab2="1,8", mn="0,5"),
)


def test_row_ids_are_random_and_short() -> None:
    first, second = new_row_id(), new_row_id()

    assert re.fullmatch(r"r[0-9a-f]{8}", first)
    assert first != second


def test_current_time_has_an_offset() -> None:
    assert dt.datetime.fromisoformat(now_text()).utcoffset() is not None


def test_with_ids_keeps_ids_and_replaces_missing_or_repeated_ones() -> None:
    rows = with_ids([row("a"), row(""), row("a")], new_id=ids())

    assert [r.id for r in rows] == ["a", "n1", "n2"]


def test_ids_and_times_do_not_take_part_in_row_equality() -> None:
    assert row("a", ab2="1", entered_at=NOW) == SheetRow(ab2="1")


def test_typing_into_empty_cells_is_not_a_change() -> None:
    edited = [SHEET[0], row("b", ab2="1,3", mn="0,5", delta_v="9", current="50"), SHEET[2]]

    update = reconcile_sheet(SHEET, edited, now=LATER)

    assert update.entries == ()
    assert update.rows[1].entered_at == LATER  # the reading is complete now
    assert update.rows[0].entered_at == NOW


def test_reading_time_is_set_only_when_both_values_are_typed() -> None:
    edited = [SHEET[0], row("b", ab2="1,3", mn="0,5", delta_v="9"), SHEET[2]]

    assert reconcile_sheet(SHEET, edited, now=LATER).rows[1].entered_at == ""


def test_correcting_a_typed_value_is_recorded_and_keeps_the_reading_time() -> None:
    edited = [row("a", ab2="1", mn="0,5", delta_v="82", current="40"), SHEET[1], SHEET[2]]

    update = reconcile_sheet(SHEET, edited, now=LATER)

    assert update.entries == (
        HistoryEntry(
            at=LATER, action="edit", row="a", row_number=1, field="delta_v", old="80", new="82"
        ),
    )
    assert update.rows[0].entered_at == NOW


def test_clearing_a_value_and_excluding_a_reading_are_recorded() -> None:
    edited = [
        row("a", ab2="1", mn="0,5", delta_v="", current="40", excluded=True, reason="bad"),
        SHEET[1],
        SHEET[2],
    ]

    entries = reconcile_sheet(SHEET, edited, now=LATER).entries

    # The reason was typed into an empty cell, so only the flag and the cleared value count.
    assert [(e.field, e.old, e.new) for e in entries] == [
        ("delta_v", "80", ""),
        ("excluded", "false", "true"),
    ]


def test_deleting_a_row_records_its_content_and_position() -> None:
    update = reconcile_sheet(SHEET, [SHEET[0], SHEET[2]], now=LATER)

    (entry,) = update.entries
    assert (entry.action, entry.row, entry.row_number) == ("delete_row", "b", 2)
    assert entry.old_row == SHEET[1]
    assert [r.id for r in update.rows] == ["a", "c"]


def test_deleting_an_empty_row_is_not_recorded() -> None:
    sheet = [*SHEET, row("d")]

    assert reconcile_sheet(sheet, list(SHEET), now=LATER).entries == ()


def test_rows_added_in_the_editor_get_new_ids_and_are_followed_by_content() -> None:
    added = [
        SheetRow(ab2="13", mn="2", delta_v="5", current="50"),
        SheetRow(ab2="18", mn="2", delta_v="3", current="50"),
        SheetRow(ab2="24", mn="2"),
    ]
    first = reconcile_sheet(SHEET, [*SHEET, *added], now=LATER, new_id=ids())
    assert [r.id for r in first.rows[3:]] == ["n1", "n2", "n3"]
    assert first.entries == ()

    # The editor still returns the added rows without ids; deleting the first of them must not
    # look like a change of the two below it.
    second = reconcile_sheet(first.rows, [*SHEET, *added[1:]], now=LATER, new_id=ids())

    (entry,) = second.entries
    assert (entry.action, entry.row, entry.row_number) == ("delete_row", "n1", 4)
    assert [r.id for r in second.rows[3:]] == ["n2", "n3"]


def test_correcting_a_value_in_an_added_row_is_recorded() -> None:
    added = SheetRow(ab2="13", mn="2", delta_v="5", current="50")
    first = reconcile_sheet(SHEET, [*SHEET, added], now=LATER, new_id=ids())

    edited = [*SHEET, dataclasses.replace(added, delta_v="6")]
    (entry,) = reconcile_sheet(first.rows, edited, now=LATER).entries

    assert (entry.row, entry.row_number, entry.old, entry.new) == ("n1", 4, "5", "6")


def test_rows_without_ids_are_matched_by_content() -> None:
    previous = unsaved(*SHEET)  # for example, rows seeded before any id was given
    edited = unsaved(SHEET[0], SHEET[2])

    update = reconcile_sheet(previous, edited, now=LATER, new_id=ids())

    (entry,) = update.entries
    assert (entry.action, entry.row_number) == ("delete_row", 2)
    assert len({r.id for r in update.rows}) == 2


def test_a_repeated_id_from_the_editor_is_treated_as_a_new_row() -> None:
    edited = [*SHEET, SHEET[0]]

    update = reconcile_sheet(SHEET, edited, now=LATER, new_id=ids())

    assert [r.id for r in update.rows] == ["a", "b", "c", "n1"]
    assert update.entries == ()


def test_replacing_an_untouched_sheet_is_not_recorded() -> None:
    template = [SheetRow(ab2="1", mn="0,5"), SheetRow(ab2="1,3", mn="0,5")]

    assert replacement_entry(template, ("mV", "mA"), source="new_sheet", detail="", now=NOW) is None


def test_replacing_a_sheet_keeps_its_rows_and_units() -> None:
    entry = replacement_entry(SHEET, ("V", "mA"), source="import", detail="a.csv", now=NOW)

    assert entry is not None
    assert (entry.action, entry.source, entry.detail) == ("replace_sheet", "import", "a.csv")
    assert entry.old_rows == SHEET
    assert entry.old_units == ("V", "mA")


def test_undo_reverts_the_latest_change_and_records_it() -> None:
    rows = [row("a", ab2="1", mn="0,5", delta_v="82", current="40"), SHEET[1], SHEET[2]]
    history = [
        HistoryEntry(
            at=NOW, action="edit", row="a", row_number=1, field="delta_v", old="80", new="82"
        )
    ]

    result = undo_last(rows, ("mV", "mA"), history, now=LATER)

    assert result is not None
    assert result.rows[0].delta_v == "80"
    assert result.entry == HistoryEntry(
        at=LATER, action="undo", row="a", row_number=1, field="delta_v", undoes=1
    )
    assert undoable_entry([*history, result.entry]) is None
    assert undo_last(rows, ("mV", "mA"), [*history, result.entry], now=LATER) is None


def test_undo_walks_back_past_undone_entries() -> None:
    history = [
        HistoryEntry(at=NOW, action="units", old="mV / mA", new="V / mA", old_units=("mV", "mA")),
        HistoryEntry(at=NOW, action="edit", row="a", field="current", old="40", new="41"),
        HistoryEntry(at=NOW, action="undo", undoes=2),
    ]

    assert undoable_entry(history) == 1
    result = undo_last(SHEET, ("V", "mA"), history, now=LATER)

    assert result is not None
    assert result.units == ("mV", "mA")
    assert result.entry.undoes == 1


def test_undo_restores_an_exclusion_flag() -> None:
    rows = [row("a", ab2="1", excluded=True, reason="bad")]
    history = [
        HistoryEntry(at=NOW, action="edit", row="a", field="excluded", old="false", new="true")
    ]

    result = undo_last(rows, ("mV", "mA"), history, now=LATER)

    assert result is not None
    assert result.rows[0].excluded is False


def test_undo_puts_a_deleted_row_back_in_its_place() -> None:
    history = [HistoryEntry(at=NOW, action="delete_row", row="b", row_number=2, old_row=SHEET[1])]

    result = undo_last([SHEET[0], SHEET[2]], ("mV", "mA"), history, now=LATER)

    assert result is not None
    assert [r.id for r in result.rows] == ["a", "b", "c"]


def test_undo_brings_back_a_replaced_sheet_with_its_units() -> None:
    entry = replacement_entry(SHEET, ("V", "A"), source="template", detail="T", now=NOW)
    assert entry is not None

    result = undo_last([row("x", ab2="10")], ("mV", "mA"), [entry], now=LATER)

    assert result is not None
    assert result.rows == SHEET
    assert result.units == ("V", "A")


def test_undo_removes_appended_rows() -> None:
    added = with_ids([SheetRow(ab2="13"), SheetRow(ab2="18")], new_id=ids())
    entry = append_entry(added, source="import", detail="b.csv", now=NOW)

    result = undo_last([*SHEET, *added], ("mV", "mA"), [entry], now=LATER)

    assert entry.row_ids == ("n1", "n2")
    assert result is not None
    assert result.rows == SHEET


def test_undo_of_a_row_that_is_gone_is_refused() -> None:
    history = [HistoryEntry(at=NOW, action="edit", row="z", field="ab2", old="1", new="2")]

    with pytest.raises(GeoValueError) as error:
        undo_last(SHEET, ("mV", "mA"), history, now=LATER)

    assert error.value.problem.code == "history.row_missing"


def test_units_entry_describes_both_units() -> None:
    entry = units_entry(("mV", "mA"), ("V", "mA"), now=NOW)

    assert (entry.old, entry.new, entry.old_units) == ("mV / mA", "V / mA", ("mV", "mA"))


def test_a_new_id_already_in_use_is_drawn_again() -> None:
    drawn = iter(["a", "b", "n1"])

    update = reconcile_sheet(
        SHEET, [*SHEET, SheetRow(ab2="13")], now=LATER, new_id=lambda: next(drawn)
    )

    assert update.rows[3].id == "n1"
