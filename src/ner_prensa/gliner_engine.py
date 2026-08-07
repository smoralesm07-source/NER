from __future__ import annotations

import os

from .models import Entity

LABEL_MAP = {
    "persona natural": "PERSONA_NATURAL",
    "empresa privada": "PERSONA_JURIDICA",
    "organismo público": "ORGANISMO_PUBLICO",
    "institución financiera": "INSTITUCION_FINANCIERA",
    "organización internacional": "ORGANIZACION_INTERNACIONAL",
    "organización sin fines de lucro": "ORGANIZACION_SIN_FINES_DE_LUCRO",
    "partido político": "PARTIDO_POLITICO",
    "medio de comunicación": "MEDIO_COMUNICACION",
    "tribunal": "TRIBUNAL",
    "fiscalía": "FISCALIA",
    "país": "PAIS",
    "región": "REGION",
    "ciudad o comuna": "CIUDAD_COMUNA",
    "lugar": "LUGAR",
    "ley o norma": "LEY_NORMA",
    "delito": "DELITO",
    "producto financiero": "PRODUCTO_FINANCIERO",
    "criptoactivo": "CRIPTOACTIVO",
    "otra organización": "OTRA_ORGANIZACION",
}

LABELS = list(LABEL_MAP)


def extract_with_gliner(text: str) -> list[Entity]:
    try:
        from gliner2 import GLiNER2
    except Exception as exc:
        raise RuntimeError("GLiNER2 no está instalado. Instala el extra 'local'.") from exc

    model_name = os.getenv("GLINER_MODEL", "fastino/gliner2-base-v1")
    extractor = GLiNER2.from_pretrained(model_name)
    # GLiNER2 puede trabajar por schema. Para artículos largos, troceamos para evitar truncamiento.
    chunks: list[str] = []
    max_chars = 7000
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut > start + 1200:
                end = cut
        chunks.append(text[start:end])
        start = end

    entities: list[Entity] = []
    for chunk in chunks:
        result = extractor.extract_entities(chunk, LABELS)
        groups = result.get("entities", {}) if isinstance(result, dict) else {}
        for label, values in groups.items():
            etype = LABEL_MAP.get(label, "OTRO")
            for value in values or []:
                mention = value.get("text") if isinstance(value, dict) else str(value)
                mention = mention.strip()
                if not mention:
                    continue
                entities.append(Entity(
                    mention=mention,
                    canonical_name=mention,
                    type=etype,  # type: ignore[arg-type]
                    signals=["gliner2"],
                ))
    return entities
