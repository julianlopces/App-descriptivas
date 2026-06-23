# Estado actual de QuanTi Stats

Ultima revision local: rama `main`, sincronizada con `origin/main`.

Repositorio GitHub: `https://github.com/julianlopces/App-descriptivas`

La app esta desarrollada en Python con Streamlit y gestionada con `uv`. Su objetivo es cargar bases tabulares, revisar la estructura de variables, producir descriptivas, generar tablas cruzadas y construir graficos exportables para informes.

## Resumen funcional

QuanTi Stats permite:

- Cargar archivos `CSV`, `XLSX` y `XLS`.
- Seleccionar hoja de Excel o ajustar codificacion/separador para CSV.
- Normalizar nombres de columnas y eliminar columnas completamente vacias.
- Definir valores personalizados como missing, ademas de los perdidos nativos.
- Detectar variables continuas y categoricas automaticamente.
- Ajustar manualmente la clasificacion de variables.
- Ver una vista previa del dataset cargado.
- Generar tablas descriptivas para variables continuas y categoricas.
- Generar tablas cruzadas masivas o manuales y exportarlas a Excel.
- Crear graficos de barras, histogramas, dispersion y pie/dona.
- Personalizar titulos, leyendas, ejes, rangos, colores, fuentes, fondos y grilla.
- Exportar tablas a CSV/XLSX y graficos a PNG.
- Usar paletas institucionales de Equilibrium, incluyendo `Paleta Equi`.

## Flujo principal de la app

1. **Pantalla inicial**
   - Muestra una landing institucional azul.
   - Permite subir una base.
   - Muestra una tarjeta de carga cuando se presiona `Cargar dataset`.
   - Lee el archivo, normaliza columnas, aplica missings personalizados y detecta tipos de variables.

2. **Sidebar**
   - Muestra logo de Equilibrium, nombre de la app y dataset actual.
   - Permite cargar un nuevo archivo.
   - Incluye `Ajustes de lectura`:
     - `Ajustar tipos`: clasificacion manual de variables continuas/categoricas.
     - `Control de missing`: valores adicionales que deben tratarse como datos perdidos.

3. **Metricas superiores**
   - Muestran `N total` y numero de variables.
   - Usan tarjetas azules institucionales.

4. **Modulos horizontales**
   - `Instrucciones`
   - `Vista previa`
   - `Graficos`
   - `Tablas cruzadas`
   - `Continuas`
   - `Categoricas`
   - `Informe IA`

## Modulos de la interfaz

### Instrucciones

Explica visualmente que hace cada modulo de la app y sugiere un flujo de uso:

1. Cargar la base.
2. Revisar clasificacion de variables.
3. Usar vista previa.
4. Generar graficos, tablas cruzadas o descriptivas.
5. Exportar desde cada modulo.

### Vista previa

Muestra las primeras filas del dataset cargado para revisar:

- nombres de columnas;
- estructura general;
- valores visibles;
- consistencia inicial de la carga.

### Graficos

Modulo de visualizacion exploratoria con panel de configuracion y vista previa fija.

Tipos disponibles:

- **Barras**
  - Variable de conteo/principal.
  - Variable para desagregar/color.
  - Tercera variable/panel.
  - Barras apiladas o agrupadas.
  - Frecuencias o porcentajes.
  - Etiquetas visibles en barras.
  - Decimales configurables.

- **Histograma**
  - Variable continua.
  - Agrupacion/color opcional.
  - Numero de bins.

- **Grafico de pie/dona**
  - Variable de proporcion.
  - Variable opcional para comparar en paneles.
  - Forma `Dona` o `Pie`.
  - Porcentajes por defecto.
  - Decimales de porcentaje configurables.

- **Grafico de dispersion**
  - Variable X continua.
  - Variable Y continua.
  - Color opcional.
  - Linea de ajuste OLS opcional.
  - Ajuste general o por subgrupos.

Opciones generales:

- filtro `Excluir datos perdidos`, activo por defecto;
- titulos y alineacion;
- etiquetas de ejes;
- titulo de leyenda;
- rangos personalizados de ejes;
- paletas institucionales y otras paletas;
- fuente, tamano, color de texto, fondos y grilla;
- exportacion PNG.

### Tablas cruzadas

Genera tablas de contingencia orientadas a informes.

Modo automatico:

- selecciona varias variables principales;
- selecciona varias variables de desagregacion;
- genera todas las combinaciones;
- exporta un Excel con las tablas agrupadas en una misma hoja.

Modo manual:

- permite agregar tablas una por una;
- cada tabla usa una variable para filas y una para columnas;
- cada tabla puede tener titulo personalizado;
- cada tabla puede usar tipo y decimales propios, o heredar configuracion global;
- exporta todas las tablas manuales a un solo Excel.

Tipos de tabla:

- frecuencia absoluta;
- porcentaje por fila;
- porcentaje por columna.

### Continuas

Genera estadisticas descriptivas para variables numericas:

- conteo de valores validos;
- valores perdidos;
- media;
- mediana;
- desviacion estandar;
- minimo;
- maximo;
- percentiles.

Incluye:

- filtro para seleccionar variables visibles;
- formato de tabla institucional;
- control global de decimales;
- descarga CSV y XLSX.

### Categoricas

Genera tablas de frecuencias para variables categoricas:

- frecuencia absoluta;
- porcentaje;
- valores perdidos;
- limite de categorias visibles.

Incluye:

- filtro para seleccionar variables visibles;
- formato de tabla institucional;
- control global de decimales;
- descarga CSV y XLSX.

### Informe IA

Genera un borrador de reporte descriptivo con modelos Gemini a partir de las tablas que la app ya calcula (no envia la base cruda). Flujo:

1. Ingresar la API key de Gemini (campo de texto tipo password, solo en memoria de la sesion) y elegir modelo (los dos mas economicos: `gemini-2.5-flash-lite` y `gemini-3.1-flash-lite`).
2. Subir opcionalmente un diccionario: si es un formulario ODK usa la hoja `survey` con columna `name` (nombre) y `label`/`label::idioma` (descripcion); si la estructura es distinta, pide elegir manualmente las columnas de nombre y descripcion.
3. Seleccionar las variables continuas, categoricas y, opcionalmente, las tablas cruzadas (principales x desagregacion y tipo) que veran como contexto.
4. Escribir un prompt con el contexto del proyecto/encuesta y el enfoque deseado. Si queda vacio, se usa un prompt generico de EDA y relaciones entre variables.

Devuelve el reporte en Markdown, lo muestra en pantalla y permite descargarlo como `.md`. La logica vive en `src/ai_report.py`; requiere la dependencia `google-genai`.

## Estructura del repo

```text
App descriptivas/
  app.py
  main.py
  pyproject.toml
  uv.lock
  packages.txt
  README.md
  CONTEXTO_PROYECTO.txt
  ESTADO_ACTUAL_APP.md
  .python-version
  .gitignore
  .streamlit/
    config.toml
  .devcontainer/
    devcontainer.json
  media/
    Equilibrium-Logo-Blanco.png
    Equilibrium-Logo-Completo-Azul.png
  src/
    __init__.py
    crosstabs.py
    data_loader.py
    descriptive_stats.py
    palettes.py
    plots.py
    theme.py
    utils.py
```

## Archivos principales

### `app.py`

Archivo principal de Streamlit. Orquesta la aplicacion completa:

- configuracion de pagina;
- estado de sesion;
- landing inicial;
- sidebar;
- carga de datos;
- ajustes de tipos y missings;
- metricas superiores;
- navegacion por modulos;
- render de tablas;
- render de graficos;
- descarga de salidas.

Funciones destacadas:

- `init_state()`: inicializa el estado de Streamlit.
- `render_landing_page()`: pantalla inicial antes de cargar dataset.
- `load_controls()`: sidebar para dataset, carga y ajustes.
- `process_uploaded_dataset()`: procesa archivo subido.
- `variable_controls()`: ajustes de tipos y missings.
- `overview_metrics()`: tarjetas superiores.
- `continuous_tab()`: descriptivas continuas.
- `categorical_tab()`: descriptivas categoricas.
- `mass_crosstab_tab()`: tablas cruzadas automaticas/manuales.
- `charts_tab()`: graficos y exportacion PNG.
- `instructions_tab()`: modulo de instrucciones.
- `preview_tab()`: vista previa del dataset.
- `main()`: flujo principal de la app.

### `main.py`

Punto de entrada minimo que importa y ejecuta `main()` desde `app.py`.

### `pyproject.toml`

Define el proyecto Python y sus dependencias. El proyecto se gestiona con `uv`.

Dependencias principales:

- `streamlit`
- `pandas`
- `plotly`
- `kaleido`
- `openpyxl`
- `xlrd`
- `xlsxwriter`
- `statsmodels`
- `websockets`

### `uv.lock`

Lockfile de `uv`. Fija versiones exactas para reproducir el entorno.

### `packages.txt`

Archivo usado para dependencias de sistema en despliegues como Streamlit Community Cloud. Actualmente incluye `chromium`.

### `.streamlit/config.toml`

Tema base de Streamlit con colores institucionales:

- `primaryColor = "#020F50"`
- `backgroundColor = "#F7FAF2"`
- `secondaryBackgroundColor = "#FFFFFF"`
- `textColor = "#020F50"`

### `.devcontainer/devcontainer.json`

Configuracion para abrir el proyecto en un contenedor de desarrollo.

### `media/`

Contiene logos institucionales:

- `Equilibrium-Logo-Blanco.png`: usado sobre fondos oscuros, como landing y sidebar.
- `Equilibrium-Logo-Completo-Azul.png`: usado sobre fondos claros.

## Modulos en `src/`

### `src/data_loader.py`

Funciones de carga y limpieza inicial:

- lee bytes del archivo subido;
- lista hojas de Excel;
- carga CSV, XLSX y XLS;
- normaliza nombres de columnas;
- interpreta valores personalizados como missing.

Funciones:

- `_read_bytes()`
- `get_excel_sheets()`
- `load_uploaded_file()`
- `normalize_columns()`
- `parse_custom_missing_values()`
- `apply_custom_missing_values()`

### `src/descriptive_stats.py`

Funciones estadisticas:

- deteccion de variables continuas/categoricas;
- descriptivas continuas;
- frecuencias categoricas;
- tablas de contingencia simples.

Funciones:

- `_coerce_numeric()`
- `detect_variable_types()`
- `continuous_summary()`
- `categorical_summary()`
- `contingency_table()`

### `src/crosstabs.py`

Funciones para tablas cruzadas y exportacion Excel:

- genera cruces entre variables;
- calcula frecuencias y porcentajes;
- formatea porcentajes;
- limpia nombres de hojas;
- construye Excel en memoria.

Funciones:

- `iter_crosstab_tables()`
- `compute_crosstab()`
- `format_crosstab_for_display()`
- `sanitize_excel_sheet_name()`
- `build_crosstab_excel()`
- `build_selected_crosstab_excel()`

Nota: algunas funciones equivalentes tambien existen en `app.py` para mantener compatibilidad con Streamlit Cloud ante problemas previos de importacion.

### `src/plots.py`

Funciones para graficos Plotly y exportacion PNG:

- histogramas;
- barras;
- pie/dona;
- dispersion;
- exportacion PNG con navegador/headless cuando es posible;
- fallback con Kaleido.

Funciones:

- `histogram()`
- `bar_chart()`
- `pie_chart()`
- `scatter_plot()`
- `to_png_bytes()`
- helpers internos para navegador y captura.

Caracteristicas actuales:

- respeta paleta institucional;
- respeta fuente Geologica en exportacion;
- permite excluir datos perdidos;
- mantiene decimales configurados en etiquetas;
- permite lineas de ajuste OLS en dispersion.

### `src/palettes.py`

Centraliza paletas de colores.

Incluye:

- `Paleta Equi`
- `Paleta Equi 1`
- `Paleta Equi 2`
- `Paleta Equi 3`
- `Paleta Equi 4`
- `Paleta Equi 5`
- paletas adicionales existentes.

Funciones:

- `get_available_palettes()`
- `get_palette_colors()`
- `is_equi_palette()`
- `get_default_style_for_palette()`

### `src/theme.py`

Centraliza colores institucionales y CSS de la interfaz.

Incluye:

- colores Equilibrium;
- funciones de contraste;
- CSS para sidebar, botones, tarjetas, inputs, tablas y controles.

Funciones:

- `relative_luminance()`
- `contrast_ratio()`
- `pick_text_color()`
- `get_institutional_css()`

### `src/ai_report.py`

Logica de generacion de reportes con Gemini:

- detecta y parsea el diccionario/ODK;
- construye el mapa nombre de variable -> descripcion;
- serializa descriptivas y tablas cruzadas a Markdown compacto;
- arma el prompt (rol + contexto + diccionario + datos + tarea);
- llama al modelo y devuelve el texto.

Funciones:

- `inspect_dictionary_file()`
- `build_variable_descriptions()`
- `build_data_context()`
- `build_prompt()`
- `generate_report()`

Constantes: `AVAILABLE_MODELS`, `GENERIC_PROMPT`, `SYSTEM_INSTRUCTION`.

### `src/utils.py`

Funciones de exportacion de tablas:

- DataFrame a CSV;
- DataFrame a Excel;
- varias tablas a Excel.

Funciones:

- `dataframe_to_csv_bytes()`
- `dataframe_to_excel_bytes()`
- `tables_to_excel_bytes()`

## Gestion del entorno

El proyecto usa `uv`.

Comandos principales:

```powershell
uv sync
uv run streamlit run app.py
uv run python -m py_compile app.py
$files = Get-ChildItem -Path src -Filter *.py | ForEach-Object { $_.FullName }
uv run python -m py_compile @files
```

En este equipo se ha usado tambien:

```powershell
uv --cache-dir .uv-cache run streamlit run app.py
```

Esto evita problemas del cache global de `uv` en Windows.

## Estado Git y despliegue

- Rama principal: `main`.
- Remoto: `origin`.
- Repo GitHub: `https://github.com/julianlopces/App-descriptivas`.
- La app esta preparada para Streamlit Community Cloud.
- El despliegue usa el repo de GitHub y el archivo principal `app.py`.
- `packages.txt` incluye `chromium` para apoyar exportaciones PNG con navegador en entornos cloud.

## Riesgos o puntos a vigilar

- La exportacion PNG depende de que el entorno tenga navegador disponible o que Kaleido funcione correctamente.
- Hay duplicacion intencional de algunas funciones de tablas cruzadas entre `app.py` y `src/crosstabs.py` por compatibilidad con Streamlit Cloud.
- El CSS personalizado depende de selectores internos de Streamlit; futuras versiones de Streamlit podrian requerir ajustes visuales.
- Las bases cargadas en Streamlit Cloud se procesan en memoria durante la sesion de usuario; no se guardan intencionalmente en disco por la app.
