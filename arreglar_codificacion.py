"""Repara acentos doble-codificados (mojibake) en archivos del proyecto.

Algunos archivos quedaron guardados con los acentos doble-codificados: una vocal
con tilde aparece como dos caracteres extranos (por ejemplo se ve "Conexi" seguido
de simbolos raros en lugar de "Conexion" con tilde). Esto ocurre cuando texto
UTF-8 se interpreta como Latin-1 y se vuelve a guardar como UTF-8.

Este script reescribe en UTF-8 limpio cualquier archivo .py o .md que tenga esas
secuencias. Es seguro: la correccion se hace linea por linea y solo se aplica a las
lineas que realmente estan doble-codificadas; las lineas correctas no se tocan.

No contiene ningun caracter no-ASCII: la correccion es algoritmica (relacion
Latin-1 / UTF-8), no una tabla de reemplazos. Asi este script no puede corromperse.

Uso (desde la raiz del proyecto):

    uv run python arreglar_codificacion.py
"""

from __future__ import annotations

import pathlib

EXTENSIONS = (".py", ".md")
IGNORE_DIRS = {".venv", "__pycache__", ".git", ".uv-cache"}


def _fix_line(line: str) -> str:
    """Si la linea esta doble-codificada, la corrige; si no, la deja igual.

    Texto doble-codificado = UTF-8 valido que fue interpretado como Latin-1.
    Para revertirlo se vuelve a bytes con Latin-1 y se decodifica como UTF-8.
    Una linea ya correcta (con tildes UTF-8 reales) falla esa conversion y se
    devuelve intacta, por lo que el proceso es seguro.
    """
    try:
        candidate = line.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return line
    return candidate


def fix_text(text: str) -> str:
    return "".join(_fix_line(line) for line in text.splitlines(keepends=True))


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    this_file = pathlib.Path(__file__).name
    changed: list[str] = []

    for path in root.rglob("*"):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.name == this_file:
            continue  # no tocar este mismo script

        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        fixed = fix_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            changed.append(str(path.relative_to(root)))

    if changed:
        print("Archivos corregidos:")
        for name in changed:
            print("  -", name)
    else:
        print("No se encontraron secuencias mojibake. Nada que corregir.")


if __name__ == "__main__":
    main()
