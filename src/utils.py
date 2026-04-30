from __future__ import annotations

from io import BytesIO

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "tabla") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        worksheet = writer.sheets[sheet_name[:31]]
        for index, column in enumerate(df.columns):
            width = max(12, min(40, len(str(column)) + 2))
            worksheet.set_column(index, index, width)
    output.seek(0)
    return output.read()


def tables_to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, table in tables.items():
            if table.empty:
                continue
            sheet_name = name[:31]
            table.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]
            for index, column in enumerate(table.columns):
                width = max(12, min(40, len(str(column)) + 2))
                worksheet.set_column(index, index, width)
    output.seek(0)
    return output.read()
