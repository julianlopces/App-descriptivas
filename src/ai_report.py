"""Generacion de reportes preliminares de EDA con modelos Gemini.

Este modulo concentra toda la logica de IA: lectura del diccionario/ODK,
serializacion de tablas ya calculadas por la app, construccion del prompt y
llamada al modelo. La interfaz vive en app.py (pestana "Informe IA").

Decision de diseno clave: la IA NO recibe la base cruda, solo recibe las
descriptivas y tablas cruzadas que la app ya calcula. Es mas barato, mas
preciso y mas seguro para datos de encuesta.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd


# Modelos disponibles: solo los dos mas economicos recomendados.
# El nombre visible apunta al "model string" que entiende la API de Gemini.
AVAILABLE_MODELS: dict[str, str] = {
    "Gemini 2.5 Flash-Lite (mas economico)": "gemini-2.5-flash-lite",
    "Gemini 3.1 Flash-Lite": "gemini-3.1-flash-lite",
}


# Instruccion base que gobierna todo el reporte. El contexto del proyecto y las
# variables socioeconomicas son insumos obligatorios que se anexan en build_prompt.
SYSTEM_INSTRUCTION = """Actúa como un/a analista cuantitativo/a senior especializado/a en análisis exploratorio de datos de encuesta, monitoreo, evaluación y generación de reportes descriptivos.
Vas a elaborar un borrador de informe en español a partir de información agregada ya calculada por la aplicación. No recibirás la base de datos cruda. Tus únicos insumos serán:

1. El contexto del proyecto, encuesta o estudio aportado por el usuario.
2. Un diccionario de variables, si está disponible.
3. Tablas descriptivas de variables continuas.
4. Tablas de frecuencias de variables categóricas.
5. Tablas cruzadas o cruces entre variables seleccionadas.
Tu tarea es producir un informe preliminar de análisis exploratorio de datos —EDA— y de relaciones entre variables, usando únicamente las cifras provistas. No inventes datos, no supongas valores no observados y no afirmes resultados que no estén respaldados por las tablas. Si algo no puede concluirse con la información disponible, indícalo explícitamente.
Usa el contexto del usuario para orientar el análisis. Prioriza las variables, grupos, resultados, dimensiones o hipótesis que el usuario mencione. Si el contexto identifica una población objetivo, intervención, territorio, línea base, seguimiento, diagnóstico, evaluación, encuesta de percepción o encuesta de caracterización, adapta la interpretación a ese propósito. Si el contexto es breve o ambiguo, realiza un EDA general y señala qué información adicional ayudaría a enriquecer el análisis.
Al interpretar las variables:

* Usa las etiquetas del diccionario para hacer el reporte más claro.
* Si una variable no tiene etiqueta o descripción, usa su nombre técnico con cautela.
* No cambies el significado de las variables.
* Si una variable parece ser de identificación, fecha, enumerador, control operativo o metadato, no la trates como una variable sustantiva salvo que el contexto lo justifique.
* Si hay categorías como "No sabe", "No responde", "Otro", "Prefiere no responder", "NA" o valores perdidos, coméntalas cuando sean relevantes para la calidad del dato o la interpretación.
Para el análisis descriptivo:

* Resume la composición general de la muestra cuando haya variables sociodemográficas o de caracterización.
* Identifica patrones importantes en variables categóricas: categorías dominantes, categorías minoritarias, concentración de respuestas y posibles señales de heterogeneidad.
* Para variables continuas, comenta medias, medianas, dispersión, mínimos, máximos y posibles valores atípicos solo si esas estadísticas están disponibles.
* Señala posibles problemas de calidad de datos: alta no respuesta, categorías ambiguas, distribuciones muy concentradas, valores extremos, tamaños de celda pequeños o inconsistencias aparentes.
* No exageres hallazgos menores. Prioriza los patrones con mayor relevancia sustantiva.
Para el análisis de relaciones entre variables:

* Analiza las tablas cruzadas disponibles buscando diferencias relevantes entre grupos, asociaciones descriptivas y patrones de segmentación.
* Prioriza cruces entre variables de resultado o interés principal y variables explicativas o de segmentación como sexo, edad, territorio, zona, nivel educativo, condición socioeconómica, grupo de intervención, exposición al programa u otras variables relevantes según el contexto.
* Describe diferencias en porcentajes, medias o distribuciones cuando estén disponibles.
* Usa lenguaje descriptivo: "se observa", "la proporción es mayor", "parece haber una diferencia", "los datos sugieren una asociación descriptiva".
* No hagas afirmaciones causales. No digas que una variable "causa", "explica" o "produce" otra, a menos que el usuario haya indicado explícitamente que el diseño permite inferencia causal y las tablas entregadas sean suficientes para sostenerlo.
* No reportes significancia estadística, p-valores, intervalos de confianza o efectos si no están incluidos en las tablas.
* Cuando los tamaños de celda sean pequeños o no estén disponibles, advierte que la interpretación de los cruces debe hacerse con cautela.
* Si algunas relaciones parecen importantes pero no están cruzadas en las tablas, sugiere analizarlas en próximos pasos.
El informe debe estar escrito en Markdown, con tono profesional, claro y útil para un equipo técnico o de proyecto. Evita lenguaje excesivamente académico, pero mantén rigor analítico.
Estructura el reporte así:
Informe preliminar de análisis descriptivo
1. Resumen ejecutivo
Presenta entre 4 y 6 hallazgos principales. Deben ser concretos, basados en cifras y conectados con el contexto del usuario. Incluye también una advertencia breve de que el reporte se basa en tablas agregadas y debe ser revisado antes de usarse.
2. Contexto del análisis
Resume brevemente el objetivo del estudio o encuesta según el contexto aportado por el usuario. Si el contexto es insuficiente, dilo de forma explícita y explica cómo eso limita la interpretación.
3. Composición de la muestra
Describe las características principales de la muestra usando las variables disponibles. Incluye tamaño de muestra si está disponible. Comenta distribución por grupos relevantes como sexo, edad, territorio, zona, cohorte, sede, institución, tratamiento, exposición u otros segmentos disponibles.
4. Hallazgos descriptivos por variable o dimensión
Organiza los hallazgos por temas o dimensiones, no necesariamente variable por variable. Agrupa variables relacionadas cuando sea posible. Para cada dimensión, resume los patrones más relevantes y menciona cifras concretas.
5. Relaciones entre variables
Analiza los cruces disponibles. Identifica diferencias entre grupos, asociaciones descriptivas y patrones que complementen el EDA. Para cada relación importante, menciona:

* Variables cruzadas.
* Patrón observado.
* Magnitud aproximada de la diferencia, si se puede derivar de la tabla.
* Interpretación sustantiva.
* Precauciones de lectura.
6. Calidad de los datos y limitaciones
Comenta posibles limitaciones del análisis: datos agregados, ausencia de base cruda, no respuesta, variables sin diccionario, cruces insuficientes, tamaños de celda pequeños, ausencia de pruebas estadísticas, imposibilidad de inferencia causal o cualquier otra restricción visible en las tablas.
7. Próximos pasos sugeridos
Propón análisis complementarios útiles, priorizados según el contexto del usuario. Puedes sugerir nuevos cruces, segmentaciones, visualizaciones, limpieza de variables, análisis de no respuesta, modelos estadísticos, pruebas de balance, análisis de heterogeneidad o validaciones adicionales, pero solo como recomendaciones futuras.
Reglas finales:

* Basa todo el reporte únicamente en las cifras provistas.
* No inventes datos, porcentajes, tamaños de muestra ni conclusiones.
* No uses conocimiento externo salvo para interpretar de forma general el tipo de análisis.
* No incluyas código.
* No incluyas fórmulas innecesarias.
* No muestres razonamiento paso a paso interno.
* Sé claro cuando una interpretación sea tentativa.
* El resultado debe ser un borrador revisable, no un informe final definitivo."""


# ---------------------------------------------------------------------------
# Lectura del diccionario / formulario ODK
# ---------------------------------------------------------------------------

def _read_uploaded_bytes(uploaded_file: Any) -> bytes:
    uploaded_file.seek(0)
    return uploaded_file.read()


def _find_label_column(columns: list[Any]) -> str | None:
    """Busca la columna de etiqueta. En ODK puede ser 'label' o 'label::Espanol (es)'."""
    lowered = {str(col).lower(): col for col in columns}
    if "label" in lowered:
        return lowered["label"]
    for col in columns:
        if str(col).lower().startswith("label"):
            return col
    return None


def _odk_mapping(survey: pd.DataFrame) -> tuple[Any, Any] | None:
    """Devuelve (columna_nombre, columna_etiqueta) si la hoja survey tiene estructura ODK."""
    lowered = {str(col).lower(): col for col in survey.columns}
    name_col = lowered.get("name")
    label_col = _find_label_column(list(survey.columns))
    if name_col is not None and label_col is not None:
        return name_col, label_col
    return None


def _inspect_generic_df(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "kind": "generic",
        "df": df,
        "columns": [str(col) for col in df.columns],
        "name_col": None,
        "label_col": None,
    }


def inspect_dictionary_file(uploaded_file: Any) -> dict[str, Any]:
    """Lee el archivo de diccionario y detecta si es ODK o un diccionario generico.

    Retorna un dict con:
      - kind: "odk" | "generic"
      - df: DataFrame del diccionario (hoja survey para ODK)
      - columns: lista de columnas disponibles
      - name_col / label_col: columnas detectadas (solo en ODK; None en generico)
    """
    name = str(uploaded_file.name).lower()
    data = _read_uploaded_bytes(uploaded_file)
    if not data:
        raise ValueError("El archivo de diccionario esta vacio.")

    if name.endswith(".csv"):
        df = pd.read_csv(BytesIO(data), sep=None, engine="python")
        return _inspect_generic_df(df)

    if name.endswith((".xlsx", ".xls")):
        engine = "xlrd" if name.endswith(".xls") else "openpyxl"
        excel = pd.ExcelFile(BytesIO(data), engine=engine)
        sheets_lower = {str(sheet).lower(): sheet for sheet in excel.sheet_names}

        # Estructura ODK: hoja "survey" con columnas name/label.
        if "survey" in sheets_lower:
            survey = excel.parse(sheets_lower["survey"])
            mapping = _odk_mapping(survey)
            if mapping is not None:
                name_col, label_col = mapping
                return {
                    "kind": "odk",
                    "df": survey,
                    "columns": [str(col) for col in survey.columns],
                    "name_col": name_col,
                    "label_col": label_col,
                }
            # Hay hoja survey pero sin name/label -> tratar como generico.
            return _inspect_generic_df(survey)

        # Sin hoja survey: usar la primera hoja como diccionario generico.
        first = excel.parse(excel.sheet_names[0])
        return _inspect_generic_df(first)

    raise ValueError("Formato de diccionario no soportado. Usa CSV, XLSX o XLS.")


def build_variable_descriptions(
    dictionary_df: pd.DataFrame,
    name_col: Any,
    label_col: Any,
) -> dict[str, str]:
    """Construye el mapa nombre_variable -> descripcion a partir del diccionario."""
    descriptions: dict[str, str] = {}
    if dictionary_df is None or name_col is None or label_col is None:
        return descriptions
    if name_col not in dictionary_df.columns or label_col not in dictionary_df.columns:
        return descriptions

    for _, row in dictionary_df.iterrows():
        variable = row[name_col]
        label = row[label_col]
        if pd.isna(variable) or pd.isna(label):
            continue
        variable_text = str(variable).strip()
        label_text = str(label).strip()
        if variable_text and label_text:
            descriptions.setdefault(variable_text, label_text)
    return descriptions


# ---------------------------------------------------------------------------
# Serializacion de tablas a texto compacto (Markdown) para el prompt
# ---------------------------------------------------------------------------

def _format_cell(value: object, max_decimals: int) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        rounded = round(value, max_decimals)
        if float(rounded).is_integer():
            return str(int(rounded))
        return f"{rounded:.{max_decimals}f}".rstrip("0").rstrip(".")
    return str(value)


def _df_to_markdown(df: pd.DataFrame, *, index: bool, max_decimals: int) -> str:
    """Convierte un DataFrame a tabla Markdown sin depender de 'tabulate'."""
    if df is None or df.empty:
        return "(sin datos)"

    table = df.reset_index() if index else df.copy()
    headers = [str(col) for col in table.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in table.iterrows():
        cells = [_format_cell(value, max_decimals) for value in row.values]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _descriptions_to_markdown(descriptions: dict[str, str]) -> str:
    if not descriptions:
        return "(no se proporciono diccionario de variables)"
    lines = ["| Variable | Descripcion |", "| --- | --- |"]
    for variable, label in descriptions.items():
        safe_label = label.replace("|", "/").replace("\n", " ")
        lines.append(f"| {variable} | {safe_label} |")
    return "\n".join(lines)


def build_data_context(
    continuous_table: pd.DataFrame,
    categorical_table: pd.DataFrame,
    crosstabs: list[tuple[str, str, pd.DataFrame]],
    table_type_label: str,
    *,
    max_decimals: int = 2,
) -> str:
    """Arma el bloque de datos que vera la IA a partir de las tablas calculadas."""
    parts: list[str] = []

    if continuous_table is not None and not continuous_table.empty:
        parts.append(
            "### Descriptivas de variables continuas\n"
            + _df_to_markdown(continuous_table, index=False, max_decimals=max_decimals)
        )
    else:
        parts.append("### Descriptivas de variables continuas\n(no se incluyeron variables continuas)")

    if categorical_table is not None and not categorical_table.empty:
        parts.append(
            "### Frecuencias de variables categoricas\n"
            + _df_to_markdown(categorical_table, index=False, max_decimals=max_decimals)
        )
    else:
        parts.append("### Frecuencias de variables categoricas\n(no se incluyeron variables categoricas)")

    if crosstabs:
        cross_parts: list[str] = []
        for main_var, disagg_var, table in crosstabs:
            cross_parts.append(
                f"#### {main_var} x {disagg_var} ({table_type_label})\n"
                + _df_to_markdown(table, index=True, max_decimals=max_decimals)
            )
        parts.append("### Tablas cruzadas\n" + "\n\n".join(cross_parts))
    else:
        parts.append("### Tablas cruzadas\n(no se incluyeron tablas cruzadas)")

    return "\n\n".join(parts)


def build_prompt(
    data_context: str,
    variable_descriptions: dict[str, str],
    user_context: str,
    *,
    dataset_name: str,
    n_rows: int,
    n_vars: int,
    socioeconomic_vars: list[str],
) -> str:
    """Construye el prompt final: instruccion base + insumos (contexto, diccionario, datos).

    El contexto del proyecto y las variables socioeconomicas son obligatorios; la
    validacion se hace en la interfaz antes de llamar a esta funcion.
    """
    dictionary_text = _descriptions_to_markdown(variable_descriptions)
    socio_text = ", ".join(socioeconomic_vars) if socioeconomic_vars else "(no se indicaron)"

    return f"""{SYSTEM_INSTRUCTION}

---
# INSUMOS PARA EL INFORME

## 1. Contexto del proyecto, encuesta o estudio (aportado por el usuario)
{user_context.strip()}

## 2. Diccionario de variables
{dictionary_text}

## Informacion del dataset
- Nombre: {dataset_name}
- Numero de registros: {n_rows}
- Numero de variables: {n_vars}

## Variables socioeconomicas / de caracterizacion (obligatorias)
Las siguientes variables fueron marcadas como socioeconomicas o de caracterizacion y DEBEN usarse para describir la composicion de la muestra en la seccion correspondiente: {socio_text}

## 3 a 5. Datos calculados por la aplicacion (unica fuente de cifras permitida)
{data_context}
"""


# ---------------------------------------------------------------------------
# Llamada al modelo
# ---------------------------------------------------------------------------

def generate_report(api_key: str, model: str, prompt: str) -> str:
    """Llama a la API de Gemini y devuelve el texto del reporte.

    Lanza RuntimeError con un mensaje claro si falta la dependencia, si la
    respuesta viene vacia o si la API falla.
    """
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "Falta la dependencia 'google-genai'. Instalala con: uv add google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)

    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise RuntimeError(
            "El modelo no devolvio texto. Revisa la API key, el modelo seleccionado "
            "o los limites de uso de tu cuenta."
        )
    return text


# ---------------------------------------------------------------------------
# Exportacion del reporte a Word (.docx) editable
# ---------------------------------------------------------------------------

def _is_table_separator(cells: list[str]) -> bool:
    """Detecta la fila separadora de una tabla Markdown (|---|---|)."""
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def _add_runs_with_bold(paragraph, text: str) -> None:
    """Agrega texto a un parrafo interpretando **negritas** de Markdown."""
    for part in re.split(r"(\*\*.+?\*\*)", text):
        if len(part) > 4 and part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part:
            paragraph.add_run(part)


def markdown_to_docx_bytes(markdown_text: str) -> bytes:
    """Convierte el reporte en Markdown a un documento Word (.docx) editable.

    Soporta encabezados (#..####), listas con viñetas y numeradas, tablas
    Markdown y negritas en linea. Devuelve los bytes del .docx.
    """
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "Falta la dependencia 'python-docx'. Instalala con: uv add python-docx"
        ) from exc

    document = Document()
    lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    total = len(lines)

    while index < total:
        stripped = lines[index].strip()

        if not stripped:
            index += 1
            continue

        # Bloque de tabla Markdown
        if stripped.startswith("|") and stripped.endswith("|"):
            block: list[list[str]] = []
            while index < total and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                block.append(cells)
                index += 1
            rows = [row for row in block if not _is_table_separator(row)]
            if rows:
                n_cols = max(len(row) for row in rows)
                table = document.add_table(rows=0, cols=n_cols)
                try:
                    table.style = "Light Grid Accent 1"
                except Exception:  # noqa: BLE001 - estilo opcional
                    pass
                for row in rows:
                    cells = table.add_row().cells
                    for col_index in range(n_cols):
                        cells[col_index].text = row[col_index] if col_index < len(row) else ""
            continue

        # Encabezados
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            document.add_heading(stripped[level:].strip(), level=min(max(level, 1), 4))
            index += 1
            continue

        # Listas con viñeta
        if stripped[:2] in ("- ", "* ") or stripped.startswith("• "):
            paragraph = document.add_paragraph(style="List Bullet")
            _add_runs_with_bold(paragraph, stripped[2:].strip())
            index += 1
            continue

        # Listas numeradas
        numbered = re.match(r"^\d+[.)]\s+(.*)", stripped)
        if numbered:
            paragraph = document.add_paragraph(style="List Number")
            _add_runs_with_bold(paragraph, numbered.group(1))
            index += 1
            continue

        # Parrafo normal
        paragraph = document.add_paragraph()
        _add_runs_with_bold(paragraph, stripped)
        index += 1

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
