"""Entity extraction and alignment service.

Provides:
- LLM-based entity extraction from academic paper text
- Hybrid entity alignment (exact match + LLM similarity)
- Methods, datasets, metrics, and venues identification

Entity types:
- Method: Research methods, algorithms, architectures (e.g., "Transformer", "YOLO")
- Dataset: Benchmark datasets (e.g., "ImageNet", "COCO")
- Metric: Evaluation metrics (e.g., "mAP@0.5", "F1-score")
- Venue: Publication venues (e.g., "CVPR", "Nature")
"""

import os
from typing import Dict, List, Optional, Any

import litellm
import structlog

from app.core.neo4j_service import Neo4jService

logger = structlog.get_logger()


EXTRACTION_PROMPT = """Extract academic entities from this paper text.

Return a JSON object with these keys:
- methods: list of {{name: str, context: str, variants: list[str]}}
  * Research methods, algorithms, architectures, approaches
  * Example: [{{"name": "Transformer", "context": "We use the Transformer architecture...", "variants": ["Attention mechanism"]}}]
- datasets: list of {{name: str, context: str, variants: list[str]}}
  * Benchmark datasets, corpora, training data
  * Example: [{{"name": "ImageNet", "context": "trained on ImageNet-1K", "variants": ["ILSVRC"]}}]
- metrics: list of {{name: str, context: str, variants: list[str]}}
  * Evaluation metrics, performance measures
  * Example: [{{"name": "mAP@0.5", "context": "achieved 45.2 mAP", "variants": ["mean Average Precision"]}}]
- venues: list of {{name: str, type: str}}
  * Publication venues (conferences, journals, workshops)
  * Example: [{{"name": "CVPR", "type": "conference"}}]

Rules:
1. Include only explicitly mentioned entities
2. Capture abbreviations and full names as variants
3. Include brief context for each entity (1 sentence)
4. For venues, use type: "conference", "journal", or "workshop"

Text: {text}
JSON:"""

# Alias for backward compatibility with tests
ENTITY_EXTRACTION_PROMPT = EXTRACTION_PROMPT


ENTITY_SAME_CHECK_PROMPT = """Determine if these two entity names refer to the same academic concept.

Entity 1: {name1}
Entity 2: {name2}

Consider:
- Full names vs abbreviations (e.g., "You Only Look Once" = "YOLO")
- Different capitalizations (e.g., "imagenet" = "ImageNet")
- Version numbers (e.g., "ResNet" vs "ResNet-50" are same family but different specifics)
- Same concept, different descriptions

Answer only "yes" or "no".

Same entity? """


class EntityExtractor:
    """Extract academic entities from paper text using LLM."""

    def __init__(
        self,
        model: str = None,
        max_text_length: int = 8000
    ):
        """
        Initialize entity extractor.

        Args:
            model: LiteLLM model string for extraction (defaults to LLM_MODEL env var)
            max_text_length: Maximum text length to send to LLM
        """
        self.model = model or os.getenv("LLM_MODEL", "openai/qwen-plus")
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.max_text_length = max_text_length

    def _truncate_text(self, text: str, max_length: int = None) -> str:
        """Truncate text to fit context window.

        Args:
            text: Input text
            max_length: Optional max length override

        Returns:
            Truncated text
        """
        limit = max_length if max_length is not None else self.max_text_length
        if len(text) <= limit:
            return text
        return text[:limit] + "\n\n[Content truncated due to length...]"

    async def extract(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extract entities from paper text using LLM.

        Args:
            text: Paper text content

        Returns:
            Dict with keys: methods, datasets, metrics, venues (all lists)
            Returns empty dict with all keys on error (graceful degradation)
        """
        truncated = self._truncate_text(text)

        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=truncated)}],
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=30
            )

            content = response.choices[0].message.content
            entities = self._parse_response(content)

            # Log results
            total = sum(len(v) for v in entities.values())
            logger.info(
                "Entity extraction complete",
                total_entities=total,
                methods=len(entities.get("methods", [])),
                datasets=len(entities.get("datasets", [])),
                metrics=len(entities.get("metrics", [])),
                venues=len(entities.get("venues", []))
            )

            return entities

        except Exception as e:
            logger.error("Entity extraction failed", error=str(e))
            return {"methods": [], "datasets": [], "metrics": [], "venues": []}

    def _parse_response(self, content: str) -> Dict[str, List[Dict]]:
        """Parse and validate LLM response.

        Args:
            content: JSON string from LLM

        Returns:
            Validated entity dict with all required keys
        """
        import json

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON", content=content[:200])
            return {"methods": [], "datasets": [], "metrics": [], "venues": []}

        # Ensure all keys exist and are lists
        result = {}
        for key in ["methods", "datasets", "metrics", "venues"]:
            value = data.get(key, [])
            if not isinstance(value, list):
                logger.warning(f"Entity key {key} is not a list, using empty list")
                value = []
            result[key] = value

        return result


class EntityAligner:
    """Align entities with existing graph nodes using hybrid strategy."""

    def __init__(
        self,
        neo4j_service: Optional[Neo4jService] = None,
        llm_model: str = "openai/qwen-plus"
    ):
        """
        Initialize entity aligner.

        Args:
            neo4j_service: Neo4jService instance for database queries
            llm_model: LiteLLM model string for similarity checks
        """
        self.neo4j = neo4j_service or Neo4jService()
        self.llm_model = llm_model
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")

    def _get_neo4j_session(self):
        """Get Neo4j session for testing purposes.

        Returns:
            Neo4j driver session
        """
        return self.neo4j.driver.session()

    async def align_entity(self, name: str, entity_type: str) -> Optional[str]:
        """
        Align entity name with existing graph node.

        Two-phase strategy:
        1. Exact match (case-insensitive) on canonical_name
        2. LLM similarity check for variants (abbreviations, full names)

        Args:
            name: Entity name to align
            entity_type: Type of entity (Method, Dataset, Metric, Venue)

        Returns:
            Existing entity ID if match found, None otherwise
            (Caller should create new entity if None returned)
        """
        # Phase 1: Exact match (case-insensitive)
        existing_id = await self._find_exact_match(name, entity_type)
        if existing_id:
            logger.debug("Exact match found", name=name, entity_id=existing_id)
            return existing_id

        # Phase 2: LLM similarity for variants
        candidates = await self._find_similar_candidates(name, entity_type, limit=5)
        for candidate in candidates:
            is_same = await self._llm_check_same_entity(name, candidate["name"])
            if is_same:
                logger.info(
                    "LLM alignment match found",
                    name=name,
                    matched_to=candidate["name"],
                    entity_id=candidate["id"]
                )
                return candidate["id"]

        # No match found
        logger.debug("No alignment match found", name=name, entity_type=entity_type)
        return None

    async def _find_exact_match(self, name: str, entity_type: str) -> Optional[str]:
        """Find exact match by canonical name (lowercase).

        Args:
            name: Entity name to match
            entity_type: Node label (Method, Dataset, Metric, Venue)

        Returns:
            Entity ID if found, None otherwise
        """
        try:
            async with self.neo4j.driver.session() as session:
                result = await session.run(
                    f"""MATCH (n:{entity_type})
                        WHERE n.canonical_name = toLower($name)
                        RETURN n.id as id
                        LIMIT 1""",
                    name=name
                )
                record = await result.single()
                return record["id"] if record else None
        except Exception as e:
            logger.error("Exact match query failed", error=str(e), name=name)
            return None

    async def _find_similar_candidates(
        self,
        name: str,
        entity_type: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """Find similar entity candidates using partial string matching.

        Args:
            name: Entity name to search for
            entity_type: Node label (Method, Dataset, Metric, Venue)
            limit: Maximum candidates to return

        Returns:
            List of {id, name} dicts for potential matches
        """
        try:
            # Extract parts of the name for partial matching
            name_lower = name.lower()
            parts = [p for p in name_lower.split() if len(p) > 2]

            async with self.neo4j.driver.session() as session:
                # Try matching on any word in the name
                result = await session.run(
                    f"""MATCH (n:{entity_type})
                        WHERE any(part IN $parts WHERE n.name CONTAINS part)
                           OR n.name CONTAINS $name_part
                        RETURN n.id as id, n.name as name
                        LIMIT $limit""",
                    parts=parts,
                    name_part=name_lower[:10],  # First 10 chars for partial match
                    limit=limit
                )
                records = await result.data()
                return [dict(r) for r in records]
        except Exception as e:
            logger.error("Similar candidates query failed", error=str(e), name=name)
            return []

    async def _llm_check_same_entity(self, name1: str, name2: str) -> bool:
        """Use LLM to check if two entity names refer to same concept.

        Args:
            name1: First entity name
            name2: Second entity name

        Returns:
            True if LLM determines they are the same entity
        """
        try:
            response = await litellm.acompletion(
                model=self.llm_model,
                api_base=self.api_base,
                messages=[{
                    "role": "user",
                    "content": ENTITY_SAME_CHECK_PROMPT.format(name1=name1, name2=name2)
                }],
                temperature=0,  # Deterministic
                max_tokens=10,
                timeout=10
            )

            answer = response.choices[0].message.content.strip().lower()
            is_same = "yes" in answer and "no" not in answer

            logger.debug(
                "LLM same-entity check",
                name1=name1,
                name2=name2,
                answer=answer,
                is_same=is_same
            )

            return is_same

        except Exception as e:
            logger.error("LLM same-entity check failed", error=str(e), name1=name1, name2=name2)
            return False

    async def align_entities_batch(self, entities: List[Dict]) -> List[str]:
        """Align multiple entities in batch.

        Args:
            entities: List of {name, type} dicts

        Returns:
            List of aligned entity IDs
        """
        results = []
        for entity in entities:
            entity_id = await self.align_entity(entity["name"], entity["type"])
            results.append(entity_id)
        return results

    async def close(self):
        """Close Neo4j connection."""
        await self.neo4j.close()
