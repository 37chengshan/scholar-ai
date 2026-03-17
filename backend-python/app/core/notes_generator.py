"""Notes generator using LiteLLM for structured reading notes.

Generates IMRaD-structured reading notes from academic papers using LLM.
Supports content truncation, regeneration with modifications, and Markdown export.
"""

import os
from typing import Dict, Any, Optional

import litellm
import structlog

logger = structlog.get_logger()

IMRAD_PROMPT_TEMPLATE = """You are an expert academic research assistant analyzing a research paper.
Generate structured reading notes in the following format.

Paper Information:
- Title: {title}
- Authors: {authors}
- Year: {year}
- Venue: {venue}

{modification_request}

Paper Content (IMRaD Structure):

INTRODUCTION:
{introduction}

METHODS:
{methods}

RESULTS:
{results}

CONCLUSION:
{conclusion}

---

Generate a structured reading note in Markdown with these sections:

## 1. Research Question & Motivation
- What problem does this paper address?
- Why is this problem important?
- What is the main research question or hypothesis?

## 2. Key Contributions & Innovation Points
- What are the main contributions of this work?
- What is novel or innovative compared to prior work?
- How does this advance the field?

## 3. Methodology
- What approach or method was used?
- What datasets or experimental setup was employed?
- What are the key technical details worth noting?

## 4. Main Results & Findings
- What are the key quantitative results?
- What significant findings were discovered?
- How do these results support the claims?

## 5. Limitations & Future Work
- What limitations did the authors acknowledge?
- What weaknesses or constraints exist?
- What future directions are suggested?

## 6. Personal Takeaways
- What are the key insights worth remembering?
- How might this be relevant to related research?
- Suggested papers or citations for further reading

Format your response in clean Markdown with proper headers and bullet points.
Be concise but comprehensive. Use academic language."""


class NotesGenerator:
    """Generate structured reading notes from academic papers using LLM."""

    def __init__(self, model: str = None):
        """
        Initialize notes generator.

        Args:
            model: LiteLLM model string (e.g., "gpt-4o-mini", "claude-3-haiku")
        """
        # Support Aliyun DashScope: openai/qwen-plus or openai/deepseek-v3
        self.model = model or os.getenv("LLM_MODEL", "openai/qwen-plus")
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.max_content_length = 15000  # Character limit to avoid context overflow
        self.max_tokens = 2000
        self.temperature = 0.3

    def _truncate_content(self, content: str) -> str:
        """Truncate content to fit context window."""
        if len(content) <= self.max_content_length:
            return content
        return content[:self.max_content_length] + "\n\n[Content truncated due to length...]"

    def _prepare_imrad_content(self, imrad_structure: Dict[str, Any]) -> Dict[str, str]:
        """Prepare IMRaD sections for prompt."""
        sections = {}
        for section in ["introduction", "methods", "results", "conclusion"]:
            content = ""
            if isinstance(imrad_structure, dict):
                section_data = imrad_structure.get(section, {})
                if isinstance(section_data, dict):
                    content = section_data.get("content", "")
                else:
                    content = str(section_data)
            sections[section] = self._truncate_content(content)
        return sections

    async def generate_notes(
        self,
        paper_metadata: Dict[str, Any],
        imrad_structure: Dict[str, Any]
    ) -> str:
        """
        Generate reading notes from paper content.

        Args:
            paper_metadata: Dict with title, authors, year, venue, etc.
            imrad_structure: Dict with introduction, methods, results, conclusion

        Returns:
            Markdown formatted reading notes
        """
        imrad_content = self._prepare_imrad_content(imrad_structure)

        prompt = IMRAD_PROMPT_TEMPLATE.format(
            title=paper_metadata.get("title", "Unknown"),
            authors=", ".join(paper_metadata.get("authors", [])),
            year=paper_metadata.get("year", ""),
            venue=paper_metadata.get("venue", ""),
            modification_request="",
            introduction=imrad_content["introduction"],
            methods=imrad_content["methods"],
            results=imrad_content["results"],
            conclusion=imrad_content["conclusion"]
        )

        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=60  # 60 second timeout
            )

            notes = response.choices[0].message.content
            logger.info(
                "Generated reading notes",
                paper_title=paper_metadata.get("title"),
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else None
            )
            return notes

        except Exception as e:
            logger.error(
                "Failed to generate notes",
                error=str(e),
                paper_title=paper_metadata.get("title")
            )
            raise

    async def regenerate_notes(
        self,
        paper_metadata: Dict[str, Any],
        imrad_structure: Dict[str, Any],
        modification_request: str
    ) -> str:
        """
        Regenerate notes with user modification request.

        Args:
            paper_metadata: Dict with title, authors, year, venue, etc.
            imrad_structure: Dict with introduction, methods, results, conclusion
            modification_request: User's specific requirements (e.g., "Focus on methodology")

        Returns:
            New markdown notes
        """
        imrad_content = self._prepare_imrad_content(imrad_structure)

        # Add modification context to prompt
        modification_section = f"""\n---\nUSER MODIFICATION REQUEST:\n{modification_request}\n---\n"""

        prompt = IMRAD_PROMPT_TEMPLATE.format(
            title=paper_metadata.get("title", "Unknown"),
            authors=", ".join(paper_metadata.get("authors", [])),
            year=paper_metadata.get("year", ""),
            venue=paper_metadata.get("venue", ""),
            modification_request=modification_section,
            introduction=imrad_content["introduction"],
            methods=imrad_content["methods"],
            results=imrad_content["results"],
            conclusion=imrad_content["conclusion"]
        )

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=60
            )

            notes = response.choices[0].message.content
            logger.info(
                "Regenerated reading notes",
                paper_title=paper_metadata.get("title"),
                model=self.model,
                modification_request=modification_request
            )
            return notes

        except Exception as e:
            logger.error(
                "Failed to regenerate notes",
                error=str(e),
                paper_title=paper_metadata.get("title"),
                modification_request=modification_request
            )
            raise

    def export_to_markdown(
        self,
        notes: str,
        paper_metadata: Dict[str, Any]
    ) -> str:
        """
        Export notes as standalone Markdown with metadata header.

        Args:
            notes: Generated notes content
            paper_metadata: Paper metadata for header

        Returns:
            Complete Markdown document
        """
        header = f"""# Reading Notes: {paper_metadata.get('title', 'Unknown')}

**Authors:** {', '.join(paper_metadata.get('authors', []))}
**Year:** {paper_metadata.get('year', 'N/A')}
**Venue:** {paper_metadata.get('venue', 'N/A')}
**Generated:** {paper_metadata.get('generated_at', 'N/A')}

---

"""
        return header + notes
