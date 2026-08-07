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
    llm_requested = _env_bool("USE_LLM", True)
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    use_llm = llm_requested and has_api_key

    candidates: list[Entity] = []
    gliner_error = ""
    if use_gliner:
        try:
            candidates = extract_with_gliner(article.text)
        except Exception as exc:
            gliner_error = str(exc)

    if use_llm:
        entities, relations, llm_meta = adjudicate_with_llm(article.text, candidates)
    else:
        entities, relations = candidates, []
        if llm_requested and not has_api_key:
            llm_meta = {
                "llm_used": False,
                "llm_fallback": True,
                "llm_error": "OPENAI_API_KEY no configurada; se usó GLiNER2 + reglas.",
            }
        else:
            llm_meta = {"llm_used": False, "llm_fallback": False, "llm_error": ""}

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
            "llm": bool(llm_meta["llm_used"]),
            "llm_requested": llm_requested,
            "llm_fallback": bool(llm_meta["llm_fallback"]),
            "gliner_model": os.getenv("GLINER_MODEL", "fastino/gliner2-base-v1"),
            "llm_model": os.getenv("OPENAI_MODEL", "gpt-5") if llm_requested else "",
            "gliner_error": gliner_error,
            "llm_error": str(llm_meta["llm_error"]),
        },
    )
