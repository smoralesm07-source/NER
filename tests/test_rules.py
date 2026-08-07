from ner_prensa.models import Entity
from ner_prensa.rules import deterministic_refine, reject_nonexistent, calibrate_confidence


def test_spa_is_persona_juridica():
    text = "La empresa Inversiones Los Andes SpA informó sus resultados."
    e = Entity(mention="Inversiones Los Andes SpA", canonical_name="Inversiones Los Andes SpA", type="OTRA_ORGANIZACION", signals=["gliner2"])
    e = deterministic_refine(e, text)
    e = calibrate_confidence(e)
    assert e.type == "PERSONA_JURIDICA"
    assert e.start_char >= 0
    assert e.confidence == "ALTA"


def test_uaf_dictionary():
    text = "La UAF remitió antecedentes a la Fiscalía."
    e = Entity(mention="UAF", canonical_name="UAF", type="OTRA_ORGANIZACION")
    e = deterministic_refine(e, text)
    assert e.canonical_name == "Unidad de Análisis Financiero"
    assert e.type == "ORGANISMO_PUBLICO"


def test_nonexistent_is_rejected():
    text = "Juan Pérez habló con la prensa."
    entities = [Entity(mention="Pedro Soto", canonical_name="Pedro Soto", type="PERSONA_NATURAL")]
    assert reject_nonexistent(entities, text) == []
