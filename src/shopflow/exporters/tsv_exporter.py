"""TSV exporter. DEMO: _normalize_rows is copy-pasted from csv_exporter.py."""
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


def to_tsv(rows: list[dict], columns: list[str]) -> str:
    lines = ["\t".join(columns)]
    for values in _normalize_rows(rows, columns):
        lines.append("\t".join(v.replace("\t", " ") for v in values))
    return "\n".join(lines) + "\n"
