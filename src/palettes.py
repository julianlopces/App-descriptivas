from __future__ import annotations

from collections import OrderedDict

from src.theme import INSTITUTIONAL_COLORS


DEFAULT_STYLE = {
    "paper_bg": "#2a2a27",
    "plot_bg": "#2a2a27",
    "text_color": "#f3f0e8",
    "grid_color": "#3d3d38",
}

EQUI_DEFAULT_STYLE = {
    "paper_bg": INSTITUTIONAL_COLORS["white"],
    "plot_bg": INSTITUTIONAL_COLORS["white"],
    "text_color": INSTITUTIONAL_COLORS["primary"],
    "grid_color": INSTITUTIONAL_COLORS["light_gray_blue"],
}


def get_available_palettes() -> OrderedDict[str, list[str]]:
    palettes = OrderedDict(
        [
            (
                "Paleta Equi",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                    INSTITUTIONAL_COLORS["turquoise"],
                    INSTITUTIONAL_COLORS["salmon"],
                    INSTITUTIONAL_COLORS["yellow"],
                    INSTITUTIONAL_COLORS["gray_blue"],
                    INSTITUTIONAL_COLORS["light_gray_blue"],
                    INSTITUTIONAL_COLORS["beige"],
                ],
            ),
            (
                "Paleta Equi 1",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                    INSTITUTIONAL_COLORS["turquoise"],
                    INSTITUTIONAL_COLORS["salmon"],
                    INSTITUTIONAL_COLORS["yellow"],
                ],
            ),
            (
                "Paleta Equi 2",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                    INSTITUTIONAL_COLORS["gray_blue"],
                    INSTITUTIONAL_COLORS["light_gray_blue"],
                    INSTITUTIONAL_COLORS["turquoise"],
                ],
            ),
            (
                "Paleta Equi 3",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["salmon"],
                    INSTITUTIONAL_COLORS["yellow"],
                    INSTITUTIONAL_COLORS["beige"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                ],
            ),
            (
                "Paleta Equi 4",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["night_blue"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                    INSTITUTIONAL_COLORS["gray_blue"],
                    INSTITUTIONAL_COLORS["turquoise"],
                ],
            ),
            (
                "Paleta Equi 5",
                [
                    INSTITUTIONAL_COLORS["primary"],
                    INSTITUTIONAL_COLORS["secondary_blue"],
                    INSTITUTIONAL_COLORS["salmon"],
                    INSTITUTIONAL_COLORS["turquoise"],
                    INSTITUTIONAL_COLORS["yellow"],
                    INSTITUTIONAL_COLORS["night_blue"],
                    INSTITUTIONAL_COLORS["gray_blue"],
                    INSTITUTIONAL_COLORS["light_gray_blue"],
                ],
            ),
            (
                "Violeta + menta",
                [
                    "#7468e8",
                    "#8be0c8",
                    "#f7d06b",
                    "#ff7b7b",
                    "#7ab8ff",
                    "#d89cff",
                    "#78d36f",
                    "#f59fc2",
                ],
            ),
            (
                "Plotly",
                [
                    "#636efa",
                    "#ef553b",
                    "#00cc96",
                    "#ab63fa",
                    "#ffa15a",
                    "#19d3f3",
                    "#ff6692",
                    "#b6e880",
                ],
            ),
            (
                "Alto contraste",
                [
                    "#00d2ff",
                    "#ffcc00",
                    "#ff4f81",
                    "#00e676",
                    "#b388ff",
                    "#ff9100",
                    "#40c4ff",
                    "#eeff41",
                ],
            ),
            (
                "Sobrio",
                [
                    "#5b8def",
                    "#60d394",
                    "#f5b841",
                    "#e56b6f",
                    "#8d99ae",
                    "#b56576",
                    "#2ec4b6",
                    "#c77dff",
                ],
            ),
        ]
    )
    return palettes


def get_palette_colors(palette_name: str) -> list[str]:
    return get_available_palettes()[palette_name]


def is_equi_palette(palette_name: str) -> bool:
    return palette_name.startswith("Paleta Equi")


def get_default_style_for_palette(palette_name: str) -> dict[str, str]:
    if is_equi_palette(palette_name):
        return dict(EQUI_DEFAULT_STYLE)
    return dict(DEFAULT_STYLE)
