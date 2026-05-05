from __future__ import annotations

from io import BytesIO
import re

import pandas as pd


TABLE_TYPE_LABELS = {
    "absolute": "Frecuencia absoluta",
    "row_pct": "Porcentaje por fila",
    "col_pct": "Porcentaje por columna",
}


def compute_crosstab(
    df: pd.DataFrame,
    row_var: str,
    col_var: str,
    table_type: str,
) -> pd.DataFrame:
    subset = df[[row_var, col_var]].dropna(subset=[row_var, col_var]).copy()
    if subset.empty:
        return pd.DataFrame()

    rows = subset[row_var].astype("string")
    cols = subset[col_var].astype("string")
    table = pd.crosstab(rows, cols, dropna=False)

    if table_type == "absolute":
        return table

    if table_type == "row_pct":
        totals = table.sum(axis=1).replace(0, pd.NA)
        return (table.div(totals, axis=0) * 100).round(1).fillna(0.0)

    if table_type == "col_pct":
        totals = table.sum(axis=0).replace(0, pd.NA)
        return (table.div(totals, axis=1) * 100).round(1).fillna(0.0)

    raise ValueError(f"Tipo de tabla no soportado: {table_type}")


def format_crosstab_for_display(table: pd.DataFrame, table_type: str) -> pd.DataFrame:
    if table.empty or table_type == "absolute":
        return table
    return table.apply(lambda column: column.map(lambda value: f"{value:.1f}%"))


def sanitize_excel_sheet_name(name: str, existing_names: set[str] | None = None) -> str:
    existing_names = existing_names or set()
    cleaned = re.sub(r"[\[\]:*?/\\]", "_", str(name)).strip()
    cleaned = cleaned or "Hoja"
    cleaned = cleaned[:31]

    base = cleaned
    suffix = 1
    while cleaned in existing_names:
        suffix_text = f"_{suffix}"
        cleaned = f"{base[: 31 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    existing_names.add(cleaned)
    return cleaned


def build_crosstab_excel(
    df: pd.DataFrame,
    main_vars: list[str],
    disaggregation_vars: list[str],
    table_type: str,
) -> BytesIO:
    output = BytesIO()
    used_sheet_names: set[str] = set()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#020F50",
                "font_size": 12,
            }
        )
        meta_format = workbook.add_format({"italic": True, "font_color": "#000031"})
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#020F50",
                "font_color": "#FFFFFF",
                "border": 1,
                "border_color": "#B6C4E5",
            }
        )
        row_header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#F7FAF2",
                "font_color": "#020F50",
                "border": 1,
                "border_color": "#B6C4E5",
            }
        )
        cell_format = workbook.add_format(
            {
                "font_color": "#000031",
                "border": 1,
                "border_color": "#D8E0F4",
            }
        )
        percent_format = workbook.add_format(
            {
                "font_color": "#000031",
                "border": 1,
                "border_color": "#D8E0F4",
                "num_format": '0.0"%"',
            }
        )

        for main_var in main_vars:
            sheet_name = sanitize_excel_sheet_name(main_var, used_sheet_names)
            worksheet = workbook.add_worksheet(sheet_name)
            writer.sheets[sheet_name] = worksheet

            current_row = 0
            max_widths: dict[int, int] = {}

            for disagg_var in disaggregation_vars:
                if main_var == disagg_var:
                    continue

                table = compute_crosstab(df, disagg_var, main_var, table_type)
                if table.empty:
                    continue

                table_title = f"Tabla: {main_var} x {disagg_var}"
                worksheet.write(current_row, 0, table_title, title_format)
                worksheet.write(
                    current_row + 1,
                    0,
                    f"Tipo de visualización: {TABLE_TYPE_LABELS[table_type]}",
                    meta_format,
                )

                start_row = current_row + 2
                worksheet.write(start_row, 0, disagg_var, header_format)
                max_widths[0] = max(max_widths.get(0, 0), len(str(disagg_var)) + 2)

                for col_idx, column_name in enumerate(table.columns, start=1):
                    worksheet.write(start_row, col_idx, str(column_name), header_format)
                    max_widths[col_idx] = max(max_widths.get(col_idx, 0), len(str(column_name)) + 2)

                body_format = cell_format if table_type == "absolute" else percent_format
                for row_offset, (row_name, values) in enumerate(table.iterrows(), start=1):
                    worksheet.write(start_row + row_offset, 0, str(row_name), row_header_format)
                    max_widths[0] = max(max_widths.get(0, 0), len(str(row_name)) + 2)
                    for col_idx, value in enumerate(values, start=1):
                        worksheet.write(start_row + row_offset, col_idx, value, body_format)
                        cell_length = len(f"{value:.1f}%") if table_type != "absolute" else len(str(value))
                        max_widths[col_idx] = max(max_widths.get(col_idx, 0), cell_length + 2)

                current_row = start_row + len(table.index) + 4

            if current_row == 0:
                worksheet.write(0, 0, f"Sin datos válidos para {main_var}", title_format)

            for col_idx, width in max_widths.items():
                worksheet.set_column(col_idx, col_idx, min(max(width, 14), 42))

    output.seek(0)
    return output
