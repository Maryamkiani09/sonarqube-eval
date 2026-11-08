"""CSV exporter. DEMO: _normalize_rows is copy-pasted in tsv_exporter.py."""
from __future__ import annotations


def _normalize_rows(rows: list[dict], columns: list[str]) -> list[list[str]]:
    normalized = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"row {index} is not a dict")
        values = []
        for column in columns:
            value = row.get(column, "")
            if value is None:
                value = ""
            if isinstance(value, float):
                value = f"{value:.2f}"
            text = str(value).strip()
            if "\n" in text:
                text = text.replace("\n", " ")
            if "\r" in text:
                text = text.replace("\r", " ")
            values.append(text)
        normalized.append(values)
    return normalized


def to_csv(rows: list[dict], columns: list[str]) -> str:
    lines = [",".join(columns)]
    for values in _normalize_rows(rows, columns):
        lines.append(",".join('"' + v.replace('"', '""') + '"' for v in values))
    return "\n".join(lines) + "\n"
