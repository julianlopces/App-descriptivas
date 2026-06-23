# CLAUDE.md

Guía para agentes de IA (Claude Code y similares) que trabajen en este repositorio. Léela antes de hacer cambios. Para el detalle funcional completo de la interfaz, ver `ESTADO_ACTUAL_APP.md`; este archivo prioriza lo que un agente necesita para desarrollar sin romper nada.

## Qué es

**QuanTi Stats** (nombre interno del proyecto: `app-descriptivas`) es una aplicación web en **Python + Streamlit** para cargar bases tabulares (CSV/XLSX/XLS), clasificar variables, generar estadísticas descriptivas, tablas cruzadas y gráficos exportables para informes. Tiene identidad visual institucional de **Equilibrium**.

- Repo GitHub: `https://github.com/julianlopces/App-descriptivas`
- Rama principal: `main` (remoto `origin`)
- Despliegue: **Streamlit Community Cloud**, archivo principal `app.py`
- Python: `>=3.12` (ver `.python-version` → `3.12`)
- Gestor de entorno y dependencias: **`uv`** (no usar pip/poetry directamente)

## Comandos

Trabajar desde la raíz del proyecto. En este equipo (Windows) conviene usar el cache local para evitar problemas del cache global de `uv`:

```powershell
# Sincronizar entorno
uv sync

# Ejecutar la app (desarrollo)
uv run streamlit run app.py
uv --cache-dir .uv-cache run streamlit run app.py   # variante usada en este equipo

# Validar que compila (NO hay tests automatizados)
uv run python -m py_compile app.py
uv run python -m py_compile src/*.py
```

No existe suite de pruebas ni linter configurado. La verificación mínima antes de commitear es `py_compile` sobre `app.py` y `src/*.py`, e idealmente correr la app y revisar el módulo afectado.

## Arquitectura

Separación deliberada entre **interfaz/flujo** (en `app.py`) y **lógica reutilizable** (en `src/`). Mantener esta separación al extender el proyecto.

```
app.py                  # Punto de entrada real: toda la UI, estado de sesión y orquestación
main.py                 # Stub: solo imprime cómo ejecutar la app. NO es el entry point real
src/
  data_loader.py        # Lectura de archivos, detección de hojas, normalización de columnas, missings
  descriptive_stats.py  # Detección de tipos de variable, descriptivas continuas/categóricas, contingencia
  crosstabs.py          # Tablas cruzadas masivas/manuales y exportación Excel por hojas
  plots.py              # Gráficos Plotly (barras, histograma, pie/dona, dispersión) y export PNG
  palettes.py           # Paletas de color, incluidas las institucionales "Paleta Equi"
  theme.py              # Colores institucionales, lógica de contraste y CSS de la interfaz
  utils.py              # Conversión de DataFrames a CSV/Excel descargable
media/                  # Logos institucionales (azul para fondos claros, blanco para oscuros)
.streamlit/config.toml  # Tema base de Streamlit (colores institucionales)
pyproject.toml / uv.lock# Definición del proyecto y lockfile reproducible
packages.txt            # Paquetes de sistema para Streamlit Cloud (incluye `chromium`)
```

### Flujo de `main()` en `app.py`

1. `inject_styles()` + `init_state()`.
2. Si no hay dataset (`st.session_state.df is None`) → `render_landing_page()` y retorna (landing institucional con carga de archivo).
3. Con dataset cargado: sidebar oscura (`inject_sidebar_dark_css`) con `load_controls()` (carga/relectura) y `variable_controls()` (ajuste de tipos y missings personalizados).
4. `overview_metrics()` muestra N total y número de variables.
5. Seis pestañas horizontales: **Instrucciones, Vista previa, Gráficos, Tablas cruzadas, Continuas, Categóricas**.

### Estado de sesión

El estado vive en `st.session_state`, inicializado en `init_state()`. Claves centrales: `df` (dataset con missings aplicados), `raw_df` (dataset crudo), `custom_missing_values`, y configuración de tipos de variable y estilos de gráficos (claves con prefijos `chart_`, `hist_`, `bar_`, `pie_`, `scatter_`). El `raw_df` se preserva para poder reaplicar missings personalizados sin recargar el archivo.

## Convenciones y detalles importantes

- **Idioma**: todo el código, UI, comentarios y documentación están en **español**. Mantenerlo así. Los acentos suelen omitirse en identificadores y a veces en strings; seguir el estilo del archivo que se edita.
- **Type hints**: el código usa `from __future__ import annotations` y anotaciones modernas (`list[str]`, `dict`, `| None`). Mantener anotaciones en funciones nuevas.
- **Detección de tipos** (`detect_variable_types`): variables tipo texto se intentan convertir a numéricas cuando **≥90%** de los valores no perdidos son convertibles; el usuario puede reclasificar manualmente.
- **Categóricas**: se resumen con un máximo configurable de niveles (por defecto `max_levels=30`), agrupando el resto como `(Otras categorias)`.
- **Duplicación intencional**: algunas funciones de tablas cruzadas y missings existen tanto en `app.py` como en `src/crosstabs.py`/`src/data_loader.py`. Es deliberado, por problemas previos de importación en Streamlit Cloud. Si se modifica la lógica, **revisar ambas copias** para no desincronizarlas.
- **CSS personalizado**: `theme.py` inyecta CSS que depende de selectores internos de Streamlit (`data-testid`, etc.). Actualizaciones de Streamlit pueden romper la apariencia; tratar con cuidado.
- **Colores institucionales** (`.streamlit/config.toml` e `INSTITUTIONAL_COLORS`): primario `#020F50`, fondo `#F7FAF2`, secundario `#FFFFFF`, texto `#020F50`. La fuente preferida en gráficos es **Geologica**.
- **Logos**: se cargan como data-URI base64 desde `media/`. `Equilibrium-Logo-Blanco.png` sobre fondos oscuros (landing/sidebar), `Equilibrium-Logo-Completo-Azul.png` sobre fondos claros.

## Exportaciones

- **Tablas**: CSV y XLSX vía `src/utils.py` (`dataframe_to_csv_bytes`, `dataframe_to_excel_bytes`, `tables_to_excel_bytes`). Las tablas cruzadas masivas exportan un Excel con una hoja por variable principal (`build_crosstab_excel`, `sanitize_excel_sheet_name`).
- **Gráficos PNG**: `src/plots.py` intenta primero render con navegador headless (Chromium vía DevTools) y cae a Kaleido como fallback. **Punto frágil**: depende de que el entorno tenga navegador disponible o Kaleido funcione. Por eso `packages.txt` declara `chromium` para Streamlit Cloud. Si se toca la exportación PNG, probarla explícitamente en local y considerar el entorno cloud.

## Riesgos / puntos a vigilar

- La exportación PNG es la parte más frágil (navegador/Kaleido). Cambios aquí requieren prueba real.
- La duplicación intencional de funciones puede desincronizarse si se edita solo una copia.
- El CSS depende de internals de Streamlit y puede romperse al actualizar la librería.
- Las bases se procesan **en memoria** durante la sesión; la app no persiste datos en disco a propósito. No introducir escritura de datos de usuario sin justificación.
- No hay tests; validar manualmente y con `py_compile`.

## Al extender el proyecto

Mantener la modularidad: UI y flujo en `app.py`; datos/estadísticas en `descriptive_stats.py`; cruces en `crosstabs.py`; gráficos en `plots.py`; estilo en `theme.py`/`palettes.py`; exportaciones en `utils.py`. No romper la experiencia visual ni la estructura de pestañas existente. Tras cambios, actualizar `ESTADO_ACTUAL_APP.md` si cambia la funcionalidad.
