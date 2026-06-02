"""LLM cost circuit breaker for paper import.

Prevents runaway LLM API costs by tracking cumulative costs per paper
and interrupting when the budget is exceeded.

Budget: $0.50 per paper
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Cost budget per paper (USD)
MAX_COST_PER_PAPER = 0.50

# Estimated costs per LLM call type
COST_PER_SIMPLE_COMPLETION = 0.001  # ~$0.001 per simple completion
COST_PER_CHAT_COMPLETION = 0.002    # ~$0.002 per chat completion


class CostCircuitBreaker:
    """Tracks LLM API costs and interrupts when budget is exceeded."""

    def __init__(self, *, paper_id: str, max_cost: float = MAX_COST_PER_PAPER):
        self._paper_id = paper_id
        self._max_cost = max_cost
        self._total_cost = 0.0
        self._call_count = 0
        self._tripped = False

    @property
    def is_tripped(self) -> bool:
        """Whether the circuit breaker has been tripped."""
        return self._tripped

    @property
    def total_cost(self) -> float:
        """Total estimated cost so far."""
        return self._total_cost

    @property
    def call_count(self) -> int:
        """Number of LLM calls made."""
        return self._call_count

    def record_call(self, call_type: str = "simple") -> bool:
        """Record an LLM call and check if budget is exceeded.

        Args:
            call_type: Type of call ("simple" or "chat")

        Returns:
            True if budget is still OK, False if exceeded
        """
        if call_type == "chat":
            cost = COST_PER_CHAT_COMPLETION
        else:
            cost = COST_PER_SIMPLE_COMPLETION

        self._total_cost += cost
        self._call_count += 1

        if self._total_cost > self._max_cost:
            self._tripped = True
            logger.warning(
                "LLM cost circuit breaker tripped",
                paper_id=self._paper_id,
                total_cost=round(self._total_cost, 4),
                max_cost=self._max_cost,
                call_count=self._call_count,
            )
            return False

        return True

    def reset(self) -> None:
        """Reset the circuit breaker."""
        self._total_cost = 0.0
        self._call_count = 0
        self._tripped = False


_circuit_breakers: dict[str, CostCircuitBreaker] = {}


def get_cost_circuit_breaker(paper_id: str) -> CostCircuitBreaker:
    """Get or create a cost circuit breaker for a paper."""
    if paper_id not in _circuit_breakers:
        _circuit_breakers[paper_id] = CostCircuitBreaker(paper_id=paper_id)
    return _circuit_breakers[paper_id]


def reset_cost_circuit_breaker(paper_id: str) -> None:
    """Reset the circuit breaker for a paper."""
    if paper_id in _circuit_breakers:
        _circuit_breakers[paper_id].reset()
