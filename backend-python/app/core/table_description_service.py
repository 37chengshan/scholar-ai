"""Table description generation service using Zhipu AI API.

Provides:
- Table description generation via Zhipu AI API (glm-4-flash model)
- Retry logic with exponential backoff
- Row threshold filtering (skip trivial tables)
- Graceful fallback on API failures
"""

from typing import Optional, List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.utils.logger import logger


class TableDescriptionService:
    """Table description service using Zhipu AI API."""

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    MODEL_NAME = "glm-4-flash"
    DEFAULT_MAX_TOKENS = 150
    DEFAULT_TEMPERATURE = 0.3

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the description service.

        Args:
            api_key: Optional Zhipu API key (defaults to settings.ZHIPU_API_KEY)
        """
        self.api_key = api_key or getattr(settings, 'ZHIPU_API_KEY', '')
        self.client = httpx.AsyncClient(timeout=30.0)

    def _build_prompt(
        self,
        caption: str,
        headers: List[str],
        sample_rows: List[Dict[str, Any]]
    ) -> str:
        """Build the table description prompt.

        Args:
            caption: Table caption or title
            headers: List of column headers
            sample_rows: List of sample row dictionaries

        Returns:
            Formatted prompt string
        """
        # Format sample rows
        rows_text = self._format_sample_rows(sample_rows)

        return f"""请用一句话简洁描述以下表格的核心内容：

表格标题：{caption}
表格列名：{', '.join(headers)}
数据示例（前3行）：
{rows_text}

描述要求：
- 一句话概括表格展示的内容
- 提及关键指标或对比维度
- 不超过100字
"""

    def _format_sample_rows(self, rows: List[Dict[str, Any]]) -> str:
        """Format sample rows for prompt.

        Args:
            rows: List of row dictionaries

        Returns:
            Formatted string representation of rows
        """
        if not rows:
            return "(无数据)"

        lines = []
        for i, row in enumerate(rows[:3], 1):  # Limit to first 3 rows
            row_str = ", ".join([f"{k}={v}" for k, v in row.items()])
            lines.append(f"  第{i}行: {row_str}")

        return "\n".join(lines)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _call_api(self, prompt: str) -> str:
        """Call Zhipu AI API with retry logic.

        Args:
            prompt: The prompt to send

        Returns:
            Generated description text

        Raises:
            Exception: If API call fails after retries
        """
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "temperature": self.DEFAULT_TEMPERATURE
        }

        response = await self.client.post(
            self.API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            raise ValueError(f"Unexpected API response: {data}")

    async def generate_description(
        self,
        caption: str,
        headers: List[str],
        sample_rows: List[Dict[str, Any]],
        min_rows: int = 2
    ) -> Optional[str]:
        """Generate a description for a table.

        Args:
            caption: Table caption or title
            headers: List of column headers
            sample_rows: List of sample row dictionaries (first few rows)
            min_rows: Minimum rows required to generate description (default 2)

        Returns:
            Description string, or None if table is too small or generation fails
        """
        # Check row threshold (D-21)
        if len(sample_rows) <= min_rows:
            logger.info(
                "Table skipped due to insufficient rows",
                row_count=len(sample_rows),
                min_rows=min_rows
            )
            return None

        try:
            prompt = self._build_prompt(caption, headers, sample_rows)

            logger.debug(
                "Generating table description",
                caption=caption[:50],
                headers_count=len(headers),
                rows_count=len(sample_rows)
            )

            description = await self._call_api(prompt)

            # Validate description
            if not description or len(description) < 5:
                logger.warning(
                    "Generated description too short, using fallback",
                    description=description,
                    fallback=caption
                )
                return caption if caption else None

            logger.info(
                "Table description generated successfully",
                description_length=len(description)
            )
            return description

        except Exception as e:
            logger.error(
                "Table description generation failed",
                error=str(e),
                fallback=caption
            )
            # Fallback: return caption only (or None if no caption)
            return caption if caption else None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_table_description_service: Optional[TableDescriptionService] = None


def get_table_description_service() -> TableDescriptionService:
    """Get or create TableDescriptionService singleton."""
    global _table_description_service
    if _table_description_service is None:
        _table_description_service = TableDescriptionService()
    return _table_description_service


async def create_table_description_service() -> TableDescriptionService:
    """Create and initialize TableDescriptionService.

    Returns:
        TableDescriptionService instance
    """
    return get_table_description_service()
