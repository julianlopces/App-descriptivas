# Resultados esperables para validar el Informe IA

Este documento resume los principales resultados que debería detectar el **Informe IA** al analizar la base sintética `base_sintetica_eda_informe_ia.xlsx`, hoja `datos`.

La finalidad no es que el reporte generado por IA coincida palabra por palabra, sino que identifique los patrones descriptivos centrales, use cifras consistentes y mantenga una interpretación prudente. Se recomienda aceptar pequeñas diferencias por redondeo, especialmente de ±0.1 puntos porcentuales o ±0.01 en medias.

## 1. Criterios generales de validación

El informe generado por IA debería:

- Indicar que la base es **sintética** y que el análisis sirve para testear la app.
- Reportar que hay **300 registros**.
- Usar lenguaje descriptivo y no causal.
- No reportar significancia estadística, p-valores, intervalos de confianza ni efectos causales si no están en las tablas.
- Basarse en las tablas agregadas y no inventar cifras.
- Distinguir entre patrones observados y recomendaciones de análisis posterior.
- Mencionar limitaciones por valores faltantes, variables post con más missing y posibles observaciones de calidad.

## 2. Composición esperada de la muestra

### 2.1 Territorio

- `Yolombó`: 115 (38.3%)
- `Villanueva`: 97 (32.3%)
- `San Francisco`: 88 (29.3%)

Resultado esperable: el informe debe identificar que la muestra está distribuida en tres territorios, con mayor número de registros en **Yolombó**, seguido por **Villanueva** y **San Francisco**.

### 2.2 Modalidad

- `remota`: 115 (38.3%)
- `presencial`: 97 (32.3%)
- `hibrida`: 88 (29.3%)

Resultado esperable: la modalidad coincide con el territorio en esta base sintética:

- Yolombó: modalidad remota.
- Villanueva: modalidad presencial.
- San Francisco: modalidad híbrida.

### 2.3 Zona

- `urbana`: 180 (60.0%)
- `rural`: 120 (40.0%)

Resultado esperable: la muestra es mayoritariamente urbana, pero mantiene una proporción rural importante.

### 2.4 Sexo

- `mujer`: 146 (48.7%)
- `hombre`: 142 (47.3%)
- `no_binario`: 6 (2.0%)
- `prefiere_no_responder`: 6 (2.0%)

Resultado esperable: el informe debe señalar una distribución balanceada entre mujeres y hombres, con grupos pequeños de `no_binario` y `prefiere_no_responder`. Debe advertir cautela al interpretar estos grupos por su tamaño pequeño.

### 2.5 Grado

- `8`: 92 (30.7%)
- `11`: 81 (27.0%)
- `10`: 67 (22.3%)
- `9`: 60 (20.0%)

Resultado esperable: la mayor concentración está en grado 8 y grado 11.

### 2.6 Estrato

- `2`: 138 (46.0%)
- `1`: 104 (34.7%)
- `3`: 51 (17.0%)
- `4`: 7 (2.3%)

Resultado esperable: predominan los estratos 1 y 2.

## 3. Variables numéricas principales

| Variable | n válido | Missing | Media | Mediana | Mín. | Máx. |
|---|---:|---:|---:|---:|---:|---:|
| Edad | 296 | 4 | 15.40 | 15.0 | 12 | 19 |
| Apoyo familiar | 292 | 8 | 3.54 | 4.0 | 1 | 5 |
| Asistencia a sesiones | 297 | 3 | 11.10 | 11.0 | 2 | 16 |
| Satisfacción NPS | 294 | 6 | 8.06 | 8.0 | 2 | 10 |
| Autoeficacia pre | 297 | 3 | 3.09 | 3.0 | 1 | 5 |
| Autoeficacia post | 279 | 21 | 3.48 | 4.0 | 1 | 5 |
| Habilidades digitales pre | 297 | 3 | 2.91 | 3.0 | 1 | 5 |
| Habilidades digitales post | 270 | 30 | 3.61 | 4.0 | 1 | 5 |
| Conocimiento oportunidades pre | 299 | 1 | 2.39 | 2.0 | 1 | 5 |
| Conocimiento oportunidades post | 282 | 18 | 3.20 | 3.0 | 1 | 5 |
| Claridad vocacional pre | 297 | 3 | 2.63 | 3.0 | 1 | 5 |
| Claridad vocacional post | 285 | 15 | 3.25 | 3.0 | 1 | 5 |
| Bienestar emocional pre | 298 | 2 | 3.12 | 3.0 | 1 | 5 |
| Bienestar emocional post | 286 | 14 | 3.12 | 3.0 | 1 | 5 |


Resultado esperable:

- La edad promedio está alrededor de **15.4 años**, con mediana de 15.
- Hay edades mínimas y máximas de **12** y **19**, lo que debería marcarse como posible alerta porque el rango esperado del programa era 13 a 18.
- La asistencia media es cercana a **11.1 sesiones** sobre 16.
- El NPS promedio es alto, alrededor de **8.06**.
- Las variables post suelen tener más valores faltantes que las variables pre.

## 4. Acceso digital y posibles brechas

### 4.1 Acceso a internet

- `diario`: 149 (49.7%)
- `semanal`: 62 (20.7%)
- `ocasional`: 60 (20.0%)
- `no_tiene`: 29 (9.7%)

Resultado esperable:

- Cerca de la mitad de la muestra reporta acceso diario a internet.
- Un grupo relevante tiene acceso semanal u ocasional.
- Cerca de 1 de cada 10 reporta no tener acceso.

### 4.2 Dispositivo principal

- `celular_propio`: 178 (59.3%)
- `celular_compartido`: 62 (20.7%)
- `ninguno`: 30 (10.0%)
- `computador`: 30 (10.0%)

Resultado esperable:

- Predomina el uso de celular propio.
- El computador es minoritario.
- Hay un grupo con celular compartido y otro sin dispositivo, relevantes para interpretar brechas de acceso.

### 4.3 Acceso a internet por zona

| Zona | n | Diario | Semanal | Ocasional | No tiene |
|---|---:|---:|---:|---:|---:|
| urbana | 180 | 55.0% | 18.9% | 18.3% | 7.8% |
| rural | 120 | 41.7% | 23.3% | 22.5% | 12.5% |


Resultado esperable:

- La zona urbana tiene mayor proporción de acceso diario a internet que la rural.
- La zona rural presenta mayor proporción de jóvenes sin internet.
- La IA debe presentar esto como una brecha descriptiva, no como una conclusión causal.

## 5. Participación previa, trabajo/cuidado y apoyo familiar

### 5.1 Participación previa en actividades

- `no`: 173 (57.7%)
- `si`: 127 (42.3%)

Resultado esperable: la mayoría no había participado previamente en actividades similares, lo que puede interpretarse como una población con exposición previa limitada a este tipo de programas.

### 5.2 Trabajo o cuidado

- `ninguno`: 172 (57.3%)
- `cuidado_familiar`: 60 (20.0%)
- `trabajo_remunerado`: 50 (16.7%)
- `ambos`: 18 (6.0%)

Resultado esperable: la mayoría no reporta responsabilidades de trabajo o cuidado, pero hay proporciones relevantes con cuidado familiar, trabajo remunerado o ambas responsabilidades.

### 5.3 Apoyo familiar

El apoyo familiar tiene media **3.54** y mediana **4.0** en escala de 1 a 5.
Resultado esperable: el informe puede describirlo como un nivel medio-alto de apoyo familiar, con alguna variabilidad.

## 6. Cambios descriptivos entre mediciones pre y post

| Dimensión | Pares válidos | Media pre | Media post | Cambio medio post-pre | % mejora | % igual | % disminuye |
|---|---:|---:|---:|---:|---:|---:|---:|
| Autoeficacia | 276 | 3.10 | 3.47 | 0.37 | 34.4% | 65.6% | 0.0% |
| Habilidades digitales | 268 | 2.94 | 3.62 | 0.67 | 58.6% | 41.4% | 0.0% |
| Conocimiento oportunidades | 281 | 2.40 | 3.19 | 0.79 | 62.3% | 37.7% | 0.0% |
| Claridad vocacional | 282 | 2.64 | 3.25 | 0.61 | 52.5% | 47.5% | 0.0% |
| Bienestar emocional | 284 | 3.14 | 3.12 | -0.02 | 22.9% | 52.1% | 25.0% |


Resultado esperable:

- La mejora descriptiva más alta está en **conocimiento de oportunidades**.
- También hay mejoras claras en **habilidades digitales** y **claridad vocacional**.
- La **autoeficacia** mejora de forma más moderada.
- El **bienestar emocional** se mantiene prácticamente estable.
- El informe no debe afirmar que el programa causó estos cambios, solo que en la base sintética se observan diferencias descriptivas entre mediciones pre y post.
- La IA debería mencionar que las variables post tienen más valores faltantes, por lo que la comparación debe leerse con cautela.

## 7. Finalización, asistencia, satisfacción y postulación

### 7.1 Variables generales

Finalización del programa:

- `si`: 152 (50.7%)
- `no`: 148 (49.3%)

Postulación a oportunidades:

- `si`: 201 (67.0%)
- `no`: 99 (33.0%)

Resultado esperable:

- Aproximadamente la mitad finalizó el programa.
- La postulación a oportunidades es mayoritaria, con cerca de dos tercios de la muestra.

### 7.2 Resultados por territorio

| Territorio | n | Modalidad asociada | Asistencia media | Finalizó | NPS medio | Postuló oportunidad |
|---|---:|---|---:|---:|---:|---:|
| Yolombó | 115 | remota | 9.69 | 37.4% | 7.67 | 67.0% |
| Villanueva | 97 | presencial | 12.70 | 69.1% | 8.84 | 69.1% |
| San Francisco | 88 | hibrida | 11.25 | 47.7% | 7.74 | 64.8% |


Resultado esperable:

- **Villanueva** muestra mayor asistencia promedio, mayor finalización y mayor NPS.
- **Yolombó** muestra menor asistencia promedio y menor finalización.
- **San Francisco** se ubica en un punto intermedio en asistencia y finalización.
- La postulación a oportunidades es relativamente alta en los tres territorios y no presenta diferencias tan marcadas como la finalización.
- La IA debe tener cuidado porque territorio y modalidad están perfectamente asociados en esta base; por tanto, no debe separar efectos de territorio y modalidad.

### 7.3 Asistencia y resultados

| Banda de asistencia | n | Finalizó | Postuló oportunidad | NPS medio |
|---|---:|---:|---:|---:|
| baja_0_7 | 39 | 0.0% | 59.0% | 6.41 |
| media_8_12 | 157 | 35.0% | 61.8% | 7.63 |
| alta_13_16 | 101 | 94.1% | 77.2% | 9.37 |


Resultado esperable:

- La finalización aumenta fuertemente con la asistencia.
- En asistencia baja no hay finalización.
- En asistencia alta, casi todos finalizan.
- El NPS también aumenta con la asistencia.
- La postulación a oportunidades es más alta entre quienes tienen asistencia alta, aunque también aparece en asistencia media y baja.

### 7.4 Finalización y NPS

Promedios esperados:

- Finalizaron: asistencia media **13.34**, NPS medio **9.30**.
- No finalizaron: asistencia media **8.82**, NPS medio **6.82**.

Resultado esperable:

- El informe debe detectar que quienes finalizan tienen mayor asistencia y mayor satisfacción.
- Debe describirlo como una asociación descriptiva.

### 7.5 Categorías NPS

| Categoría NPS | n | Finalizó | Postuló oportunidad |
|---|---:|---:|---:|
| detractor_0_6 | 69 | 2.9% | 65.2% |
| pasivo_7_8 | 87 | 31.0% | 63.2% |
| promotor_9_10 | 138 | 85.5% | 70.3% |


Resultado esperable:

- Los promotores son el grupo más numeroso.
- La finalización es mucho más alta entre promotores que entre pasivos y detractores.
- La postulación a oportunidades no cambia tanto por categoría NPS como la finalización.

## 8. Área de interés

- `tecnologia`: 61 (20.9%)
- `emprendimiento`: 57 (19.5%)
- `educacion`: 51 (17.5%)
- `artes_cultura`: 37 (12.7%)
- `deporte`: 37 (12.7%)
- `salud`: 34 (11.6%)
- `no_sabe`: 15 (5.1%)
- Missing: 8 (2.7% sobre la base total)

Resultado esperable:

- Las áreas con más frecuencia son tecnología, emprendimiento y educación.
- `no_sabe` es una categoría minoritaria, pero relevante para orientación vocacional.
- Hay 8 valores faltantes en área de interés.

## 9. Calidad de datos y valores faltantes

### 9.1 Variables con missing

| Variable | Missing | % sobre total |
|---|---:|---:|
| observacion_calidad_dato | 290 | 96.7% |
| habilidades_digitales_post | 30 | 10.0% |
| autoeficacia_post | 21 | 7.0% |
| conocimiento_oportunidades_post | 18 | 6.0% |
| claridad_vocacional_post | 15 | 5.0% |
| bienestar_emocional_post | 14 | 4.7% |
| apoyo_familiar | 8 | 2.7% |
| area_interes | 8 | 2.7% |
| satisfaccion_nps | 6 | 2.0% |
| edad | 4 | 1.3% |
| autoeficacia_pre | 3 | 1.0% |
| habilidades_digitales_pre | 3 | 1.0% |
| claridad_vocacional_pre | 3 | 1.0% |
| asistencia_sesiones | 3 | 1.0% |
| bienestar_emocional_pre | 2 | 0.7% |
| conocimiento_oportunidades_pre | 1 | 0.3% |


Resultado esperable:

- La IA debe señalar que las variables post tienen más valores faltantes que las pre.
- `habilidades_digitales_post` es la variable sustantiva con más missing: 30 casos.
- `autoeficacia_post`, `conocimiento_oportunidades_post`, `claridad_vocacional_post` y `bienestar_emocional_post` también tienen valores faltantes relevantes.
- `observacion_calidad_dato` tiene 290 missing, pero esto no debe interpretarse como mala calidad general: es una variable de observación que solo se diligencia cuando hay alertas.

### 9.2 Observaciones de calidad

- `registro_incompleto`: 4 (40.0%)
- `posible_duplicado`: 3 (30.0%)
- `edad_fuera_rango_esperado`: 2 (20.0%)
- `respuesta_muy_rapida`: 1 (10.0%)
- Missing: 290 (96.7% sobre la base total)

Resultado esperable:

- Hay 10 registros con alguna observación de calidad.
- Las categorías incluyen registro incompleto, posible duplicado, edad fuera de rango esperado y respuesta muy rápida.
- La IA debería recomendar revisar estos casos antes de producir un informe final.

### 9.3 Edades fuera del rango esperado

Resultado esperado:

- Edad mínima: 12.
- Edad máxima: 19.
- Hay casos fuera del rango objetivo 13-18.
- El informe debería señalar esta inconsistencia como una alerta de validación o depuración.

## 10. Hallazgos que el Informe IA debería destacar en el resumen ejecutivo

Un buen resumen ejecutivo debería incluir algo parecido a esto:

1. La base sintética contiene 300 registros distribuidos en tres territorios: Yolombó, Villanueva y San Francisco.
2. La muestra es mayoritariamente urbana y se concentra en estratos 1 y 2.
3. Hay una distribución relativamente balanceada entre hombres y mujeres.
4. Se observan mejoras descriptivas entre mediciones pre y post en conocimiento de oportunidades, habilidades digitales y claridad vocacional.
5. La asistencia está fuertemente asociada de forma descriptiva con finalización y satisfacción.
6. Villanueva/presencial muestra mejores indicadores de asistencia, finalización y NPS, mientras que Yolombó/remota muestra los niveles más bajos en finalización.
7. Existen brechas descriptivas de acceso digital, especialmente entre zona urbana y rural.
8. Hay alertas de calidad por valores faltantes en variables post y algunos casos fuera del rango de edad esperado.

## 11. Señales de alerta en un reporte generado por IA

El reporte debería considerarse problemático si:

- Afirma causalidad del programa.
- Dice que hay significancia estadística sin que se hayan calculado pruebas.
- Inventa tamaños de muestra, porcentajes o variables no existentes.
- Omite por completo los valores faltantes.
- No menciona que la base es sintética.
- Confunde territorio con modalidad sin advertir que están asociados.
- Trata `observacion_calidad_dato` como una variable sustantiva común y no como una alerta de calidad.
- Hace inferencias fuertes sobre grupos con muy pocos casos, como `no_binario` o `prefiere_no_responder`.
- Interpreta el cambio pre-post como impacto causal.
- No identifica la relación descriptiva entre asistencia, finalización y NPS.

## 12. Resultado esperado en próximos pasos sugeridos

La IA debería recomendar, como mínimo:

- Revisar valores faltantes, especialmente en variables post.
- Revisar casos con observaciones de calidad.
- Validar edades fuera del rango esperado.
- Profundizar en cruces por territorio/modalidad, zona, sexo y asistencia.
- Generar visualizaciones de distribución y cruces clave.
- Analizar la no respuesta en mediciones post.
- Si el objetivo fuera evaluación de impacto, aclarar que se necesitaría un diseño causal o información adicional.
- Evitar conclusiones definitivas sin revisión humana.
