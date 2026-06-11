from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype


def _read_bytes(uploaded_file: Any) -> bytes:
    uploaded_file.seek(0)
    return uploaded_file.read()


def get_excel_sheets(uploaded_file: Any) -> list[str]:
    data = _read_bytes(uploaded_file)
    excel = pd.ExcelFile(BytesIO(data))
    if not excel.sheet_names:
        raise ValueError("El archivo Excel no contiene hojas.")
    return excel.sheet_names


def load_uploaded_file(
    uploaded_file: Any,
    *,
    sheet_name: str | None = None,
    csv_encoding: str = "utf-8",
    csv_separator: str = "Auto",
) -> pd.DataFrame:
    filename = uploaded_file.name.lower()
    data = _read_bytes(uploaded_file)
    if not data:
        raise ValueError("El archivo esta vacio.")

    if filename.endswith(".csv"):
        sep = None if csv_separator == "Auto" else csv_separator.replace("\\t", "\t")
        try:
            return pd.read_csv(
                BytesIO(data),
                encoding=csv_encoding,
                sep=sep,
                engine="python" if sep is None else "c",
            )
        except UnicodeDecodeError as exc:
            raise ValueError("La codificacion seleccionada no coincide con el archivo.") from exc
        except pd.errors.EmptyDataError as exc:
            raise ValueError("El CSV no contiene datos legibles.") from exc

    if filename.endswith((".xlsx", ".xls")):
        engine = "xlrd" if filename.endswith(".xls") else "openpyxl"
        return pd.read_excel(BytesIO(data), sheet_name=sheet_name, engine=engine)

    raise ValueError("Formato no soportado. Usa CSV, XLSX o XLS.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned.dropna(axis=1, how="all")
    if cleaned.empty:
        raise ValueError("La base no contiene columnas con datos.")

    names: list[str] = []
    used: set[str] = set()
    for index, column in enumerate(cleaned.columns, start=1):
        name = str(column).strip()
        if not name or name.lower().startswith("unnamed:"):
            name = f"columna_{index}"
        original = name
        suffix = 2
        while name in used:
            name = f"{original}_{suffix}"
            suffix += 1
        names.append(name)
        used.add(name)

    cleaned.columns = names
    return cleaned


def parse_custom_missing_values(raw_values: str) -> list[str]:
    separators = [",", ";", "\n", "\t"]
    normalized = raw_values
    for separator in separators:
        normalized = normalized.replace(separator, "\n")
    values = []
    for value in normalized.splitlines():
        cleaned = value.strip()
        if cleaned:
            values.append(cleaned)
    return list(dict.fromkeys(values))


def apply_custom_missing_values(df: pd.DataFrame, missing_values: list[str]) -> pd.DataFrame:
    if df.empty or not missing_values:
        return df.copy()

    cleaned = df.copy()
    normalized_missing = {value.strip() for value in missing_values if value.strip()}
    numeric_missing: set[float] = set()
    for value in normalized_missing:
        numeric_candidate = value.replace(",", ".")
        if len(numeric_candidate) > 1 and numeric_candidate.startswith("0") and not numeric_candidate.startswith("0."):
            continue
        try:
            numeric_missing.add(float(numeric_candidate))
        except ValueError:
            continue

    for column in cleaned.columns:
        series = cleaned[column]
        string_mask = series.astype("string").str.strip().isin(normalized_missing).fillna(False)
        if is_numeric_dtype(series) and numeric_missing:
            numeric_mask = pd.to_numeric(series, errors="coerce").isin(numeric_missing).fillna(False)
            mask = string_mask | numeric_mask
        else:
            mask = string_mask
        if mask.any():
            cleaned.loc[mask, column] = pd.NA

    return cleaned
