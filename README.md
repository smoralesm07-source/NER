# Analizador NER de Prensa — GitHub

Aplicación híbrida para recibir una URL de prensa, extraer el artículo e identificar entidades con alta trazabilidad:

- **GLiNER2**: detección zero-shot / schema-based.
- **Reglas chilenas**: persona jurídica, organismos públicos, instituciones financieras y aliases conocidos.
- **OpenAI Structured Output (opcional)**: adjudicación contextual y relaciones.
- **Validador determinístico**: rechaza cualquier entidad cuya `mention` no aparezca literalmente en el artículo.
- **GitHub Actions**: ejecuta el análisis sin exponer secretos.
- **GitHub Pages**: publica el último resultado como dashboard.

## Arquitectura

`URL -> Trafilatura -> GLiNER2 -> reglas -> LLM opcional -> validación -> JSON -> GitHub Pages`

> GitHub Pages es estático: por seguridad la API key no se usa desde el navegador. El análisis se ejecuta en Actions y luego Pages muestra el resultado.

## 1. Crear el repositorio

1. Crea un repositorio nuevo en GitHub, por ejemplo `NER-Prensa`.
2. Sube todo el contenido de este proyecto manteniendo las carpetas `.github`, `src`, `scripts`, `tests` y `docs`.
3. Haz commit a la rama `main`.

## 2. Configurar OpenAI (recomendado)

En GitHub:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Crea:

- **Name:** `OPENAI_API_KEY`
- **Secret:** tu API key

Si no agregas el secret, puedes ejecutar con `use_llm=false` y usar solo GLiNER2 + reglas.

## 3. Activar GitHub Pages

En:

`Settings -> Pages -> Build and deployment -> Source`

elige **GitHub Actions**.

El workflow `Deploy Pages` publicará `docs/`.

## 4. Analizar una noticia

### Opción A — desde la propia página (recomendada)

1. Abre GitHub Pages.
2. Pega la URL en **Nuevo análisis**.
3. Pulsa **Analizar noticia**.
4. Se abrirá un Issue prellenado; publícalo.
5. El workflow valida que quien abrió la solicitud sea el propietario del repositorio, ejecuta el motor y cierra el Issue al finalizar.

Esto evita colocar tokens o API keys en el HTML público.

### Opción B — desde Actions

1. Ve a **Actions**.
2. Abre **Analizar noticia**.
3. Pulsa **Run workflow**.
4. Pega la URL completa.
5. Mantén `use_gliner=true` y `use_llm=true` para máxima precisión.
6. Ejecuta.

El workflow genera `docs/data/latest.json`, lo guarda en el repositorio y dispara la actualización de Pages.

## 5. Taxonomía inicial

- PERSONA_NATURAL
- PERSONA_JURIDICA
- ORGANISMO_PUBLICO
- INSTITUCION_FINANCIERA
- ORGANIZACION_INTERNACIONAL
- ORGANIZACION_SIN_FINES_DE_LUCRO
- PARTIDO_POLITICO
- MEDIO_COMUNICACION
- TRIBUNAL / FISCALIA
- PAIS / REGION / CIUDAD_COMUNA / LUGAR
- LEY_NORMA / DELITO
- PRODUCTO_FINANCIERO / CRIPTOACTIVO
- OTRA_ORGANIZACION / OTRO

## 6. Confiabilidad

La confianza no es un porcentaje inventado por el LLM. Se calcula por convergencia de señales, por ejemplo:

- GLiNER2 detecta la mención.
- LLM confirma la clasificación.
- Diccionario o regla chilena confirma el tipo.
- El span literal queda validado en el texto.

Toda entidad que no exista literalmente en el artículo es descartada.

## 7. Pruebas

```bash
pip install -e '.[dev]'
pytest -q
```

Para ejecutar GLiNER2 localmente:

```bash
pip install -e '.[local]'
export USE_GLINER=true
export USE_LLM=false
python scripts/analyze_url.py 'https://...'
```

## Próxima evolución recomendada

La segunda iteración debería agregar un **corpus chileno anotado** y un benchmark por clase (precision, recall, F1 exact-span, error PN/PJ), además de entity resolution histórico para unir menciones de la misma persona o institución entre múltiples noticias.
