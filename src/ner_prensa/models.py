from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

EntityType = Literal[
    "PERSONA_NATURAL",
    "PERSONA_JURIDICA",
    "ORGANISMO_PUBLICO",
    "INSTITUCION_FINANCIERA",
    "ORGANIZACION_INTERNACIONAL",
    "ORGANIZACION_SIN_FINES_DE_LUCRO",
    "PARTIDO_POLITICO",
    "MEDIO_COMUNICACION",
    "TRIBUNAL",
    "FISCALIA",
    "LUGAR",
    "PAIS",
    "REGION",
    "CIUDAD_COMUNA",
    "LEY_NORMA",
    "DELITO",
    "PRODUCTO_FINANCIERO",
    "CRIPTOACTIVO",
    "OTRA_ORGANIZACION",
    "OTRO",
]

Confidence = Literal["ALTA", "MEDIA", "BAJA"]


class Article(BaseModel):
    url: str
    title: str = ""
    author: str = ""
    date: str = ""
    site_name: str = ""
    text: str


class Entity(BaseModel):
    mention: str
    canonical_name: str
    type: EntityType
    subtype: str = ""
    role: str = ""
    evidence: str = ""
    aliases: list[str] = Field(default_factory=list)
    start_char: int = -1
    end_char: int = -1
    confidence: Confidence = "MEDIA"
    signals: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    source: str
    relation: str
    target: str
    evidence: str = ""
    confidence: Confidence = "MEDIA"


class AnalysisResult(BaseModel):
    article: Article
    entities: list[Entity]
    relations: list[Relation] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    engine: dict[str, str | bool] = Field(default_factory=dict)
