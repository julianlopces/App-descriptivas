from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


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
