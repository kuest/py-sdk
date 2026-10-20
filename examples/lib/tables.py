"""Boxed console tables for the examples.

Mirrors Node's `console.table` so the Python example output matches the
TypeScript reference: an `(index)` column, single-quoted strings, lowercase
booleans, and box-drawing borders. Pure stdlib — no third-party dependency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def _cell(value: object) -> str:
    """Render one value the way `console.table` does (quote strings, lowercase bools)."""
    if isinstance(value, str):
        return f"'{value}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _draw(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row_line(cells: list[str]) -> str:
        padded = (cell.ljust(width) for cell, width in zip(cells, widths, strict=True))
        return "│ " + " │ ".join(padded) + " │"

    print(border("┌", "┬", "┐"))
    print(row_line(headers))
    print(border("├", "┼", "┤"))
    for row in rows:
        print(row_line(row))
    print(border("└", "┴", "┘"))


def print_rows_table(rows: Sequence[Mapping[str, object]]) -> None:
    """Print a list of records, like `console.table([{...}, {...}])`.

    Columns are taken from the first record; each row is numbered in an
    `(index)` column.
    """
    if not rows:
        print("(no rows)")
        return
    columns = list(rows[0].keys())
    headers = ["(index)", *columns]
    body = [[str(i), *[_cell(row.get(col)) for col in columns]] for i, row in enumerate(rows)]
    _draw(headers, body)


def print_values_table(obj: Mapping[str, object]) -> None:
    """Print a single record as a key/`Values` table, like `console.table({...})`."""
    body = [[key, _cell(value)] for key, value in obj.items()]
    _draw(["(index)", "Values"], body)
