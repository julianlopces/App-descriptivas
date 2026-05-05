from __future__ import annotations

from textwrap import dedent


INSTITUTIONAL_COLORS = {
    "primary": "#020F50",
    "secondary_blue": "#1955A6",
    "turquoise": "#7CCCBF",
    "salmon": "#F7966B",
    "yellow": "#F4B21B",
    "light_background": "#F7FAF2",
    "night_blue": "#000031",
    "gray_blue": "#788EC7",
    "light_gray_blue": "#B6C4E5",
    "beige": "#F4D2A4",
    "white": "#FFFFFF",
    "sidebar_background": "#F7FAF2",
    "panel_background": "#FFFFFF",
    "panel_muted": "#F7FAF2",
    "text": "#020F50",
    "text_strong": "#000031",
    "text_inverse": "#FFFFFF",
    "muted_text": "#4A5C8E",
    "border": "#B6C4E5",
    "border_strong": "#788EC7",
    "focus": "#1955A6",
}


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _linearize(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    red, green, blue = _hex_to_rgb(color)
    r_lin = _linearize(red)
    g_lin = _linearize(green)
    b_lin = _linearize(blue)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(foreground: str, background: str) -> float:
    fg_luminance = relative_luminance(foreground)
    bg_luminance = relative_luminance(background)
    lighter = max(fg_luminance, bg_luminance)
    darker = min(fg_luminance, bg_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def pick_text_color(background: str) -> str:
    white_ratio = contrast_ratio(INSTITUTIONAL_COLORS["white"], background)
    dark_ratio = contrast_ratio(INSTITUTIONAL_COLORS["text"], background)
    return INSTITUTIONAL_COLORS["white"] if white_ratio >= dark_ratio else INSTITUTIONAL_COLORS["text"]


def get_institutional_css() -> str:
    colors = INSTITUTIONAL_COLORS
    primary_button_text = pick_text_color(colors["primary"])
    secondary_button_text = pick_text_color(colors["secondary_blue"])
    turquoise_button_text = pick_text_color(colors["turquoise"])
    yellow_button_text = pick_text_color(colors["yellow"])

    return dedent(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Geologica:wght@400;500;600;700&display=swap');

        :root {{
            --bg: {colors["light_background"]};
            --panel: {colors["panel_background"]};
            --panel-soft: {colors["panel_muted"]};
            --stroke: {colors["border"]};
            --stroke-strong: {colors["border_strong"]};
            --text: {colors["text"]};
            --text-strong: {colors["text_strong"]};
            --text-inverse: {colors["text_inverse"]};
            --muted: {colors["muted_text"]};
            --accent: {colors["primary"]};
            --accent-2: {colors["turquoise"]};
            --accent-3: {colors["secondary_blue"]};
            --accent-warm: {colors["yellow"]};
            --accent-soft: {colors["beige"]};
            --sidebar-bg: {colors["sidebar_background"]};
            --sidebar-panel: {colors["white"]};
            --primary-button-text: {primary_button_text};
            --secondary-button-text: {secondary_button_text};
            --turquoise-button-text: {turquoise_button_text};
            --yellow-button-text: {yellow_button_text};
        }}

        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}

        header[data-testid="stHeader"] {{
            background: var(--panel);
            border-bottom: 1px solid var(--stroke);
        }}

        [data-testid="stSidebar"] {{
            background: var(--sidebar-bg);
            border-right: 1px solid var(--stroke);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--text);
        }}

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-baseweb="popover"] *,
        [data-testid="stSidebar"] [data-baseweb="tag"] *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderFileName"],
        [data-testid="stSidebar"] [data-testid="stFileUploaderFileSize"],
        [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] *,
        [data-testid="stSidebar"] [data-testid="stUploadedFile"] *,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] li *,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] small {{
            color: var(--text) !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="base-input"] > div,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {{
            background: var(--sidebar-panel) !important;
            border-color: var(--stroke) !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="tag"] {{
            background: var(--accent-3) !important;
            border-color: var(--accent-3) !important;
            color: var(--text-inverse) !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="tag"] > span,
        [data-testid="stSidebar"] [data-baseweb="tag"] > div,
        [data-testid="stSidebar"] [data-baseweb="tag"] [role="button"],
        [data-testid="stSidebar"] [data-baseweb="tag"] *,
        [data-testid="stSidebar"] [data-baseweb="tag"] span,
        [data-testid="stSidebar"] [data-baseweb="tag"] svg {{
            color: var(--text-inverse) !important;
            -webkit-text-fill-color: var(--text-inverse) !important;
            fill: currentColor !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
        [data-testid="stSidebar"] [data-testid="stUploadedFile"],
        [data-testid="stSidebar"] [data-testid="stFileUploader"] li {{
            background: var(--panel-soft) !important;
            border-color: var(--stroke) !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
            background: var(--panel) !important;
            border: 1px solid var(--stroke-strong) !important;
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {{
            border-color: var(--accent-3) !important;
            background: var(--panel-soft) !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploader"] button *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] div {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] > div {{
            color: var(--text) !important;
        }}

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button svg {{
            color: var(--text) !important;
            fill: currentColor !important;
            opacity: 1 !important;
            stroke: currentColor !important;
        }}

        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder,
        [data-testid="stSidebar"] [data-baseweb="select"] input::placeholder {{
            color: var(--muted) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] svg {{
            color: inherit;
            fill: currentColor;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] svg,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] svg {{
            color: var(--text) !important;
            fill: currentColor;
        }}

        [data-testid="stSidebar"] [role="option"] *,
        [data-testid="stSidebar"] [data-baseweb="menu"] * {{
            color: var(--text) !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"],
        [data-testid="stSidebar"] details,
        [data-testid="stSidebar"] details summary {{
            background: var(--panel) !important;
            border-color: var(--stroke) !important;
            color: var(--text) !important;
        }}

        [data-testid="stSidebar"] details summary *,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary *,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stSidebar"] [data-testid="stExpander"] p,
        [data-testid="stSidebar"] [data-testid="stExpander"] span {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] details summary svg,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{
            color: var(--text) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            opacity: 1 !important;
        }}

        h1, h2, h3 {{
            color: var(--text-strong);
            letter-spacing: 0;
        }}

        [data-testid="stMain"] [data-testid="stWidgetLabel"],
        [data-testid="stMain"] [data-testid="stWidgetLabel"] *,
        [data-testid="stMain"] [data-testid="stRadio"] label,
        [data-testid="stMain"] [data-testid="stRadio"] label *,
        [data-testid="stMain"] [data-testid="stCheckbox"] label,
        [data-testid="stMain"] [data-testid="stCheckbox"] label *,
        [data-testid="stMain"] [data-testid="stToggle"] label,
        [data-testid="stMain"] [data-testid="stToggle"] label *,
        [data-testid="stMain"] [data-testid="stSlider"] label,
        [data-testid="stMain"] [data-testid="stSlider"] label * {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
        [data-testid="stSidebar"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stRadio"] label *,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label *,
        [data-testid="stSidebar"] [data-testid="stToggle"] label,
        [data-testid="stSidebar"] [data-testid="stToggle"] label *,
        [data-testid="stSidebar"] [data-testid="stSlider"] label,
        [data-testid="stSidebar"] [data-testid="stSlider"] label * {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stWidgetLabel"] {{
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 0.4rem !important;
            width: fit-content !important;
            max-width: 100% !important;
        }}

        [data-testid="stWidgetLabel"] > div {{
            width: auto !important;
            flex: 0 1 auto !important;
        }}

        [data-testid="stWidgetLabel"] button {{
            margin-left: 0 !important;
            width: 1.6rem !important;
            height: 1.6rem !important;
            min-width: 1.6rem !important;
            padding: 0 !important;
            border-radius: 999px !important;
            border: 1px solid var(--stroke-strong) !important;
            background: var(--panel) !important;
            color: transparent !important;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 0 !important;
            font-weight: 700 !important;
            line-height: 1 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: relative !important;
            overflow: hidden !important;
        }}

        [data-testid="stWidgetLabel"] button::after {{
            content: "?" !important;
            color: var(--accent) !important;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 0.92rem !important;
            font-weight: 700 !important;
            line-height: 1 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            height: 100% !important;
            position: absolute !important;
            inset: 0 !important;
        }}

        [data-testid="stWidgetLabel"] button:hover,
        [data-testid="stWidgetLabel"] button:focus-visible {{
            border-color: var(--accent-3) !important;
            background: rgba(25, 85, 166, 0.08) !important;
        }}

        [data-testid="stWidgetLabel"] button:hover::after,
        [data-testid="stWidgetLabel"] button:focus-visible::after {{
            color: var(--accent-3) !important;
        }}

        [data-testid="stWidgetLabel"] button svg,
        [data-testid="stWidgetLabel"] button img,
        [data-testid="stWidgetLabel"] button path {{
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }}

        [data-testid="stWidgetLabel"] button > span,
        [data-testid="stWidgetLabel"] button > div,
        [data-testid="stWidgetLabel"] button * {{
            color: transparent !important;
            fill: transparent !important;
            stroke: transparent !important;
            text-shadow: none !important;
        }}

        [data-testid="stMain"] [data-baseweb="radio"] div,
        [data-testid="stMain"] [data-baseweb="radio"] span,
        [data-testid="stMain"] [data-baseweb="checkbox"] div,
        [data-testid="stMain"] [data-baseweb="checkbox"] span {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea,
        [data-testid="stMain"] [data-baseweb="select"] *,
        [data-testid="stMain"] [data-baseweb="base-input"] * {{
            color: var(--text) !important;
        }}

        [data-testid="stMain"] [data-baseweb="select"] > div,
        [data-testid="stMain"] [data-baseweb="base-input"] > div {{
            background: var(--panel) !important;
            border-color: var(--stroke) !important;
        }}

        [data-testid="stMain"] [data-baseweb="tag"] {{
            background: var(--accent-3) !important;
            border-color: var(--accent-3) !important;
            color: var(--text-inverse) !important;
        }}

        [data-testid="stMain"] [data-baseweb="tag"] > span,
        [data-testid="stMain"] [data-baseweb="tag"] > div,
        [data-testid="stMain"] [data-baseweb="tag"] [role="button"],
        [data-testid="stMain"] [data-baseweb="tag"] *,
        [data-testid="stMain"] [data-baseweb="tag"] span,
        [data-testid="stMain"] [data-baseweb="tag"] svg {{
            color: var(--text-inverse) !important;
            -webkit-text-fill-color: var(--text-inverse) !important;
            fill: currentColor !important;
        }}

        [data-testid="stMain"] [data-baseweb="select"] svg {{
            color: var(--text) !important;
            fill: currentColor !important;
        }}

        [data-testid="stMain"] [data-testid="stSegmentedControl"] button {{
            background: var(--panel-soft) !important;
            border-color: var(--stroke-strong) !important;
            color: var(--text) !important;
        }}

        [data-testid="stMain"] [data-testid="stSegmentedControl"] button[aria-pressed="true"],
        [data-testid="stMain"] [data-testid="stSegmentedControl"] button[data-selected="true"] {{
            background: var(--accent-2) !important;
            color: var(--text-strong) !important;
            border-color: var(--accent-3) !important;
            box-shadow: inset 0 0 0 1px var(--accent-3);
        }}

        [data-testid="stMain"] [data-testid="stSegmentedControl"] button *,
        [data-testid="stMain"] [data-testid="stSegmentedControl"] label,
        [data-testid="stMain"] [data-testid="stSegmentedControl"] label * {{
            color: inherit !important;
            opacity: 1 !important;
        }}

        [data-testid="stMain"] [data-testid="stExpander"],
        [data-testid="stMain"] details,
        [data-testid="stMain"] details summary {{
            background: var(--panel) !important;
            border-color: var(--stroke) !important;
            color: var(--text) !important;
        }}

        [data-testid="stMain"] details summary *,
        [data-testid="stMain"] [data-testid="stExpander"] summary *,
        [data-testid="stMain"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stMain"] [data-testid="stExpander"] p,
        [data-testid="stMain"] [data-testid="stExpander"] span {{
            color: var(--text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stMain"] details summary svg,
        [data-testid="stMain"] [data-testid="stExpander"] summary svg {{
            color: var(--text) !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            opacity: 1 !important;
        }}

        .block-container {{
            padding-top: 4.75rem;
            max-width: 1420px;
        }}

        div[data-testid="stTabs"] button {{
            background: var(--panel) !important;
            border: 1px solid var(--stroke) !important;
            border-radius: 8px;
            color: var(--muted) !important;
            min-height: 44px;
            padding: 0.35rem 1rem;
        }}

        div[data-testid="stTabs"] button:hover {{
            border-color: var(--accent-3) !important;
            color: var(--text) !important;
        }}

        div[data-testid="stTabs"] button[aria-selected="true"] {{
            background: var(--accent) !important;
            color: var(--text-inverse) !important;
            border-color: var(--accent) !important;
            font-weight: 700;
        }}

        .app-title {{
            display: flex;
            align-items: center;
            gap: 0.72rem;
            margin-bottom: 1rem;
        }}

        .logo-mark {{
            width: 120px;
            height: 34px;
            display: flex;
            align-items: center;
        }}

        .logo-mark img {{
            display: block;
            width: 100%;
            height: auto;
            object-fit: contain;
        }}

        .title-copy strong {{
            display: block;
            font-size: 1.05rem;
            line-height: 1.1;
            color: var(--text-strong);
        }}

        .title-copy span {{
            color: var(--muted);
            font-size: 0.78rem;
        }}

        .side-heading {{
            color: var(--text-strong);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            margin: 1.25rem 0 0.45rem;
            text-transform: uppercase;
        }}

        .dataset-card,
        .metric-card,
        .panel,
        .note-card {{
            background: var(--panel);
            border: 1px solid var(--stroke);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(2, 15, 80, 0.08);
        }}

        .dataset-card {{
            border-style: dashed;
            padding: 1rem;
            text-align: center;
            margin-bottom: 0.8rem;
        }}

        .dataset-card .file-name {{
            font-weight: 800;
            color: var(--text-strong);
            overflow-wrap: anywhere;
        }}

        .dataset-card .file-meta {{
            color: var(--muted);
            font-size: 0.86rem;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.35rem 0 1rem;
        }}

        .metric-card {{
            min-height: 112px;
            padding: 1rem;
            background: linear-gradient(180deg, var(--accent), var(--accent-3));
            border-color: var(--accent) !important;
            box-shadow: 0 12px 24px rgba(2, 15, 80, 0.18);
        }}

        .metric-card small {{
            color: var(--text-inverse);
            display: block;
            font-weight: 800;
            margin-bottom: 0.35rem;
            opacity: 0.96;
        }}

        .metric-card strong {{
            color: var(--text-inverse);
            display: block;
            font-size: 2rem;
            line-height: 1;
            font-weight: 800;
        }}

        .metric-card span {{
            color: var(--text-inverse);
            display: block;
            font-size: 0.85rem;
            margin-top: 0.35rem;
            font-weight: 700;
            opacity: 0.92;
        }}

        .panel {{
            padding: 1rem;
            margin-top: 0.75rem;
        }}

        .panel-title {{
            color: var(--text-strong);
            font-size: 1rem;
            font-weight: 850;
            margin-bottom: 0.15rem;
        }}

        .panel-subtitle {{
            color: var(--muted);
            font-size: 0.82rem;
            margin-bottom: 0.75rem;
        }}

        .note-card {{
            background: var(--accent-soft);
            border-color: var(--yellow);
            color: var(--text-strong);
            font-size: 0.88rem;
            margin-top: 0.8rem;
            padding: 0.85rem 1rem;
        }}

        .instruction-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.9rem;
            margin-top: 0.9rem;
        }}

        .instruction-card {{
            background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(247,250,242,1) 100%);
            border: 1px solid var(--stroke);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 20px rgba(2, 15, 80, 0.05);
        }}

        .instruction-card h4 {{
            margin: 0 0 0.5rem 0;
            color: var(--accent);
            font-size: 0.96rem;
            font-weight: 700;
        }}

        .instruction-card p {{
            margin: 0 0 0.55rem 0;
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }}

        .instruction-card ul {{
            margin: 0;
            padding-left: 1rem;
            color: var(--text-strong);
            font-size: 0.82rem;
            line-height: 1.5;
        }}

        .instruction-card li + li {{
            margin-top: 0.2rem;
        }}

        .chip {{
            align-items: center;
            background: var(--accent-soft);
            border: 1px solid rgba(244, 178, 27, 0.35);
            border-radius: 7px;
            color: var(--text-strong);
            display: flex;
            font-size: 0.84rem;
            justify-content: space-between;
            margin: 0.34rem 0;
            min-height: 32px;
            padding: 0.34rem 0.55rem;
        }}

        .chip.teal {{
            background: rgba(124, 204, 191, 0.24);
            border-color: rgba(25, 85, 166, 0.28);
            color: var(--text-strong);
        }}

        .chip.dark {{
            background: rgba(182, 196, 229, 0.18);
            border: 1px solid var(--stroke);
            color: var(--muted);
        }}

        .chip code {{
            background: rgba(255, 255, 255, 0.85);
            border-radius: 5px;
            color: inherit;
            font-size: 0.68rem;
            padding: 0.08rem 0.35rem;
        }}

        .stDataFrame {{
            border: 1px solid var(--stroke);
            border-radius: 8px;
            overflow: hidden;
        }}

        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button,
        button[kind="primary"] {{
            border-radius: 8px !important;
            font-weight: 750 !important;
            border: 1px solid var(--accent) !important;
            transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
        }}

        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stDownloadButton"] button[kind="primary"],
        button[kind="primary"] {{
            background: var(--accent) !important;
            color: var(--primary-button-text) !important;
        }}

        [data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"],
        [data-testid="stSidebar"] button[kind="primary"] {{
            background: var(--accent) !important;
            border-color: var(--accent) !important;
            color: var(--text-inverse) !important;
        }}

        div[data-testid="stButton"] button[kind="primary"] *,
        div[data-testid="stDownloadButton"] button[kind="primary"] *,
        button[kind="primary"] * {{
            color: var(--primary-button-text) !important;
            -webkit-text-fill-color: var(--primary-button-text) !important;
            fill: currentColor !important;
        }}

        [data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] *,
        [data-testid="stSidebar"] button[kind="primary"] * {{
            color: var(--text-inverse) !important;
            -webkit-text-fill-color: var(--text-inverse) !important;
            fill: currentColor !important;
        }}

        div[data-testid="stButton"] button[kind="primary"]:hover,
        div[data-testid="stDownloadButton"] button[kind="primary"]:hover,
        button[kind="primary"]:hover {{
            background: var(--accent-3) !important;
            border-color: var(--accent-3) !important;
            color: var(--secondary-button-text) !important;
        }}

        div[data-testid="stButton"] button:not([kind="primary"]) {{
            background: var(--panel) !important;
            border-color: var(--stroke-strong) !important;
            color: var(--text) !important;
        }}

        div[data-testid="stButton"] button:not([kind="primary"]):hover {{
            background: rgba(124, 204, 191, 0.18) !important;
            border-color: var(--accent-3) !important;
            color: var(--text-strong) !important;
        }}

        div[data-testid="stDownloadButton"] button:not([kind="primary"]) {{
            background: var(--accent-3) !important;
            border-color: var(--accent-3) !important;
            color: var(--secondary-button-text) !important;
        }}

        div[data-testid="stDownloadButton"] button:not([kind="primary"]) *,
        div[data-testid="stButton"] button[data-baseweb] *,
        div[data-testid="stDownloadButton"] button[data-baseweb] * {{
            color: inherit !important;
            fill: currentColor !important;
        }}

        div[data-testid="stDownloadButton"] button:not([kind="primary"]) * {{
            color: var(--secondary-button-text) !important;
            fill: currentColor !important;
        }}

        div[data-testid="stDownloadButton"] button:not([kind="primary"]):hover {{
            background: var(--yellow) !important;
            border-color: var(--yellow) !important;
            color: var(--yellow-button-text) !important;
        }}

        div[data-testid="stDownloadButton"] button:not([kind="primary"]):hover * {{
            color: var(--yellow-button-text) !important;
            fill: currentColor !important;
        }}

        button:focus,
        button:focus-visible,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="base-input"] > div:focus-within {{
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(25, 85, 166, 0.18), 0 0 0 4px rgba(25, 85, 166, 0.32) !important;
            border-color: var(--focus) !important;
        }}

        [data-testid="stAlert"] {{
            border-radius: 8px;
            border: 1px solid var(--stroke);
        }}

        [data-testid="stInfo"] {{
            background: rgba(124, 204, 191, 0.16);
            color: var(--text) !important;
        }}

        [data-testid="stSuccess"] {{
            background: rgba(124, 204, 191, 0.22);
            color: var(--text) !important;
        }}

        [data-testid="stWarning"] {{
            background: rgba(244, 178, 27, 0.18);
            color: var(--text-strong) !important;
        }}

        [data-testid="stError"] {{
            background: rgba(247, 150, 107, 0.18);
            color: var(--text-strong) !important;
        }}

        hr, [data-testid="stDivider"] {{
            border-color: var(--stroke) !important;
        }}

        @media (max-width: 1100px) {{
            .metric-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 760px) {{
            .metric-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """
    )
