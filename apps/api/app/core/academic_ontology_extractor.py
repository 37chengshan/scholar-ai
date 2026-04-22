from __future__ import annotations

import re
from typing import List

from app.core.academic_ontology_schema import AcademicEntity, AcademicRelation, PaperGraphSlice


class AcademicOntologyExtractor:
    """Lightweight extractor for Method/Task/Dataset/Metric/Baseline/Limitation."""

    METHOD_PATTERN = re.compile(r"\b(method\s+[A-Za-z0-9\-]+|[A-Z][A-Za-z0-9\-]{1,20})\b")
    DATASET_PATTERN = re.compile(r"\b(CIFAR-10|ImageNet|SQuAD|COCO|MNIST|WikiText)\b", re.IGNORECASE)
    METRIC_PATTERN = re.compile(r"\b(accuracy|f1|bleu|rouge|auc|precision|recall)\b", re.IGNORECASE)
    BASELINE_PATTERN = re.compile(r"\b(baseline\s+[A-Za-z0-9\-]+|bert|resnet|svm)\b", re.IGNORECASE)
    TASK_PATTERN = re.compile(r"\b(classification|detection|qa|question answering|summarization|translation)\b", re.IGNORECASE)

    def extract_from_text(self, paper_id: str, text: str) -> PaperGraphSlice:
        entities: List[AcademicEntity] = []
        relations: List[AcademicRelation] = []
        seen: dict[tuple[str, str], str] = {}

        def add_entity(entity_type: str, name: str) -> str:
            key = (entity_type, name.lower().strip())
            if key in seen:
                return seen[key]
            entity_id = f"{entity_type}:{len(seen) + 1}"
            entities.append(
                AcademicEntity(entity_id=entity_id, entity_type=entity_type, name=name.strip())
            )
            seen[key] = entity_id
            return entity_id

        methods = [match.group(1) for match in self.METHOD_PATTERN.finditer(text or "")][:8]
        datasets = [match.group(1) for match in self.DATASET_PATTERN.finditer(text or "")][:8]
        metrics = [match.group(1) for match in self.METRIC_PATTERN.finditer(text or "")][:8]
        baselines = [match.group(1) for match in self.BASELINE_PATTERN.finditer(text or "")][:8]
        tasks = [match.group(1) for match in self.TASK_PATTERN.finditer(text or "")][:8]

        method_ids = [add_entity("method", item) for item in methods]
        dataset_ids = [add_entity("dataset", item) for item in datasets]
        metric_ids = [add_entity("metric", item) for item in metrics]
        baseline_ids = [add_entity("baseline", item) for item in baselines]
        task_ids = [add_entity("task", item) for item in tasks]

        if "limitation" in (text or "").lower() or "failure" in (text or "").lower():
            limitation_id = add_entity("limitation", "reported limitation")
            for method_id in method_ids[:3]:
                relations.append(
                    AcademicRelation(
                        relation_id=f"rel-{len(relations) + 1}",
                        subject_id=method_id,
                        relation_type="has_limitation",
                        object_id=limitation_id,
                    )
                )

        for method_id in method_ids[:3]:
            for task_id in task_ids[:2]:
                relations.append(
                    AcademicRelation(
                        relation_id=f"rel-{len(relations) + 1}",
                        subject_id=method_id,
                        relation_type="applies_to_task",
                        object_id=task_id,
                    )
                )
            for dataset_id in dataset_ids[:2]:
                relations.append(
                    AcademicRelation(
                        relation_id=f"rel-{len(relations) + 1}",
                        subject_id=method_id,
                        relation_type="evaluated_on_dataset",
                        object_id=dataset_id,
                    )
                )
            for baseline_id in baseline_ids[:2]:
                relations.append(
                    AcademicRelation(
                        relation_id=f"rel-{len(relations) + 1}",
                        subject_id=method_id,
                        relation_type="compares_against_baseline",
                        object_id=baseline_id,
                    )
                )

        if method_ids and metric_ids and dataset_ids:
            relations.append(
                AcademicRelation(
                    relation_id=f"rel-{len(relations) + 1}",
                    subject_id=method_ids[0],
                    relation_type="improves_metric_on_dataset",
                    object_id=dataset_ids[0],
                )
            )

        return PaperGraphSlice(paper_id=paper_id, entities=entities, relations=relations)


_academic_ontology_extractor: AcademicOntologyExtractor | None = None


def get_academic_ontology_extractor() -> AcademicOntologyExtractor:
    global _academic_ontology_extractor
    if _academic_ontology_extractor is None:
        _academic_ontology_extractor = AcademicOntologyExtractor()
    return _academic_ontology_extractor
