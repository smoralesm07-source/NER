from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Entity

LEGAL_SUFFIX = re.compile(r"\b(?:S\.?A\.?|SpA|Ltda\.?|Limitada|EIRL|S\.A\.C\.|Sociedad An[oó]nima)\b", re.I)
PUBLIC_PREFIX = re.compile(r"^(?:Ministerio|Subsecretar[ií]a|Servicio|Superintendencia|Municipalidad|Gobierno Regional|Comisi[oó]n|Unidad|Direcci[oó]n|Fiscal[ií]a|Defensor[ií]a|Contralor[ií]a|Tribunal)\b", re.I)
FINANCIAL_HINT = re.compile(r"\b(?:Banco|Cooperativa de Ahorro|Corredora de Bolsa|Administradora General de Fondos|AGF|AFP|Aseguradora)\b", re.I)
MEDIA_HINT = re.compile(r"\b(?:Diario|Radio|Noticias|Televisi[oó]n|TVN|CNN|Emol|BioBio|La Tercera|El Mercurio|DF|Cooperativa)\b", re.I)

KNOWN_PUBLIC = {
    "UAF": ("Unidad de Análisis Financiero", "ORGANISMO_PUBLICO", "Unidad de inteligencia financiera"),
    "Unidad de Análisis Financiero": ("Unidad de Análisis Financiero", "ORGANISMO_PUBLICO", "Unidad de inteligencia financiera"),
    "CMF": ("Comisión para el Mercado Financiero", "ORGANISMO_PUBLICO", "Regulador financiero"),
    "Comisión para el Mercado Financiero": ("Comisión para el Mercado Financiero", "ORGANISMO_PUBLICO", "Regulador financiero"),
    "SII": ("Servicio de Impuestos Internos", "ORGANISMO_PUBLICO", "Administración tributaria"),
    "Servicio de Impuestos Internos": ("Servicio de Impuestos Internos", "ORGANISMO_PUBLICO", "Administración tributaria"),
    "PDI": ("Policía de Investigaciones de Chile", "ORGANISMO_PUBLICO", "Policía"),
    "Carabineros": ("Carabineros de Chile", "ORGANISMO_PUBLICO", "Policía"),
}


def occurrences(text: str, mention: str) -> list[tuple[int, int]]:
    if not mention.strip():
        return []
    return [(m.start(), m.end()) for m in re.finditer(re.escape(mention), text, re.I)]


def evidence_window(text: str, start: int, end: int, radius: int = 150) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    chunk = " ".join(text[lo:hi].split())
    return chunk


def deterministic_refine(entity: Entity, text: str) -> Entity:
    raw = entity.mention.strip()
    canonical = entity.canonical_name or raw
    signals = list(entity.signals)
    etype = entity.type
    subtype = entity.subtype

    if raw in KNOWN_PUBLIC:
        canonical, etype, subtype = KNOWN_PUBLIC[raw]
        signals.append("diccionario_institucional")

    if LEGAL_SUFFIX.search(raw):
        etype = "PERSONA_JURIDICA"
        subtype = subtype or "Empresa/sociedad"
        signals.append("sufijo_persona_juridica")

    if FINANCIAL_HINT.search(raw):
        etype = "INSTITUCION_FINANCIERA"
        subtype = subtype or "Entidad financiera"
        signals.append("patron_entidad_financiera")

    if PUBLIC_PREFIX.search(raw):
        etype = "ORGANISMO_PUBLICO"
        subtype = subtype or "Institución pública"
        signals.append("patron_organismo_publico")

    if MEDIA_HINT.search(raw) and etype in {"OTRA_ORGANIZACION", "OTRO"}:
        etype = "MEDIO_COMUNICACION"
        subtype = subtype or "Medio de comunicación"
        signals.append("patron_medio")

    spans = occurrences(text, raw)
    if spans:
        start, end = spans[0]
        entity.start_char = start
        entity.end_char = end
        entity.evidence = entity.evidence or evidence_window(text, start, end)
        signals.append("span_exactamente_validado")
    else:
        signals.append("span_no_encontrado")

    entity.canonical_name = canonical
    entity.type = etype  # type: ignore[assignment]
    entity.subtype = subtype
    entity.signals = sorted(set(signals))
    return entity


def reject_nonexistent(entities: list[Entity], text: str) -> list[Entity]:
    out: list[Entity] = []
    for e in entities:
        if occurrences(text, e.mention):
            out.append(e)
    return out


def merge_entities(entities: list[Entity]) -> list[Entity]:
    merged: dict[tuple[str, str], Entity] = {}
    for e in entities:
        key = (e.canonical_name.casefold().strip(), e.type)
        if key not in merged:
            merged[key] = e
            continue
        m = merged[key]
        aliases = set(m.aliases) | set(e.aliases)
        if e.mention.casefold() != m.mention.casefold():
            aliases.add(e.mention)
        m.aliases = sorted(a for a in aliases if a.casefold() != m.canonical_name.casefold())
        m.signals = sorted(set(m.signals) | set(e.signals))
        if len(e.evidence) > len(m.evidence):
            m.evidence = e.evidence
    return list(merged.values())


def calibrate_confidence(entity: Entity) -> Entity:
    positive = {"gliner2", "llm_confirmado", "diccionario_institucional", "sufijo_persona_juridica", "patron_organismo_publico", "patron_entidad_financiera", "span_exactamente_validado"}
    score = sum(1 for s in set(entity.signals) if s in positive)
    if "span_no_encontrado" in entity.signals:
        entity.confidence = "BAJA"
    elif score >= 3:
        entity.confidence = "ALTA"
    elif score >= 2:
        entity.confidence = "MEDIA"
    else:
        entity.confidence = "BAJA"
    return entity
