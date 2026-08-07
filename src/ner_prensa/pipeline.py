from __future__ import annotations

import os
from collections import Counter

from .fetcher import fetch_article
from .gliner_engine import extract_with_gliner
from .llm_engine import adjudicate_with_llm
from .models import AnalysisResult, Entity
from .rules import calibrate_confidence, deterministic_refine, merge_entities, reject_nonexistent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def analyze_url(url: str) -> AnalysisResult:
    article = fetch_article(url)
    use_gliner = _env_bool("USE_GLINER", True)
    use_llm = _env_bool("USE_LLM", True) and bool(os.getenv("OPENAI_API_KEY"))

    candidates: list[Entity] = []
    gliner_error = ""
    if use_gliner:
        try:
            candidates = extract_with_gliner(article.text)
        except Exception as exc:
            gliner_error = str(exc)

    # Si GLiNER falla y hay LLM, el LLM puede trabajar sin candidatos; si no, se informa resultado vacío.
    entities, relations = adjudicate_with_llm(article.text, candidates) if use_llm else (candidates, [])

    refined: list[Entity] = []
    for e in entities:
        e = deterministic_refine(e, article.text)
        refined.append(e)
    refined = reject_nonexistent(refined, article.text)
    refined = merge_entities(refined)
    refined = [calibrate_confidence(e) for e in refined]
    refined.sort(key=lambda e: ({"ALTA": 0, "MEDIA": 1, "BAJA": 2}[e.confidence], e.type, e.canonical_name.casefold()))

    # Relaciones también deben referir a entidades finalmente aceptadas.
    names = {e.canonical_name.casefold() for e in refined} | {e.mention.casefold() for e in refined}
    safe_relations = [r for r in relations if r.source.casefold() in names and r.target.casefold() in names]

    stats = dict(Counter(e.type for e in refined))
    return AnalysisResult(
        article=article,
        entities=refined,
        relations=safe_relations,
        stats=stats,
        engine={
            "gliner": use_gliner,
            "llm": use_llm,
            "gliner_model": os.getenv("GLINER_MODEL", "fastino/gliner2-base-v1"),
            "llm_model": os.getenv("OPENAI_MODEL", "gpt-5") if use_llm else "",
            "gliner_error": gliner_error,
        },
    )
