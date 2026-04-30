from __future__ import annotations

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if is_numeric_dtype(series):
        return series
    if is_bool_dtype(series):
        return series.astype("Int64")
    return pd.to_numeric(series.astype("string").str.replace(",", ".", regex=False), errors="coerce")


def detect_variable_types(df: pd.DataFrame) -> dict[str, list[str]]:
    continuous: list[str] = []
    categorical: list[str] = []

    for column in df.columns:
        series = df[column]
        non_missing = series.dropna()
        if non_missing.empty:
            categorical.append(column)
            continue

        numeric = _coerce_numeric(series)
        numeric_ratio = numeric.notna().sum() / max(series.notna().sum(), 1)
        unique_count = non_missing.nunique(dropna=True)

        if is_bool_dtype(series) or unique_count <= 2:
            categorical.append(column)
        elif is_numeric_dtype(series) or numeric_ratio >= 0.9:
            continuous.append(column)
        else:
            categorical.append(column)

    return {"continuous": continuous, "categorical": categorical}


def continuous_summary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    percentiles = [0.25, 0.5, 0.75, 0.95]

    for column in columns:
        numeric = _coerce_numeric(df[column])
        non_missing = numeric.dropna()
        row: dict[str, object] = {
            "variable": column,
            "n_no_perdidos": int(non_missing.shape[0]),
            "n_perdidos": int(numeric.isna().sum()),
            "media": None,
            "mediana": None,
            "desviacion_estandar": None,
            "minimo": None,
            "maximo": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
        }
        if not non_missing.empty:
            quantiles = non_missing.quantile(percentiles)
            row.update(
                {
                    "media": non_missing.mean(),
                    "mediana": non_missing.median(),
                    "desviacion_estandar": non_missing.std(),
                    "minimo": non_missing.min(),
                    "maximo": non_missing.max(),
                    "p25": quantiles.loc[0.25],
                    "p50": quantiles.loc[0.5],
                    "p75": quantiles.loc[0.75],
                    "p95": quantiles.loc[0.95],
                }
            )
        rows.append(row)

    return pd.DataFrame(rows)


def categorical_summary(df: pd.DataFrame, columns: list[str], *, max_levels: int = 30) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = len(df)

    for column in columns:
        series = df[column]
        missing = int(series.isna().sum())
        counts = series.astype("string").fillna("(Perdido)").value_counts(dropna=False)
        if len(counts) > max_levels:
            shown = counts.head(max_levels)
            other_count = int(counts.iloc[max_levels:].sum())
            counts = pd.concat([shown, pd.Series({"(Otras categorias)": other_count})])

        for value, count in counts.items():
            rows.append(
                {
                    "variable": column,
                    "categoria": value,
                    "frecuencia": int(count),
                    "porcentaje": (count / total_rows * 100) if total_rows else 0,
                    "n_perdidos_variable": missing,
                }
            )

    return pd.DataFrame(rows)


def contingency_table(
    df: pd.DataFrame,
    row_var: str,
    col_var: str,
    *,
    normalize: str | None = None,
) -> pd.DataFrame:
    kwargs = {"normalize": normalize} if normalize is not None else {}
    table = pd.crosstab(
        df[row_var].astype("string").fillna("(Perdido)"),
        df[col_var].astype("string").fillna("(Perdido)"),
        dropna=False,
        **kwargs,
    )
    if normalize is not None:
        table = table * 100
    return table.round(2)
