from __future__ import annotations

import json
import os
from collections import defaultdict

from openai import OpenAI, OpenAIError

from .models import Entity, Relation

ENTITY_TYPES = [
    "PERSONA_NATURAL", "PERSONA_JURIDICA", "ORGANISMO_PUBLICO", "INSTITUCION_FINANCIERA",
    "ORGANIZACION_INTERNACIONAL", "ORGANIZACION_SIN_FINES_DE_LUCRO", "PARTIDO_POLITICO",
    "MEDIO_COMUNICACION", "TRIBUNAL", "FISCALIA", "LUGAR", "PAIS", "REGION", "CIUDAD_COMUNA",
    "LEY_NORMA", "DELITO", "PRODUCTO_FINANCIERO", "CRIPTOACTIVO", "OTRA_ORGANIZACION", "OTRO"
]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mention": {"type": "string"},
                    "canonical_name": {"type": "string"},
                    "type": {"type": "string", "enum": ENTITY_TYPES},
                    "subtype": {"type": "string"},
                    "role": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "evidence": {"type": "string"},
                },
                "required": ["mention", "canonical_name", "type", "subtype", "role", "aliases", "evidence"],
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "source": {"type": "string"},
                    "relation": {"type": "string"},
                    "target": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["source", "relation", "target", "evidence"],
            },
        },
    },
    "required": ["entities", "relations"],
}


def _candidate_payload(candidates: list[Entity]) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    for e in candidates:
        grouped[e.type].append(e.mention)
    return json.dumps({k: sorted(set(v)) for k, v in grouped.items()}, ensure_ascii=False)


def _friendly_openai_error(exc: Exception) -> str:
    """Devuelve un mensaje corto y estable para el dashboard/logs, sin secretos."""
    text = str(exc)
    low = text.casefold()
    if "insufficient_quota" in low or "credit_balance_exhausted" in low or "no credits remaining" in low:
        return "Sin créditos disponibles en la API de OpenAI; se usó GLiNER2 + reglas como fallback."
    if "rate limit" in low or "429" in low:
        return "Límite temporal de la API de OpenAI; se usó GLiNER2 + reglas como fallback."
    if "401" in low or "authentication" in low or "api key" in low:
        return "No fue posible autenticar la API de OpenAI; se usó GLiNER2 + reglas como fallback."
    return "OpenAI no estuvo disponible; se usó GLiNER2 + reglas como fallback."


def adjudicate_with_llm(
    text: str, candidates: list[Entity]
) -> tuple[list[Entity], list[Relation], dict[str, str | bool]]:
    """Adjudica entidades con OpenAI, pero nunca hace fallar el pipeline.

    Si la API no tiene cuota, hay rate limit, falla la autenticación o la salida no
    puede validarse, devuelve los candidatos locales y una explicación de fallback.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return candidates, [], {
            "llm_used": False,
            "llm_fallback": True,
            "llm_error": "OPENAI_API_KEY no configurada; se usó GLiNER2 + reglas.",
        }

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5")
    prompt = f"""
Eres un adjudicador NER de alta precisión para prensa chilena.
Objetivo: confirmar, corregir, fusionar y clasificar entidades que estén LITERALMENTE presentes en el texto.
Nunca agregues una entidad cuya mención no aparezca literalmente. No infieras nombres ausentes.
Distingue especialmente PERSONA_NATURAL, PERSONA_JURIDICA, ORGANISMO_PUBLICO e INSTITUCION_FINANCIERA.
El campo role describe solo el rol que el texto atribuye a la entidad. Si no está claro, déjalo vacío.
Las relaciones deben estar explícitamente sustentadas por la noticia y usar entidades presentes.

CANDIDATOS DEL DETECTOR:
{_candidate_payload(candidates)}

TEXTO:
{text[:30000]}
"""

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "Extrae y adjudica entidades con máxima precisión y mínima inferencia."},
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "news_entities",
                    "schema": SCHEMA,
                    "strict": True,
                }
            },
        )
        data = json.loads(response.output_text)
        entities = [Entity(**item, signals=["llm_confirmado"]) for item in data.get("entities", [])]
        relations = [Relation(**item, confidence="MEDIA") for item in data.get("relations", [])]
        return entities, relations, {
            "llm_used": True,
            "llm_fallback": False,
            "llm_error": "",
        }
    except OpenAIError as exc:
        return candidates, [], {
            "llm_used": False,
            "llm_fallback": True,
            "llm_error": _friendly_openai_error(exc),
        }
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        return candidates, [], {
            "llm_used": False,
            "llm_fallback": True,
            "llm_error": f"Salida LLM no válida ({type(exc).__name__}); se usó GLiNER2 + reglas como fallback.",
        }
