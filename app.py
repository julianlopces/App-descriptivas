from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.crosstabs import (
    TABLE_TYPE_LABELS,
    build_crosstab_excel,
    compute_crosstab,
    format_crosstab_for_display,
    iter_crosstab_tables,
)
from src.data_loader import (
    get_excel_sheets,
    load_uploaded_file,
    normalize_columns,
)
from src.descriptive_stats import (
    categorical_summary,
    continuous_summary,
    detect_variable_types,
)
from src.palettes import (
    get_available_palettes,
    get_default_style_for_palette,
    get_palette_colors,
)
from src.plots import bar_chart, histogram, scatter_plot, to_png_bytes
from src.theme import INSTITUTIONAL_COLORS, get_institutional_css
from src.utils import dataframe_to_csv_bytes, dataframe_to_excel_bytes, tables_to_excel_bytes


st.set_page_config(
    page_title="QuanTi Stats",
    layout="wide",
    initial_sidebar_state="expanded",
)


FONT_FAMILIES = {
    "Geologica": "Geologica, Arial, sans-serif",
    "Arial": "Arial, Helvetica, sans-serif",
    "Inter": "Inter, Arial, sans-serif",
    "Verdana": "Verdana, Arial, sans-serif",
    "Helvetica": "Helvetica, Arial, sans-serif",
    "Georgia": "Georgia, serif",
    "Courier New": "\"Courier New\", Courier, monospace",
    "Times New Roman": "\"Times New Roman\", Times, serif",
}

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "media" / "Equilibrium-Logo-Completo-Azul.png"


def get_logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_styles() -> None:
    st.markdown(
        get_institutional_css(),
        unsafe_allow_html=True,
    )


def render_app_header(subtitle: str) -> None:
    logo_data_uri = get_logo_data_uri()
    logo_html = (
        f'<img src="{logo_data_uri}" alt="Equilibrium logo">' if logo_data_uri else "QS"
    )
    st.markdown(
        f"""
        <div class="app-title">
            <div class="logo-mark">{logo_html}</div>
            <div class="title-copy">
                <strong>QuanTi Stats</strong>
                <span>{escape(subtitle)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_table_value(value: object, max_decimals: int) -> object:
    if isinstance(value, bool) or value is None:
        return value
    if pd.isna(value):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        rounded = round(value, max_decimals)
        if float(rounded).is_integer():
            return str(int(rounded))
        formatted = f"{rounded:.{max_decimals}f}"
        return formatted.rstrip("0").rstrip(".")
    return value


def style_table(table: pd.DataFrame, max_decimals: int) -> pd.io.formats.style.Styler:
    colors = INSTITUTIONAL_COLORS
    formatter = {
        column: (lambda value, decimals=max_decimals: format_table_value(value, decimals))
        for column in table.columns
    }
    return table.style.format(formatter).set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", colors["primary"]),
                    ("color", colors["white"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                    ("font-weight", "700"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("background-color", colors["white"]),
                    ("color", colors["text_strong"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                ],
            },
            {
                "selector": "tbody th",
                "props": [
                    ("background-color", colors["panel_muted"]),
                    ("color", colors["text_strong"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                    ("font-weight", "600"),
                ],
            },
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("border", f"1px solid {colors['night_blue']}"),
                ],
            },
        ]
    )


def render_styled_table(
    table: pd.DataFrame,
    *,
    height: int,
    key_prefix: str,
    max_decimals: int | None = None,
) -> None:
    if max_decimals is None:
        max_decimals = st.number_input(
            "Decimales máximos visibles",
            min_value=0,
            max_value=6,
            value=2,
            step=1,
            key=f"{key_prefix}_table_decimals",
        )
    st.dataframe(style_table(table, int(max_decimals)), use_container_width=True, height=height)


def init_state() -> None:
    defaults = {
        "df": None,
        "raw_df": None,
        "file_name": None,
        "continuous_vars": [],
        "categorical_vars": [],
        "custom_missing_values": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


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
        if pd.api.types.is_numeric_dtype(series) and numeric_missing:
            numeric_mask = pd.to_numeric(series, errors="coerce").isin(numeric_missing).fillna(False)
            mask = string_mask | numeric_mask
        else:
            mask = string_mask
        if mask.any():
            cleaned.loc[mask, column] = pd.NA

    return cleaned


def chip_list(title: str, items: list[str], kind: str, badge: str) -> None:
    st.markdown(f'<div class="side-heading">{escape(title)}</div>', unsafe_allow_html=True)
    if not items:
        st.caption("Sin variables seleccionadas.")
        return
    html = "\n".join(
        f'<div class="chip {kind}"><span>{escape(item)}</span><code>{escape(badge)}</code></div>'
        for item in items[:12]
    )
    if len(items) > 12:
        html += f'<div class="chip dark"><span>+ {len(items) - 12} variables mas</span><code>...</code></div>'
    st.markdown(html, unsafe_allow_html=True)


def dataset_card(df: pd.DataFrame | None) -> None:
    if df is None:
        body = """
        <div class="dataset-card">
            <div class="file-name">Sin dataset cargado</div>
            <div class="file-meta">CSV, XLSX o XLS</div>
        </div>
        """
    else:
        file_name = escape(st.session_state.file_name or "Dataset cargado")
        body = f"""
        <div class="dataset-card">
            <div class="file-name">{file_name}</div>
            <div class="file-meta">n = {df.shape[0]:,} casos - {df.shape[1]:,} variables</div>
        </div>
        """
    st.markdown(body, unsafe_allow_html=True)


def load_controls() -> None:
    render_app_header("v1.0 - campo rápido")
    st.divider()
    st.markdown('<div class="side-heading">Dataset</div>', unsafe_allow_html=True)
    dataset_card(st.session_state.df)

    uploaded = st.file_uploader(
        "Cargar archivo",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    if not uploaded:
        return

    suffix = uploaded.name.rsplit(".", 1)[-1].lower()
    sheet_name = None
    csv_encoding = "utf-8"
    csv_separator = "Auto"

    with st.expander("Opciones de lectura", expanded=False):
        if suffix in {"xlsx", "xls"}:
            try:
                sheets = get_excel_sheets(uploaded)
            except Exception as exc:
                st.error(f"No fue posible leer las hojas del archivo Excel: {exc}")
                return
            sheet_name = st.selectbox("Hoja de Excel", sheets)
        else:
            csv_encoding = st.selectbox(
                "Codificación",
                ["utf-8", "utf-8-sig", "latin-1", "cp1252"],
                index=0,
            )
            csv_separator = st.selectbox(
                "Separador",
                ["Auto", ",", ";", "\\t", "|"],
                index=0,
            )

    if st.button("Cargar dataset", type="primary", use_container_width=True):
        try:
            loaded = load_uploaded_file(
                uploaded,
                sheet_name=sheet_name,
                csv_encoding=csv_encoding,
                csv_separator=csv_separator,
            )
            loaded = normalize_columns(loaded)
            if loaded.empty:
                st.error("El archivo no contiene filas de datos.")
                return
            st.session_state.raw_df = loaded
            missing_values = parse_custom_missing_values(st.session_state.custom_missing_values)
            loaded_for_analysis = apply_custom_missing_values(loaded, missing_values)
            st.session_state.df = loaded_for_analysis
            st.session_state.file_name = uploaded.name
            detected = detect_variable_types(loaded_for_analysis)
            st.session_state.continuous_vars = detected["continuous"]
            st.session_state.categorical_vars = detected["categorical"]
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible cargar el archivo: {exc}")


def variable_controls(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    all_columns = list(df.columns)

    st.markdown('<div class="side-heading">Ajustes de lectura</div>', unsafe_allow_html=True)
    with st.expander("Ajustar tipos", expanded=False):
        continuous = st.multiselect(
            "Continuas",
            all_columns,
            default=[c for c in st.session_state.continuous_vars if c in all_columns],
        )
        categorical_options = [c for c in all_columns if c not in continuous]
        categorical = st.multiselect(
            "Categóricas",
            categorical_options,
            default=[c for c in st.session_state.categorical_vars if c in categorical_options],
        )

    with st.expander("Control de missing", expanded=False):
        st.text_area(
            "Valores personalizados como missing",
            key="custom_missing_values",
            placeholder="Ejemplo: 9999, 0000, NS/NR",
            help=(
                "Escribe valores separados por coma, punto y coma o salto de línea. "
                "La app los tratará como valores perdidos además de las celdas vacías."
            ),
            height=92,
        )
        custom_missing = parse_custom_missing_values(st.session_state.custom_missing_values)
        if custom_missing:
            raw_df = st.session_state.raw_df
            added_missing = 0
            if raw_df is not None:
                added_missing = int(df.isna().sum().sum() - raw_df.isna().sum().sum())
            st.caption(
                f"Valores activos: {', '.join(custom_missing[:8])}"
                f"{'...' if len(custom_missing) > 8 else ''}. "
                f"Celdas adicionales tratadas como perdidas: {max(added_missing, 0):,}."
            )
        else:
            st.caption("Sin valores personalizados. Solo se tratan como perdidas las celdas vacías o nulas.")

    st.session_state.continuous_vars = continuous
    st.session_state.categorical_vars = categorical

    return continuous, categorical


def metric_html(label: str, value: str, detail: str) -> str:
    colors = INSTITUTIONAL_COLORS
    return f"""
    <div
        class="metric-card"
        style="
            min-height: 112px;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid {colors["primary"]};
            background: linear-gradient(180deg, {colors["primary"]}, {colors["secondary_blue"]});
            box-shadow: 0 12px 24px rgba(2, 15, 80, 0.18);
            color: {colors["white"]};
        "
    >
        <small style="display:block; color:{colors['white']}; font-weight:800; margin-bottom:0.35rem; opacity:0.96;">{escape(label)}</small>
        <strong style="display:block; color:{colors['white']}; font-size:2rem; line-height:1; font-weight:800;">{escape(value)}</strong>
        <span style="display:block; color:{colors['white']}; font-size:0.85rem; margin-top:0.35rem; font-weight:700; opacity:0.92;">{escape(detail)}</span>
    </div>
    """


def overview_metrics(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    html = f"""
    <div
        class="metric-grid"
        style="
            display:grid;
            grid-template-columns:repeat(2, minmax(0, 1fr));
            gap:0.85rem;
            margin:0.35rem 0 1rem;
            align-items:stretch;
        "
    >
        {metric_html("N total", f"{df.shape[0]:,}", "casos válidos en la base")}
        {metric_html("Variables", f"{df.shape[1]:,}", f"{len(continuous_vars)} continuas - {len(categorical_vars)} categóricas")}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def apply_trace_palette(fig, palette: list[str]) -> None:
    if not palette:
        return
    for index, trace in enumerate(fig.data):
        color = palette[index % len(palette)]
        trace_type = getattr(trace, "type", "")
        if trace_type in {"scatter", "scattergl"}:
            trace.update(marker={"color": color, "line": {"color": color}})
        elif trace_type in {"bar", "histogram"}:
            trace.update(marker={"color": color, "line": {"color": color, "width": 0.5}})
        elif hasattr(trace, "marker"):
            trace.update(marker={"color": color})


def sync_palette_style_defaults(selected_palette: str) -> None:
    new_defaults = get_default_style_for_palette(selected_palette)
    applied_palette = st.session_state.get("chart_palette_applied")

    for field, value in new_defaults.items():
        state_key = f"chart_{field}"
        if state_key not in st.session_state:
            st.session_state[state_key] = value

    if not applied_palette or applied_palette == selected_palette:
        st.session_state["chart_palette_applied"] = selected_palette
        return

    old_defaults = get_default_style_for_palette(applied_palette)
    for field, old_value in old_defaults.items():
        state_key = f"chart_{field}"
        if st.session_state.get(state_key) == old_value:
            st.session_state[state_key] = new_defaults[field]

    st.session_state["chart_palette_applied"] = selected_palette


def chart_style_controls(chart_type: str | None = None) -> dict[str, object]:
    with st.expander("Estilo del gráfico", expanded=True):
        available_palettes = get_available_palettes()
        palette_options = list(available_palettes.keys())
        if "chart_palette_name" not in st.session_state:
            st.session_state["chart_palette_name"] = palette_options[0]

        palette_name = st.selectbox(
            "Paleta de colores",
            palette_options,
            index=palette_options.index(st.session_state["chart_palette_name"]),
            key="chart_palette_name",
        )
        sync_palette_style_defaults(palette_name)
        col1, col2 = st.columns(2)
        with col1:
            paper_bg = st.color_picker("Fondo externo", key="chart_paper_bg")
            plot_bg = st.color_picker("Fondo del area", key="chart_plot_bg")
            text_color = st.color_picker("Color de letras", key="chart_text_color")
        with col2:
            grid_color = st.color_picker("Color de grilla", key="chart_grid_color")
            font_family = st.selectbox(
                "Fuente",
                list(FONT_FAMILIES.keys()),
            )
            font_size = st.slider("Tamaño de fuente", 10, 28, 16)
        orientation = None
        if chart_type == "Barras":
            orientation = st.segmented_control(
                "Orientación",
                ["Vertical", "Horizontal"],
                default="Vertical",
                key="bar_orientation",
                help="Define si las barras se muestran de abajo hacia arriba o de izquierda a derecha.",
            )
        show_grid = st.toggle("Mostrar grilla", value=True)
    return {
        "palette_name": palette_name,
        "palette": get_palette_colors(palette_name),
        "legend_title": "",
        "show_title": True,
        "title_alignment": "Centro",
        "show_grid": show_grid,
        "paper_bg": paper_bg,
        "plot_bg": plot_bg,
        "text_color": text_color,
        "grid_color": grid_color,
        "font_family": font_family,
        "font_size": font_size,
        "orientation": orientation,
    }


def style_figure(fig, style: dict[str, object]) -> None:
    palette = style["palette"]
    apply_trace_palette(fig, palette if isinstance(palette, list) else [])
    paper_bg = str(style["paper_bg"])
    plot_bg = str(style["plot_bg"])
    text_color = str(style["text_color"])
    grid_color = str(style["grid_color"])
    selected_font = str(style["font_family"])
    font_family = FONT_FAMILIES.get(selected_font, selected_font)
    font_size = int(style["font_size"])
    legend_title = str(style.get("legend_title", "")).strip()
    show_title = bool(style.get("show_title", True))
    show_grid = bool(style.get("show_grid", True))
    title_alignment = str(style.get("title_alignment", "Centro"))
    title_x = {"Izquierda": 0.0, "Centro": 0.5, "Derecha": 1.0}.get(title_alignment, 0.5)
    title_anchor = {"Izquierda": "left", "Centro": "center", "Derecha": "right"}.get(
        title_alignment,
        "center",
    )
    current_title = fig.layout.title.text if fig.layout.title and fig.layout.title.text else ""
    title_text = f"<b>{escape(current_title)}</b>" if show_title and current_title else ""
    trace_names = [
        str(getattr(trace, "name", "") or "")
        for trace in fig.data
        if getattr(trace, "showlegend", True)
    ]
    legend_source = [legend_title] if legend_title else []
    if getattr(fig.layout.legend.title, "text", None):
        legend_source.append(str(fig.layout.legend.title.text))
    legend_source.extend(trace_names)
    longest_legend_text = max((len(text.strip()) for text in legend_source if text), default=0)
    legend_margin = max(170, min(320, int(longest_legend_text * (font_size * 0.78)) + 42))
    chart_width = 900 + max(0, legend_margin - 170)
    fig.update_layout(
        template="plotly_dark",
        width=chart_width,
        height=520,
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        font={"color": text_color, "family": font_family, "size": font_size},
        title={
            "text": title_text,
            "x": title_x,
            "xanchor": title_anchor,
            "font": {"color": text_color, "family": font_family, "size": font_size + 4},
        },
        legend={
            "bgcolor": paper_bg,
            "bordercolor": paper_bg,
            "font": {"color": text_color, "family": font_family, "size": font_size},
            "title": {
                "font": {"color": text_color, "family": font_family, "size": font_size + 1}
            },
            "x": 1.02,
            "xanchor": "left",
            "y": 1.0,
            "yanchor": "top",
        },
        margin={"l": 48, "r": legend_margin, "t": 56, "b": 48},
    )
    if legend_title:
        fig.update_layout(legend_title_text=legend_title)
    x_showgrid = False if not show_grid else (False if fig.layout.xaxis.showgrid is False else True)
    y_showgrid = False if not show_grid else (False if fig.layout.yaxis.showgrid is False else True)
    fig.update_xaxes(
        color=text_color,
        gridcolor=grid_color,
        linecolor=text_color,
        showgrid=x_showgrid,
        tickfont={"color": text_color, "family": font_family, "size": font_size},
        title_font={"color": text_color, "family": font_family, "size": font_size},
        zerolinecolor=grid_color,
    )
    fig.update_yaxes(
        color=text_color,
        gridcolor=grid_color,
        linecolor=text_color,
        showgrid=y_showgrid,
        tickfont={"color": text_color, "family": font_family, "size": font_size},
        title_font={"color": text_color, "family": font_family, "size": font_size},
        zerolinecolor=grid_color,
    )


def chart_title_controls(default_title: str, key_prefix: str) -> str:
    title = st.text_input(
        "Título",
        default_title,
        key=f"{key_prefix}_title",
        help="Texto principal que aparecerá en la parte superior del gráfico.",
    )
    show_title = st.toggle(
        "Mostrar título",
        value=True,
        key=f"{key_prefix}_show_title",
        help="Activa o desactiva la visibilidad del título en el gráfico.",
    )
    title_alignment = st.segmented_control(
        "Alineación del título",
        ["Izquierda", "Centro", "Derecha"],
        default="Centro",
        key=f"{key_prefix}_title_alignment",
        help="Define en qué parte superior del gráfico se ubicará el título.",
    )
    st.session_state[f"{key_prefix}_title_options"] = {
        "show_title": show_title,
        "title_alignment": title_alignment,
    }
    return title


def axis_range_controls(
    x_label: str,
    y_label: str,
    *,
    key_prefix: str,
    x_numeric: bool,
    y_numeric: bool,
) -> dict[str, tuple[float | None, float | None] | None]:
    st.markdown("**Rango de ejes**")
    use_custom_ranges = st.toggle(
        "Personalizar rango de ejes",
        value=False,
        key=f"{key_prefix}_use_axis_ranges",
        help="Permite fijar el mínimo y/o el máximo de los ejes. Si completas solo uno, el otro se calcula automáticamente.",
    )
    x_range: tuple[float | None, float | None] | None = None
    y_range: tuple[float | None, float | None] | None = None

    if use_custom_ranges:
        if x_numeric:
            st.caption(f"{x_label}: activa mínimo y/o máximo para fijar el rango.")
            col_x_min, col_x_max = st.columns(2)
            with col_x_min:
                use_x_min = st.checkbox("Usar Min X", key=f"{key_prefix}_use_x_min")
                x_min_value = st.number_input(
                    "Min X",
                    value=float(st.session_state.get(f"{key_prefix}_x_min_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_x_min_value",
                    disabled=not use_x_min,
                )
            with col_x_max:
                use_x_max = st.checkbox("Usar Max X", key=f"{key_prefix}_use_x_max")
                x_max_value = st.number_input(
                    "Max X",
                    value=float(st.session_state.get(f"{key_prefix}_x_max_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_x_max_value",
                    disabled=not use_x_max,
                )
            x_range = (
                float(x_min_value) if use_x_min else None,
                float(x_max_value) if use_x_max else None,
            )

        if y_numeric:
            st.caption(f"{y_label}: activa mínimo y/o máximo para fijar el rango.")
            col_y_min, col_y_max = st.columns(2)
            with col_y_min:
                use_y_min = st.checkbox("Usar Min Y", key=f"{key_prefix}_use_y_min")
                y_min_value = st.number_input(
                    "Min Y",
                    value=float(st.session_state.get(f"{key_prefix}_y_min_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_y_min_value",
                    disabled=not use_y_min,
                )
            with col_y_max:
                use_y_max = st.checkbox("Usar Max Y", key=f"{key_prefix}_use_y_max")
                y_max_value = st.number_input(
                    "Max Y",
                    value=float(st.session_state.get(f"{key_prefix}_y_max_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_y_max_value",
                    disabled=not use_y_max,
                )
            y_range = (
                float(y_min_value) if use_y_min else None,
                float(y_max_value) if use_y_max else None,
            )

    return {
        "x_range": x_range,
        "y_range": y_range,
    }


def apply_axis_ranges(fig, axis_ranges: dict[str, tuple[float | None, float | None] | None]) -> None:
    def complete_range(axis_name: str, requested_range: tuple[float | None, float | None]) -> tuple[float | None, float | None]:
        start, end = requested_range
        if start is not None and end is not None:
            return start, end
        try:
            full_fig = fig.full_figure_for_development(warn=False)
            full_axis = getattr(full_fig.layout, f"{axis_name}axis", None)
            computed_range = getattr(full_axis, "range", None) if full_axis else None
            if computed_range and len(computed_range) == 2:
                start = computed_range[0] if start is None else start
                end = computed_range[1] if end is None else end
        except Exception:
            pass
        return start, end

    x_range = axis_ranges.get("x_range")
    y_range = axis_ranges.get("y_range")

    if x_range and any(limit is not None for limit in x_range):
        x_min, x_max = x_range
        x_min, x_max = complete_range("x", (x_min, x_max))
        if x_min is not None or x_max is not None:
            fig.update_xaxes(range=[x_min, x_max], autorange=False)

    if y_range and any(limit is not None for limit in y_range):
        y_min, y_max = y_range
        y_min, y_max = complete_range("y", (y_min, y_max))
        if y_min is not None or y_max is not None:
            fig.update_yaxes(range=[y_min, y_max], autorange=False)


def panel_start(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{escape(title)}</div>
            <div class="panel-subtitle">{escape(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">Carga una base para comenzar</div>
            <div class="panel-subtitle">
                Usa el panel izquierdo para subir un CSV, XLSX o XLS. Luego podrás clasificar variables
                y generar tablas o gráficos desde los módulos horizontales.
            </div>
            <div class="note-card">
                El flujo queda organizado como un tablero: dataset y variables a la izquierda;
                análisis, tablas, gráficos y exportación a la derecha.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing_page() -> None:
    """Full-screen landing shown only when no dataset is loaded."""
    primary = INSTITUTIONAL_COLORS["primary"]  # #020F50

    # Logo blanco para fondo oscuro
    white_logo_path = PROJECT_ROOT / "media" / "Equilibrium-Logo-Blanco.png"
    if white_logo_path.exists():
        encoded = base64.b64encode(white_logo_path.read_bytes()).decode("ascii")
        logo_data_uri = f"data:image/png;base64,{encoded}"
    else:
        logo_data_uri = get_logo_data_uri()

    # ------------------------------------------------------------------ #
    # CSS condicional — solo activo mientras no hay dataset               #
    # ------------------------------------------------------------------ #
    st.markdown(
        f"""
        <style>
        /* Fondo oscuro institucional */
        .stApp {{
            background-color: {primary} !important;
        }}
        header[data-testid="stHeader"] {{
            background: {primary} !important;
            border-bottom: 1px solid rgba(255,255,255,0.08) !important;
        }}
        /* Ocultar sidebar y botón de colapso */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        section[data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}
        /* Centrar contenido */
        .block-container {{
            padding-top: 1.5rem !important;
            max-width: 860px !important;
            margin: 0 auto !important;
        }}

        /* ── Dropzone: fondo plomo claro, borde continuo ────────────── */
        [data-testid="stFileUploaderDropzone"] {{
            background: #F1F5F9 !important;
            border: 1px solid #94A3B8 !important;
            border-radius: 12px !important;
            padding: 0 !important;
        }}
        /* Layout vertical centrado */
        .stFileUploader > section {{
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 2.5rem !important;
            text-align: center !important;
        }}
        /* Ocultar SOLO el texto nativo de límite (e.g. "200MB per file") — NO el bloque del archivo */
        .stFileUploader > section > div [data-testid="stMarkdownContainer"] {{
            display: none !important;
        }}
        /* Texto superior en reposo: solo cuando NO hay archivo cargado */
        .stFileUploader > section:not(:has([data-testid="stFileUploaderFileData"]))::before {{
            content: "Arrastre la bases de datos aquí o haga click para buscar" !important;
            display: block !important;
            margin-bottom: 15px !important;
            color: #1E293B !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
        }}
        /* Texto inferior en reposo: solo cuando NO hay archivo cargado */
        .stFileUploader > section:not(:has([data-testid="stFileUploaderFileData"]))::after {{
            content: "Tamaño máximo: 200 MB" !important;
            display: block !important;
            margin-top: 15px !important;
            color: #1E293B !important;
            font-size: 0.85rem !important;
            font-weight: 400 !important;
        }}
        /* ── Pastilla del archivo cargado ────────────────────────────── */
        [data-testid="stFileUploaderFileData"] {{
            display: flex !important;
            background-color: #FFFFFF !important;
            padding: 8px 12px !important;
            border-radius: 4px !important;
            margin-top: 10px !important;
        }}
        [data-testid="stFileUploaderFileName"],
        [data-testid="stFileUploaderFileData"] span,
        [data-testid="stFileUploaderFileData"] p {{
            color: #1E293B !important;
            font-weight: 500 !important;
        }}
        [data-testid="stFileUploaderFileData"] div svg,
        [data-testid="stFileUploaderFileData"] svg,
        .stFileUploader [data-testid="stFileUploaderFileData"] svg {{
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
            stroke: #FFFFFF !important;
        }}
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] div {{
            color: #1E293B !important;
        }}
        [data-testid="stFileUploaderDropzone"] svg {{
            color: #1E293B !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }}
        /* Botón "Browse files" */
        [data-testid="stFileUploaderDropzone"] button {{
            background: #FFFFFF !important;
            border: 1px solid #94A3B8 !important;
            color: #1E293B !important;
        }}
        [data-testid="stFileUploaderDropzone"] button * {{
            color: #1E293B !important;
        }}

        /* ── Chip del archivo cargado: fondo blanco, texto oscuro ─────── */
        [data-testid="stFileUploaderFile"],
        [data-testid="stUploadedFile"] {{
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }}
        [data-testid="stFileUploaderFileName"],
        [data-testid="stFileUploaderFileSize"],
        [data-testid="stFileUploaderFile"] *,
        [data-testid="stUploadedFile"] *,
        .stFileUploader span,
        .stFileUploader p,
        .stFileUploader small {{
            color: #1E293B !important;
        }}
        [data-testid="stFileUploaderFile"] button,
        [data-testid="stUploadedFile"] button {{
            background: transparent !important;
            border: none !important;
        }}
        .stFileUploader button svg {{
            fill: #1E293B !important;
            color: #1E293B !important;
        }}
        /* Icono de documento junto al nombre del archivo cargado */
        .stFileUploader div[data-testid="stFileUploaderFileData"] svg {{
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
        }}

        /* ── Widget labels (etiquetas de todos los inputs) ───────────── */
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] * {{
            color: rgba(255,255,255,0.85) !important;
        }}

        /* ── Expander "Opciones de lectura" ──────────────────────────── */
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] details summary {{
            background: rgba(255,255,255,0.07) !important;
            border-color: rgba(255,255,255,0.20) !important;
            border-radius: 8px !important;
        }}
        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {{
            color: rgba(255,255,255,0.90) !important;
        }}
        [data-testid="stExpander"] summary svg {{
            color: rgba(255,255,255,0.90) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }}
        /* Contenido abierto del expander */
        [data-testid="stExpander"] details > div {{
            background: rgba(255,255,255,0.05) !important;
            border-color: rgba(255,255,255,0.15) !important;
        }}

        /* ── Selectbox cerrado (campo visible) ───────────────────────── */
        [data-testid="stExpander"] [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.12) !important;
            border-color: rgba(255,255,255,0.30) !important;
            border-radius: 6px !important;
        }}
        /* Texto del valor seleccionado */
        [data-testid="stExpander"] [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] [data-baseweb="select"] span,
        [data-testid="stExpander"] [data-baseweb="select"] input,
        [data-testid="stExpander"] [data-baseweb="select"] div[class*="placeholder"] {{
            color: #FFFFFF !important;
        }}
        /* Flecha del selector */
        [data-testid="stExpander"] [data-baseweb="select"] svg {{
            color: #FFFFFF !important;
            fill: currentColor !important;
        }}

        /* ── Dropdown abierto (popover/menú de opciones) ─────────────── */
        /* Fondo blanco con texto oscuro para máximo contraste           */
        [data-baseweb="popover"] [data-baseweb="menu"],
        [data-baseweb="popover"] ul {{
            background: #FFFFFF !important;
        }}
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="popover"] [role="option"] * {{
            background: #FFFFFF !important;
            color: {primary} !important;
        }}
        [data-baseweb="popover"] [role="option"]:hover,
        [data-baseweb="popover"] [role="option"][aria-selected="true"] {{
            background: rgba(2,15,80,0.08) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------ #
    # Logo arriba a la derecha                                            #
    # ------------------------------------------------------------------ #
    if logo_data_uri:
        _, col_logo = st.columns([3, 1])
        with col_logo:
            st.markdown(
                f'<img src="{logo_data_uri}" '
                f'style="width:200px; display:block; margin-left:auto; margin-top:0.5rem;" '
                f'alt="Equilibrium">',
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------ #
    # Título centrado                                                      #
    # ------------------------------------------------------------------ #
    st.markdown(
        """
        <div style="text-align:center; margin:1.5rem 0 2rem;">
            <h1 style="color:#FFFFFF; font-size:3rem; font-weight:800; margin:0 0 0.4rem;">
                QuanTi Stats
            </h1>
            <p style="color:rgba(255,255,255,0.65); font-size:0.82rem; letter-spacing:0.14em;
                      text-transform:uppercase; margin:0;">
                Creado por Equilibrium BDC
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------ #
    # Tarjeta de carga centrada                                           #
    # ------------------------------------------------------------------ #
    _, col_card, _ = st.columns([1, 3, 1])
    with col_card:
        uploaded = st.file_uploader(
            "Arrastre la bases de datos aquí o haga click para buscar",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=False,
            label_visibility="visible",
        )

        # Detectar tipo de archivo para mostrar opciones correctas
        suffix = uploaded.name.rsplit(".", 1)[-1].lower() if uploaded else ""
        sheet_name = None
        csv_encoding = "utf-8"
        csv_separator = "Auto"

        # El expander reacciona reactivamente: Excel → hoja; CSV/otro → encoding+sep
        with st.expander("Opciones de lectura", expanded=bool(uploaded)):
            if uploaded and suffix in {"xlsx", "xls"}:
                try:
                    sheets = get_excel_sheets(uploaded)
                    sheet_name = st.selectbox("Hoja de Excel", sheets)
                except Exception as exc:
                    st.error(f"No fue posible leer las hojas: {exc}")
            else:
                csv_encoding = st.selectbox(
                    "Codificación", ["utf-8", "utf-8-sig", "latin-1", "cp1252"], index=0
                )
                csv_separator = st.selectbox(
                    "Separador", ["Auto", ",", ";", "\\t", "|"], index=0
                )

        if st.button("Cargar dataset", type="primary", use_container_width=True):
            if uploaded is None:
                st.warning("Primero selecciona un archivo.")
            else:
                try:
                    loaded = load_uploaded_file(
                        uploaded,
                        sheet_name=sheet_name,
                        csv_encoding=csv_encoding,
                        csv_separator=csv_separator,
                    )
                    loaded = normalize_columns(loaded)
                    if loaded.empty:
                        st.error("El archivo no contiene filas de datos.")
                    else:
                        st.session_state.raw_df = loaded
                        missing_values = parse_custom_missing_values(
                            st.session_state.custom_missing_values
                        )
                        loaded_for_analysis = apply_custom_missing_values(loaded, missing_values)
                        st.session_state.df = loaded_for_analysis
                        st.session_state.file_name = uploaded.name
                        detected = detect_variable_types(loaded_for_analysis)
                        st.session_state.continuous_vars = detected["continuous"]
                        st.session_state.categorical_vars = detected["categorical"]
                        st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible cargar el archivo: {exc}")

    # ------------------------------------------------------------------ #
    # Footer fijo                                                         #
    # ------------------------------------------------------------------ #
    st.markdown(
        """
        <div style="
            position:fixed; bottom:0; left:0; right:0;
            background:rgba(0,0,0,0.30);
            padding:0.85rem 2rem;
            text-align:center;
        ">
            <div style="margin-bottom:0.35rem;">
                <a href="#" style="color:rgba(255,255,255,0.70); text-decoration:none;
                   margin:0 1rem; font-size:0.80rem;">Privacy Policy</a>
                <a href="#" style="color:rgba(255,255,255,0.70); text-decoration:none;
                   margin:0 1rem; font-size:0.80rem;">Terms of Service</a>
                <a href="#" style="color:rgba(255,255,255,0.70); text-decoration:none;
                   margin:0 1rem; font-size:0.80rem;">Contact Us</a>
                <a href="#" style="color:rgba(255,255,255,0.70); text-decoration:none;
                   margin:0 1rem; font-size:0.80rem;">Social Media Icons</a>
            </div>
            <div style="color:rgba(255,255,255,0.40); font-size:0.72rem;">
                © 2026 Equilibrium BDC. All Rights Reserved.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def continuous_tab(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected_columns = st.multiselect(
        "Variables continuas a mostrar",
        columns,
        default=columns,
        key="continuous_table_filter",
    )
    panel_start("Variables continuas", "Conteo, perdidos, tendencia central, dispersión y percentiles.")
    if not selected_columns:
        st.info("Selecciona al menos una variable continua para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = continuous_summary(df, selected_columns)
    render_styled_table(table, height=430, key_prefix="continuous")
    if not table.empty:
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(table),
                "descriptivas_continuas.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(table, "continuas"),
                "descriptivas_continuas.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    panel_end()
    return table


def categorical_tab(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected_columns = st.multiselect(
        "Variables categóricas a mostrar",
        columns,
        default=columns,
        key="categorical_table_filter",
    )
    max_levels = st.slider("Máximo de categorías por variable", 5, 100, 30)
    panel_start("Variables categóricas", "Frecuencias absolutas, porcentajes y valores perdidos.")
    if not selected_columns:
        st.info("Selecciona al menos una variable categórica para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = categorical_summary(df, selected_columns, max_levels=max_levels)
    render_styled_table(table, height=430, key_prefix="categorical")
    if not table.empty:
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(table),
                "descriptivas_categoricas.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(table, "categoricas"),
                "descriptivas_categoricas.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    panel_end()
    return table


def contingency_tab(df: pd.DataFrame, categorical_vars: list[str]) -> pd.DataFrame:
    if len(categorical_vars) < 2:
        st.info("Selecciona al menos dos variables categóricas.")
        return pd.DataFrame()

    controls, output = st.columns([0.34, 0.66], gap="large")
    with controls:
        st.markdown('<div class="side-heading">Configuración</div>', unsafe_allow_html=True)
        row_var = st.selectbox("Filas", categorical_vars)
        col_var = st.selectbox("Columnas", [c for c in categorical_vars if c != row_var])
        mode = st.selectbox(
            "Mostrar",
            ["Frecuencia absoluta", "Porcentaje por fila", "Porcentaje por columna", "Porcentaje total"],
        )

    normalize_map = {
        "Frecuencia absoluta": None,
        "Porcentaje por fila": "index",
        "Porcentaje por columna": "columns",
        "Porcentaje total": "all",
    }
    table = contingency_table(df, row_var, col_var, normalize=normalize_map[mode])

    with output:
        panel_start(f"{row_var} x {col_var}", mode)
        render_styled_table(table, height=430, key_prefix="cross")
        export_table = table.reset_index()
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(export_table),
                "tabla_cruzada.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(export_table, "tabla_cruzada"),
                "tabla_cruzada.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        panel_end()

    return table


def mass_crosstab_tab(df: pd.DataFrame, categorical_vars: list[str]) -> pd.DataFrame:
    panel_start(
        "Tablas cruzadas por desagregaciones",
        "Las variables principales se muestran como columnas y las variables de desagregación como filas. "
        "Por defecto se excluyen los valores perdidos.",
    )
    if len(categorical_vars) < 2:
        st.info("Selecciona al menos dos variables categóricas para generar tablas cruzadas.")
        panel_end()
        return pd.DataFrame()

    controls, output = st.columns([0.38, 0.62], gap="large")
    with controls:
        st.markdown('<div class="side-heading">Configuración</div>', unsafe_allow_html=True)
        main_vars = st.multiselect(
            "Variables principales",
            categorical_vars,
            key="cross_main_vars",
            help="Estas variables se usarán como columnas en todas las tablas del Excel.",
        )
        disaggregation_vars = st.multiselect(
            "Variables de desagregación sociodemográfica",
            categorical_vars,
            key="cross_disagg_vars",
            help="Estas variables se usarán como filas en todas las tablas del Excel.",
        )
        table_type_label = st.selectbox(
            "Tipo de tabla",
            list(TABLE_TYPE_LABELS.values()),
            key="cross_table_type",
            help="Este formato se aplicará a todas las tablas cruzadas generadas en el archivo.",
        )
        table_decimals = st.number_input(
            "Decimales máximos visibles",
            min_value=0,
            max_value=6,
            value=2,
            step=1,
            key="cross_table_decimals",
            help="Cantidad máxima de decimales para la vista previa y el Excel. Los ceros finales se ocultan.",
        )
        st.caption(
            "El Excel tendrá una hoja única con las tablas agrupadas por variable principal."
        )

    reverse_type_labels = {label: key for key, label in TABLE_TYPE_LABELS.items()}
    table_type = reverse_type_labels[table_type_label]
    shared_vars = sorted(set(main_vars).intersection(disaggregation_vars))
    valid_pairs = [
        (main_var, disagg_var)
        for main_var in main_vars
        for disagg_var in disaggregation_vars
        if main_var != disagg_var
    ]

    with output:
        if not main_vars:
            st.warning("Selecciona al menos una variable principal.")
            panel_end()
            return pd.DataFrame()
        if not disaggregation_vars:
            st.warning("Selecciona al menos una variable de desagregación.")
            panel_end()
            return pd.DataFrame()
        if shared_vars:
            st.warning(
                "Las variables repetidas en ambos grupos se omitirán cuando coincidan: "
                + ", ".join(shared_vars)
            )
        if not valid_pairs:
            st.warning("No hay combinaciones válidas para generar tablas cruzadas.")
            panel_end()
            return pd.DataFrame()

        preview_tables = iter_crosstab_tables(df, main_vars, disaggregation_vars, table_type)
        if not preview_tables:
            st.info("No hay datos válidos para las combinaciones seleccionadas.")
            panel_end()
            return pd.DataFrame()

        panel_start(
            "Vista previa del Excel",
            f"{table_type_label}. Se muestran hasta 5 tablas; el Excel incluirá todas las combinaciones válidas.",
        )
        excel_buffer = build_crosstab_excel(
            df,
            main_vars,
            disaggregation_vars,
            table_type,
            max_decimals=int(table_decimals),
        )
        st.download_button(
            "Descargar Excel",
            excel_buffer.getvalue(),
            "tablas_cruzadas_desagregadas.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="cross_download_excel",
            help="Descarga un Excel con una hoja única y las tablas agrupadas por variable principal.",
        )
        preview_limit = 5
        previous_main = None
        for index, (preview_main, preview_disagg, preview_table) in enumerate(preview_tables[:preview_limit], start=1):
            if preview_main != previous_main:
                st.markdown(f"#### Variable de análisis: {preview_main}")
                previous_main = preview_main
            st.markdown(f"**Tabla {index}: {preview_main} x {preview_disagg}**")
            render_styled_table(
                format_crosstab_for_display(preview_table, table_type, max_decimals=int(table_decimals)),
                height=260,
                key_prefix=f"cross_preview_{index}",
                max_decimals=int(table_decimals),
            )
        if len(preview_tables) > preview_limit:
            st.caption(
                f"Vista previa limitada a {preview_limit} de {len(preview_tables)} tablas. "
                "Descarga el Excel para ver el conjunto completo."
            )
        panel_end()

    panel_end()
    return preview_tables[0][2].reset_index()


def charts_tab(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    controls, output = st.columns([0.32, 0.68], gap="large")
    fig = None
    axis_ranges = {"x_range": None, "y_range": None}

    with controls:
        control_panel = st.container(height=760, border=False)
    with output:
        preview_panel = st.container(height=760, border=False)

    with control_panel:
        with st.expander("Tipo de gráfico", expanded=True):
            chart_type = st.radio(
                "Tipo de gráfico",
                ["Barras", "Histograma", "Gráfico de dispersión"],
                horizontal=False,
                label_visibility="collapsed",
            )
            barmode = "Apiladas"
            percent = False
            bins = 30
            show_trendline = False
            if chart_type == "Barras":
                barmode = st.segmented_control(
                    "Modo de barras",
                    ["Apiladas", "Agrupadas"],
                    default="Apiladas",
                    help="Define si las barras se muestran apiladas o una al lado de la otra.",
                )
                percent = st.toggle(
                    "Mostrar porcentajes",
                    value=False,
                    help="Si se activa, el eje Y se expresa en porcentaje en lugar de frecuencia.",
                )
            elif chart_type == "Histograma":
                bins = st.slider(
                    "Bins",
                    5,
                    100,
                    30,
                    help="Cantidad de intervalos usados para agrupar los datos.",
                )
            else:
                show_trendline = st.toggle(
                    "Mostrar línea de ajuste",
                    value=False,
                    help="Agrega una línea de ajuste para resumir la relación entre X e Y.",
                )

        if chart_type == "Histograma":
            if not continuous_vars:
                st.info("No hay variables continuas seleccionadas.")
                return
            with st.expander("Selección de variables", expanded=True):
                x = st.selectbox(
                    "Variable continua",
                    continuous_vars,
                    help="Variable numérica que se distribuirá en el histograma.",
                )
                color = st.selectbox("Agrupación/color", ["Ninguna"] + categorical_vars)
            with st.expander("Textos, etiquetas y rango de ejes", expanded=True):
                title = chart_title_controls(f"Histograma de {x}", "hist")
                x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
                y_label = st.text_input("Eje Y", "Frecuencia", help="Texto visible del eje vertical.")
                legend_title = st.text_input(
                    "Título de la leyenda",
                    "" if color == "Ninguna" else color,
                    key="hist_legend_title",
                    help="Nombre que aparecerá sobre la leyenda del gráfico.",
                )
                axis_ranges = axis_range_controls(
                    x_label,
                    y_label,
                    key_prefix="hist",
                    x_numeric=True,
                    y_numeric=True,
                )
            style_config = chart_style_controls(chart_type)
            style_config.update(st.session_state["hist_title_options"])
            style_config["legend_title"] = legend_title
            fig = histogram(
                df,
                x=x,
                color=None if color == "Ninguna" else color,
                color_sequence=style_config["palette"],
                title=title,
                x_label=x_label,
                y_label=y_label,
                bins=bins,
                width=900,
                height=520,
                percent=False,
            )

        elif chart_type == "Barras":
            if not categorical_vars:
                st.info("No hay variables categóricas seleccionadas.")
                return
            with st.expander("Selección de variables", expanded=True):
                x = st.selectbox(
                    "Variable de conteo/principal",
                    categorical_vars,
                    help="Variable cuyas categorías se verán en el eje principal.",
                )
                color_options = [c for c in categorical_vars if c != x]
                color = st.selectbox(
                    "Variable para desagregar/color",
                    ["Ninguna"] + color_options,
                    help="Variable opcional para separar las barras por color.",
                )
                facet_options = [
                    c
                    for c in categorical_vars
                    if c not in {x, None if color == "Ninguna" else color}
                ]
                facet = st.selectbox(
                    "Tercera variable / panel",
                    ["Ninguna"] + facet_options,
                    help="Crea paneles adicionales para una tercera variable categórica.",
                )
                percent_denominator = "total"
                if percent:
                    denominator_options = {"Total general": "total", f"Total por {x}": "x"}
                    if color != "Ninguna":
                        denominator_options[f"Total por {color}"] = "color"
                    if facet != "Ninguna":
                        denominator_options[f"Total por {facet}"] = "facet"
                    denominator_label = st.selectbox(
                        "Calcular porcentaje sobre",
                        list(denominator_options.keys()),
                        help="Elige sobre qué total se calcularán los porcentajes mostrados en las barras.",
                    )
                    percent_denominator = denominator_options[denominator_label]
            orientation_for_ranges = str(st.session_state.get("bar_orientation", "Vertical"))
            with st.expander("Textos, etiquetas y rango de ejes", expanded=True):
                title = chart_title_controls(f"Barras de {x}", "bar")
                x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
                y_label = st.text_input("Eje Y", "Porcentaje" if percent else "Frecuencia", help="Texto visible del eje vertical.")
                legend_title = st.text_input(
                    "Título de la leyenda",
                    "" if color == "Ninguna" else color,
                    key="bar_legend_title",
                    help="Nombre que aparecerá sobre la leyenda del gráfico.",
                )
                show_labels = st.toggle(
                    "Mostrar etiquetas en barras",
                    value=True,
                    help="Muestra el valor o porcentaje directamente sobre cada barra.",
                )
                label_decimals = 2
                if show_labels:
                    label_decimals = st.number_input(
                        "Decimales de etiquetas",
                        min_value=0,
                        max_value=6,
                        value=2,
                        step=1,
                        help="Cantidad máxima de decimales mostrados en las etiquetas.",
                    )
                axis_ranges = axis_range_controls(
                    x_label,
                    y_label,
                    key_prefix="bar",
                    x_numeric=orientation_for_ranges == "Horizontal",
                    y_numeric=orientation_for_ranges == "Vertical",
                )
            style_config = chart_style_controls(chart_type)
            style_config.update(st.session_state["bar_title_options"])
            style_config["legend_title"] = legend_title
            orientation = str(style_config.get("orientation") or "Vertical")
            fig = bar_chart(
                df,
                x=x,
                color=None if color == "Ninguna" else color,
                facet=None if facet == "Ninguna" else facet,
                color_sequence=style_config["palette"],
                title=title,
                x_label=x_label,
                y_label=y_label,
                percent=percent,
                percent_denominator=percent_denominator,
                orientation="h" if orientation == "Horizontal" else "v",
                barmode="stack" if barmode == "Apiladas" else "group",
                show_labels=show_labels,
                label_decimals=int(label_decimals),
                width=900,
                height=520,
            )

        else:
            if len(continuous_vars) < 2:
                st.info("Selecciona al menos dos variables continuas.")
                return
            with st.expander("Selección de variables", expanded=True):
                x = st.selectbox("Variable X", continuous_vars, help="Variable numérica que se mostrará en el eje horizontal.")
                y = st.selectbox("Variable Y", [c for c in continuous_vars if c != x], help="Variable numérica que se mostrará en el eje vertical.")
                color = st.selectbox("Color", ["Ninguna"] + categorical_vars, help="Variable opcional para diferenciar puntos por grupo.")
            trendline_method = "OLS"
            trendline_scope = "overall"
            trendline_color = "#F7966B"
            with st.expander("Textos, etiquetas y rango de ejes", expanded=True):
                title = chart_title_controls(f"{y} vs {x}", "scatter")
                x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
                y_label = st.text_input("Eje Y", y, help="Texto visible del eje vertical.")
                legend_title = st.text_input(
                    "Título de la leyenda",
                    "" if color == "Ninguna" else color,
                    key="scatter_legend_title",
                    help="Nombre que aparecerá sobre la leyenda del gráfico.",
                )
                if show_trendline:
                    trendline_method = st.selectbox(
                        "Método de ajuste",
                        ["OLS"],
                        index=0,
                        help="Método estadístico usado para calcular la línea de ajuste.",
                    )
                    if color != "Ninguna":
                        trendline_scope_label = st.selectbox(
                            "Cálculo de la línea de ajuste",
                            ["General", "Por subgrupos"],
                            index=0,
                            help="Elige si la línea de ajuste se calcula para todos los puntos o por cada grupo de color.",
                        )
                        trendline_scope = "overall" if trendline_scope_label == "General" else "trace"
                    if color == "Ninguna" or trendline_scope == "overall":
                        trendline_color = st.color_picker(
                            "Color de la línea de ajuste",
                            value="#F7966B",
                            help="Color aplicado a la línea de ajuste general.",
                        )
                    else:
                        st.caption("Las líneas de ajuste por subgrupos usarán automáticamente el mismo color que sus puntos.")
                axis_ranges = axis_range_controls(
                    x_label,
                    y_label,
                    key_prefix="scatter",
                    x_numeric=True,
                    y_numeric=True,
                )
            style_config = chart_style_controls(chart_type)
            style_config.update(st.session_state["scatter_title_options"])
            style_config["legend_title"] = legend_title
            fig = scatter_plot(
                df,
                x=x,
                y=y,
                color=None if color == "Ninguna" else color,
                color_sequence=style_config["palette"],
                show_trendline=show_trendline,
                trendline_method=trendline_method,
                trendline_scope=trendline_scope,
                trendline_color=trendline_color,
                title=title,
                x_label=x_label,
                y_label=y_label,
                width=900,
                height=520,
            )

    if fig is None:
        return

    style_figure(fig, style_config)
    apply_axis_ranges(fig, axis_ranges)
    with preview_panel:
        panel_start("Vista del gráfico", "Personalizable y listo para incluir en informes.")
        st.plotly_chart(fig, use_container_width=True)
        png = to_png_bytes(fig)
        if png:
            st.download_button("Descargar PNG", png, "grafico.png", "image/png")
        else:
            st.caption("La exportación PNG requiere que kaleido funcione correctamente en el entorno.")
        st.markdown(
            """
            <div class="note-card">
                Tip: usa color o agrupación para comparar segmentos. Para informes, exporta PNG o descarga
                la tabla base del módulo correspondiente.
            </div>
            """,
            unsafe_allow_html=True,
        )
        panel_end()


def export_tab(tables: dict[str, pd.DataFrame]) -> None:
    panel_start("Exportar resultados", "Descarga tablas descriptivas y salidas principales.")
    available = {name: table for name, table in tables.items() if not table.empty}
    if not available:
        st.info("Aun no hay tablas para exportar.")
    else:
        for name, table in available.items():
            st.markdown(f"**{name.replace('_', ' ').title()}**")
            col_csv, col_xlsx = st.columns(2)
            with col_csv:
                st.download_button(
                    f"{name} CSV",
                    dataframe_to_csv_bytes(table),
                    f"{name}.csv",
                    "text/csv",
                    use_container_width=True,
                    key=f"export_{name}_csv",
                )
            with col_xlsx:
                st.download_button(
                    f"{name} XLSX",
                    dataframe_to_excel_bytes(table, name),
                    f"{name}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"export_{name}_xlsx",
                )

        st.download_button(
            "Excel completo",
            tables_to_excel_bytes(available),
            "tablas_descriptivas.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    panel_end()


def preview_tab(df: pd.DataFrame) -> None:
    panel_start("Vista previa del dataset", "Primeras filas y estructura general de la base.")
    render_styled_table(df.head(80), height=460, key_prefix="preview")
    missing_by_column = (
        df.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "variable", 0: "valores_perdidos"})
        .sort_values("valores_perdidos", ascending=False)
    )
    with st.expander("Valores perdidos por variable"):
        render_styled_table(missing_by_column, height=300, key_prefix="missing")
    panel_end()


def instructions_tab() -> None:
    panel_start(
        "Instrucciones de uso",
        "Gu\u00eda r\u00e1pida de lo que puedes hacer en cada m\u00f3dulo de la app.",
    )
    st.markdown(
        """
        <div
            style="
                background:#F4D2A4;
                border:1px solid #F4B21B;
                border-radius:8px;
                color:#000031;
                font-size:0.88rem;
                margin-top:0.8rem;
                padding:0.85rem 1rem;
            "
        >
            Sugerencia de flujo: carga la base en el panel izquierdo, revisa la clasificaci&oacute;n de variables y
            luego entra al m&oacute;dulo que necesites para explorar, tabular o exportar resultados.
        </div>
        <div
            style="
                display:grid;
                grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
                gap:0.9rem;
                margin-top:0.9rem;
            "
        >
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Carga y clasificaci&oacute;n</h4>
                <p>Desde el panel izquierdo subes la base y confirmas qu&eacute; variables son continuas o categ&oacute;ricas.</p>
                <ul>
                    <li>Carga archivos CSV, XLSX o XLS.</li>
                    <li>Elige hoja, codificaci&oacute;n o separador si hace falta.</li>
                    <li>Ajusta manualmente la clasificaci&oacute;n de variables.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Vista previa</h4>
                <p>Sirve para revisar r&aacute;pidamente las primeras filas del dataset antes de seguir con el an&aacute;lisis.</p>
                <ul>
                    <li>Inspecciona las primeras filas de la base cargada.</li>
                    <li>Revisa valores perdidos por variable.</li>
                    <li>Confirma nombres de columnas y estructura general del archivo.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Gr&aacute;ficos</h4>
                <p>Construye visualizaciones personalizadas para an&aacute;lisis e informes.</p>
                <ul>
                    <li>Genera barras, histogramas o gr&aacute;ficos de dispersi&oacute;n.</li>
                    <li>Personaliza t&iacute;tulos, ejes, colores, leyenda y rangos.</li>
                    <li>Exporta el gr&aacute;fico como PNG cuando est&eacute; disponible.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Tablas cruzadas</h4>
                <p>Produce tablas masivas entre variables principales y desagregaciones sociodemogr&aacute;ficas.</p>
                <ul>
                    <li>Selecciona varias variables principales.</li>
                    <li>Selecciona varias variables de desagregaci&oacute;n.</li>
                    <li>Descarga un Excel con una hoja por variable principal.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Continuas</h4>
                <p>Resume variables num&eacute;ricas con estad&iacute;sticos descriptivos listos para reporte.</p>
                <ul>
                    <li>Media, mediana, desviaci&oacute;n est&aacute;ndar y percentiles.</li>
                    <li>Conteo de v&aacute;lidos y perdidos.</li>
                    <li>Descarga la tabla en CSV o XLSX.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Categ&oacute;ricas</h4>
                <p>Revisa frecuencias, porcentajes y valores perdidos por categor&iacute;a.</p>
                <ul>
                    <li>Filtra qu&eacute; variables mostrar.</li>
                    <li>Controla el m&aacute;ximo de categor&iacute;as visibles.</li>
                    <li>Descarga la tabla en CSV o XLSX.</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    panel_end()


def main() -> None:
    inject_styles()
    init_state()

    # Landing page completa cuando no hay dataset cargado
    if st.session_state.df is None:
        render_landing_page()
        return

    with st.sidebar:
        load_controls()
        raw_df = st.session_state.raw_df
        if raw_df is None and st.session_state.df is not None:
            raw_df = st.session_state.df
            st.session_state.raw_df = raw_df
        if raw_df is not None:
            missing_values = parse_custom_missing_values(st.session_state.custom_missing_values)
            st.session_state.df = apply_custom_missing_values(raw_df, missing_values)
        df = st.session_state.df
        if df is not None:
            continuous_vars, categorical_vars = variable_controls(df)
        else:
            continuous_vars, categorical_vars = [], []

    render_app_header("Exploración descriptiva modular")

    df = st.session_state.df
    if df is None:
        render_empty_state()
        return

    selected_continuous, selected_categorical = continuous_vars, categorical_vars
    overview_metrics(df, selected_continuous, selected_categorical)

    tables = {
        "continuas": continuous_summary(df, selected_continuous),
        "categoricas": categorical_summary(df, selected_categorical, max_levels=30),
    }

    tab_instructions, tab_preview, tab_graphs, tab_cross, tab_cont, tab_cat = st.tabs(
        ["Instrucciones", "Vista previa", "Gráficos", "Tablas cruzadas", "Continuas", "Categóricas"]
    )

    with tab_instructions:
        instructions_tab()
    with tab_preview:
        preview_tab(df)
    with tab_graphs:
        charts_tab(df, selected_continuous, selected_categorical)
    with tab_cross:
        cross = mass_crosstab_tab(df, selected_categorical)
        if not cross.empty:
            tables["tabla_cruzada"] = cross
    with tab_cont:
        tables["continuas"] = continuous_tab(df, selected_continuous)
    with tab_cat:
        tables["categoricas"] = categorical_tab(df, selected_categorical)


if __name__ == "__main__":
    main()
