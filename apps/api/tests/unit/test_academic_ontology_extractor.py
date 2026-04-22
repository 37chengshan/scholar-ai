from app.core.academic_ontology_extractor import AcademicOntologyExtractor


def test_academic_ontology_extractor_extracts_entities_and_relations() -> None:
    extractor = AcademicOntologyExtractor()
    text = (
        "Method Alpha improves accuracy on SQuAD for question answering tasks. "
        "It is evaluated on SQuAD and compared against baseline BERT. "
        "A limitation is failure under low-light conditions."
    )

    graph_slice = extractor.extract_from_text("paper-1", text)
    entity_types = {entity.entity_type for entity in graph_slice.entities}
    relation_types = {relation.relation_type for relation in graph_slice.relations}

    assert entity_types >= {"method", "dataset", "metric", "baseline", "task", "limitation"}
    assert relation_types >= {
        "applies_to_task",
        "evaluated_on_dataset",
        "compares_against_baseline",
        "has_limitation",
        "improves_metric_on_dataset",
    }
