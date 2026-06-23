# Plan paso a paso — Integración de Gemini para reportes preliminares de EDA

> Versión didáctica, pensada para seguirla sin experiencia previa en data engineering.
> Estado: **plan / propuesta**. Todavía no se toca el código de la app.
> Proyecto: QuanTi Stats (`app-descriptivas`).

**Qué vamos a lograr:** que dentro de la app, con (1) la base de datos ya cargada, (2) un diccionario de variables o el formulario de ODK, y (3) una instrucción escrita por ti, un modelo de inteligencia artificial de Google (Gemini) escriba un **borrador de reporte de análisis descriptivo**. La IA no "ve" la base completa: lee las **tablas y descriptivas que la app ya calcula** y las redacta en prosa.

---

## 0. Glosario rápido (lee esto primero)

Para que el resto del documento tenga sentido:

- **API**: una forma de que tu programa "le hable" a un servicio de otra empresa por internet. Aquí, tu app le habla a Gemini.
- **Modelo (LLM)**: el "cerebro" de IA que recibe texto y devuelve texto. Gemini tiene varios, de más baratos/rápidos a más caros/potentes.
- **API key / token**: una contraseña larga que identifica tu cuenta ante Google. Quien la tenga puede gastar en tu nombre, así que **es secreta**.
- **Token (de cobro)**: la unidad con la que se mide cuánto texto entra y sale. Aproximadamente, 1 token ≈ ¾ de una palabra en español. Se factura por millón de tokens.
- **SDK**: una librería de Python que hace fácil llamar a la API (en vez de armar peticiones a mano). El de Gemini se llama `google-genai`.
- **Secreto (`secrets`)**: lugar seguro donde guardas la API key, **fuera del código**, para que no termine publicada en GitHub.
- **EDA**: *Exploratory Data Analysis*, análisis exploratorio de datos: el primer vistazo descriptivo a una base.
- **Free tier / Paid tier**: nivel gratuito (para probar, con límites y menos privacidad) y nivel pagado (para uso real, más privado y con más capacidad).
- **Alucinación**: cuando la IA "inventa" un dato que suena creíble pero es falso. Es el riesgo principal y lo controlamos dándole las tablas ya calculadas.

---

## 1. La idea en una imagen

La regla de oro: **la IA recibe resúmenes ya calculados por la app, nunca la base de datos cruda.** Es más barato, más exacto y más seguro.

```
   Base cargada
        │
        ▼
[La app calcula]  Descriptivas (Continuas/Categóricas)  +  Tablas cruzadas
        │                         (esto YA existe en la app hoy)
        ▼
   Texto compacto con esas tablas
        │
        +  Diccionario de variables / formulario ODK
        +  Tu instrucción ("enfócate en X", "para directivos", etc.)
        ▼
   Se arma un "prompt" (el mensaje completo para la IA)
        ▼
   Gemini (modelo económico)  ──►  Borrador de reporte en texto
        ▼
   Se muestra en una pestaña nueva y se puede exportar (Word/PDF)
```

¿Por qué no mandar la base completa? Tres razones:
1. **Exactitud**: los modelos de IA son malos haciendo cálculo numérico sobre datos crudos; en cambio redactan muy bien a partir de números ya correctos.
2. **Costo**: una tabla resumida pesa muchísimo menos que toda la base → menos tokens → más barato.
3. **Privacidad**: no sale la microdata de las encuestas hacia un tercero.

---

## 2. PARTE A — Lo que haces TÚ una sola vez (sin tocar código)

Esta parte es de "plomería": dejar lista la cuenta y la llave. Hazla en orden. Tiempo estimado: 15–30 min.

### Paso A1 — Crear tu API key en Google AI Studio
1. Entra a `https://aistudio.google.com/apikey` con tu cuenta de Google.
2. Acepta los términos si te los muestra.
3. Pulsa **"Create API key"** (Crear clave de API).
4. Copia la clave que aparece (una cadena larga tipo `AIza...`). **Guárdala en un lugar seguro** (gestor de contraseñas). No la pegues en chats, correos ni en el código.

> Importante: si alguna vez crees que la clave se filtró, vuelve aquí y bórrala/regenérala. Así deja de funcionar la vieja.

### Paso A2 — Decidir nivel: empezar gratis, pasar a pagado para datos reales
- Para **probar** mientras desarrollas: el **free tier** funciona sin tarjeta y es suficiente para experimentar.
- Para **uso real con datos de encuestas**: activa **facturación (paid tier)** en el proyecto. Motivo clave: en el nivel pagado **Google no usa tus datos para entrenar sus modelos**; en el gratuito sí puede usarlos para mejorar el producto. Con datos de cliente, esto importa (ver §7).
- La facturación se activa desde la consola de Google Cloud asociada (AI Studio te enlaza ahí). Si llegas a un paso que pide **número de tarjeta o datos bancarios, házlo tú directamente en el sitio de Google** — eso no debe delegarse a una IA ni pegarse en ningún chat.

### Paso A3 — (Opcional, decisión de empresa) ¿AI Studio o Vertex AI?
- **AI Studio** = la vía simple, recomendada para empezar.
- **Vertex AI** (dentro de Google Cloud) = la vía corporativa, con control de **dónde se procesan los datos** (residencia), facturación empresarial y garantías contractuales más fuertes. Misma familia de modelos, pero la autenticación es más compleja (cuenta de servicio).
- Recomendación: **empieza con AI Studio**. Solo pásate a Vertex si Equilibrium exige residencia de datos por contrato.

✅ **Al terminar la Parte A tienes:** una API key guardada y decidido el nivel (gratis para probar / pagado para producción). Esto desbloquea todo lo demás.

---

## 3. PARTE B — Qué modelo de Gemini usar (privilegiando lo barato)

Precios oficiales verificados el **22-jun-2026** (página actualizada el 15-jun-2026), nivel pagado, por **1 millón de tokens**, en USD. Los modelos Flash y Flash-Lite tienen además **nivel gratuito** para probar.

| Modelo | Precio entrada /1M | Precio salida /1M | ¿Gratis para probar? | Para qué sirve aquí |
|---|---|---|---|---|
| **Gemini 2.5 Flash-Lite** | $0.125 | $0.75 | Sí | **El más barato.** De sobra para resumir tablas ya hechas. Buen punto de partida. |
| **Gemini 3.1 Flash-Lite** (estable) | $0.25 | $1.50 | Sí | Un poco más nuevo/capaz, sigue siendo muy barato. Alternativa de default. |
| **Gemini 2.5 Flash** | $0.75 | $4.50 | Sí | Redacta mejor; úsalo para reportes "premium" o más largos. |
| **Gemini 3.5 Flash** (estable) | ~$0.75 | ~$4.50 | Sí | Lo más capaz de la gama económica; para casos exigentes. |
| Gemini 2.5 / 3.1 **Pro** | $1.50–$2.00+ | $9.00–$12.00+ | No | Innecesario aquí y mucho más caro. |

**Recomendación práctica:**
- Arranca con **Gemini 2.5 Flash-Lite** (o 3.1 Flash-Lite). Para "tomar tablas + diccionario y redactar", la capacidad sobra.
- En la app pondremos un **interruptor "Económico / Alta calidad"** que cambia entre Flash-Lite y Flash, para que decidas por reporte.
- ¿Cuánto cuesta un reporte? Uno que envíe ~15–40 mil tokens (tablas + diccionario + instrucción) y devuelva ~3–8 mil tokens de texto cuesta, con Flash-Lite, **fracciones de centavo de dólar**. El costo no será tu limitante.

> Consejo: el nombre exacto del modelo (ej. `gemini-2.5-flash-lite`) lo guardaremos en un archivo de configuración, no "incrustado" en el código, porque Google renueva la gama seguido (un modelo pasa de *preview* a *estable* a *retirado*).

---

## 4. PARTE C — Cómo se conecta a la app (panorama técnico, explicado simple)

Tu app ya está ordenada así (ver `CLAUDE.md`): la pantalla y el flujo viven en `app.py`, y la lógica vive en archivos dentro de `src/`. Vamos a seguir esa misma costumbre y añadir **una pieza nueva**, sin tocar lo que ya funciona.

Qué se agregaría (esto lo implementaríamos en una fase posterior, no ahora):

1. **Un archivo nuevo `src/ai_report.py`** que concentra todo lo de IA:
   - conectar con Gemini usando la API key guardada,
   - convertir las tablas/descriptivas a texto compacto,
   - armar el mensaje (prompt) juntando tablas + diccionario + tu instrucción,
   - llamar al modelo y recibir el reporte,
   - limpiar el resultado.
2. **Una pestaña nueva en la app**, por ejemplo "Informe IA", que aparecería junto a las pestañas actuales (Instrucciones, Vista previa, Gráficos, Tablas cruzadas, Continuas, Categóricas).
3. **Reutilizar lo que ya existe**: las funciones que ya generan descriptivas y tablas cruzadas (`continuous_summary`, `categorical_summary`, `compute_crosstab`) se aprovechan tal cual; el archivo nuevo solo las **convierte en texto** para la IA. No se reescribe estadística.
4. **Exportar el reporte** a Word (`.docx`) o PDF con la identidad de Equilibrium, o como `.md` simple para el MVP.

Lo nuevo en dependencias: agregar `google-genai` (con `uv add google-genai`). No hace falta cambiar `packages.txt` (esto no usa navegador/Chromium).

---

## 5. PARTE D — De qué se alimenta la IA (las 4 piezas del mensaje)

El "prompt" que recibe Gemini se arma juntando cuatro bloques. Entender esto te ayuda a saber qué preparar:

1. **Instrucción de rol (fija, la ponemos nosotros):** algo como *"Eres un analista que redacta reportes preliminares en español. Básate SOLO en las tablas que te doy. No inventes cifras. Si un dato no está, dilo."* → esto reduce las alucinaciones.
2. **Diccionario / formulario ODK:** explica qué significa cada variable y cada categoría. Puede venir de:
   - un archivo de diccionario que subas (CSV/XLSX), o
   - el **XLSForm de ODK** (las hojas `survey` y `choices`), del que la app extraería las etiquetas de preguntas y opciones.
3. **Tablas seleccionadas:** las descriptivas y cruces que tú elijas alimentar, convertidas a texto.
4. **Tu instrucción libre:** el foco que quieres (audiencia, hipótesis, qué resaltar, qué secciones).

Le pediremos a la IA una **estructura fija** de salida (resumen ejecutivo → hallazgos por variable → cruces relevantes → calidad de los datos → próximos pasos) para que el reporte sea consistente.

---

## 6. PARTE E — Fases de implementación (checklist)

Marca cada casilla al completarla.

- [ ] **Fase 0 — Acceso (TÚ, Parte A):** API key creada, nivel decidido, facturación activada si va a producción. *Bloquea todo lo demás.*
- [ ] **Fase 1 — Prueba mínima:** un script chiquito que mande "Hola" a Gemini y muestre la respuesta. Sirve para confirmar que la llave, el modelo y la conexión funcionan. (Ejemplo de código abajo.)
- [ ] **Fase 2 — Conectar el secreto a la app:** que la app lea la API key desde `st.secrets` (local) y desde los *Secrets* de Streamlit Cloud.
- [ ] **Fase 3 — Conversores:** funciones que pasan las descriptivas/cruces y el diccionario/ODK a texto compacto.
- [ ] **Fase 4 — Módulo + pestaña:** crear `src/ai_report.py` y la pestaña "Informe IA" con: selector de tablas, caja de instrucción, interruptor Económico/Alta calidad y botón "Generar".
- [ ] **Fase 5 — Exportación:** descargar el reporte en `.md`, y luego `.docx`/`.pdf` con marca Equilibrium.
- [ ] **Fase 6 — Robustez:** mensajes claros si falta la llave, manejo de errores y de límites de uso, control del tamaño del texto enviado.

### Ejemplo de "Fase 1" (prueba mínima)

Esto NO se agrega a la app todavía; es solo para confirmar que tu llave funciona. Guárdalo como `prueba_gemini.py` y córrelo aparte.

```python
# prueba_gemini.py  (solo para validar la conexión)
from google import genai

# Pega aquí TEMPORALMENTE tu API key solo para esta prueba local.
# (En la app real NO se hace así: irá en st.secrets, ver Fase 2.)
client = genai.Client(api_key="TU_API_KEY_AQUI")

respuesta = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents="Responde en español: di 'conexión exitosa' y nada más.",
)
print(respuesta.text)
```

Cómo correrlo (en este equipo se usa `uv`):
```powershell
uv add google-genai
uv run python prueba_gemini.py
```
Si imprime "conexión exitosa", la llave y el modelo funcionan. Borra la llave del archivo después de probar.

### Cómo se vería el secreto en la app (Fase 2)

Local — crea `.streamlit/secrets.toml` (y agrégalo a `.gitignore` para que NO se suba):
```toml
GEMINI_API_KEY = "tu_clave_aqui"
```
En el código de la app se leería así (sin que la clave aparezca nunca en el repo):
```python
import streamlit as st
from google import genai
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
```
En **Streamlit Community Cloud**: abre tu app → *Settings* → *Secrets* y pega ahí la misma línea `GEMINI_API_KEY = "..."`.

---

## 7. PARTE F — Privacidad y seguridad (importante: son datos de encuestas)

- **No enviar la base cruda.** Solo agregados (tablas/descriptivas) + diccionario. Es la mayor protección y ya es parte del diseño.
- **Usa el nivel pagado para datos reales.** El gratuito puede usar tu contenido para mejorar los productos de Google; el pagado **no entrena con tus datos**.
- **La API key es secreta.** Nunca en el código ni en GitHub: solo en `st.secrets` o variables de entorno. Si se filtra, regénerala.
- **Marca el reporte como "preliminar, generado por IA".** Debe revisarlo una persona antes de usarlo; puede contener errores.
- **Residencia de datos:** si el contrato con un cliente exige que los datos se procesen en cierta región, esa es la razón para evaluar **Vertex AI** en vez de AI Studio.

---

## 8. PARTE G — Riesgos y cómo los manejamos

- **Que la IA invente cifras** → le damos tablas ya calculadas + instrucción estricta + estructura fija; aun así el reporte se marca como revisable.
- **Que cambie el modelo** → el nombre del modelo va en configuración, fácil de actualizar.
- **Que se topen los límites de uso** → el nivel pagado los relaja; manejamos el error con un reintento y un mensaje claro.
- **Que se envíe demasiado texto** → la app avisará o recortará si seleccionas demasiadas tablas.
- **Costos sorpresa** (poco probable aquí) → puedes fijar un límite de gasto en la consola de Google y mostrar un estimado de tokens en la app.

---

## 9. Decisiones que necesito de ti para arrancar

1. **Entorno/privacidad:** ¿empezamos con **AI Studio (nivel pagado)**, o Equilibrium exige **Vertex AI** por residencia de datos?
2. **Diccionario/ODK:** ¿el diccionario llegará como archivo aparte (CSV/XLSX), quieres que la app lea directamente el **XLSForm de ODK**, o ambos?
3. **Modelo por defecto:** ¿arrancamos con el más barato (**2.5 Flash-Lite**) con interruptor a "alta calidad", o prefieres **3.1 Flash-Lite** como base?
4. **Formato del reporte:** ¿basta **Markdown en pantalla** para el primer MVP, o desde el inicio quieres **Word/PDF** con identidad Equilibrium?
5. **Estructura del reporte:** ¿secciones fijas (resumen, hallazgos, cruces, calidad, próximos pasos), o totalmente libre según tu instrucción?

Cuando me respondas estas cinco, aterrizo la **Fase 1 y 2** en detalle (incluido el código real para tu app) y seguimos.
