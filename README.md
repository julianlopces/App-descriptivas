# App descriptivas

Aplicacion en Python con Streamlit para cargar bases tabulares y generar estadisticas descriptivas, tablas de contingencia y visualizaciones exploratorias.

## Funcionalidades

- Carga de archivos CSV, XLSX y XLS.
- Seleccion de hoja para archivos Excel.
- Vista previa, dimensiones y conteo global de valores perdidos.
- Deteccion automatica de variables continuas y categoricas.
- Ajuste manual de la clasificacion de variables.
- Seleccion de outcomes, variables demograficas y variables adicionales.
- Estadisticas descriptivas para variables continuas y categoricas.
- Tablas cruzadas con frecuencias absolutas o porcentajes por fila, columna o total.
- Histogramas, barras y dispersion con opciones basicas de personalizacion.
- Descarga de tablas en CSV y Excel.
- Descarga de graficos en PNG cuando Plotly y Kaleido pueden exportar imagenes en el entorno.

## Instalacion y sincronizacion

Este proyecto usa `uv` como gestor del entorno y dependencias.

```powershell
cd "C:\Users\julia\Documents\Codex Projects\App descriptivas"
uv sync
```

Si no existe entorno virtual:

```powershell
uv venv
uv sync
```

## Ejecucion

```powershell
uv run streamlit run app.py
```

## Validaciones utiles

```powershell
uv run python -m py_compile app.py
uv run python -m py_compile src/*.py
```

## Limitaciones

- La exportacion PNG depende de Kaleido y de los componentes que este necesite en el sistema.
- Las variables numericas cargadas como texto se intentan convertir automaticamente cuando al menos 90% de los valores no perdidos son convertibles.
- Las variables categoricas con muchos niveles se resumen mostrando un maximo configurable y agrupando el resto como `(Otras categorias)`.
