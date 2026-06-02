"""NLI (Natural Language Inference) verifier for claim verification.

Uses ONNX Runtime with cross-encoder/nli-deberta-v3-base for entailment checking.
Degrades gracefully to lexical-only verification when model is unavailable.

Resource constraints:
- max_concurrent_inference: 4
- inference_timeout: 2s
- memory_budget: ~150MB (ONNX quantized)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()

# Resource constraints
MAX_CONCURRENT_INFERENCE = 4
INFERENCE_TIMEOUT_SECONDS = 2.0

# NLI labels
LABEL_ENTAILMENT = "entailment"
LABEL_CONTRADICTION = "contradiction"
LABEL_NEUTRAL = "neutral"


@dataclass(frozen=True)
class NLIResult:
    """Result of NLI verification."""
    entailment: float
    contradiction: float
    neutral: float
    label: str
    degraded: bool = False
    inference_ms: float = 0.0

    @property
    def is_entailed(self) -> bool:
        return self.entailment > 0.6

    @property
    def is_contradicted(self) -> bool:
        return self.contradiction > 0.6


class NLIVerifier:
    """NLI verifier using ONNX Runtime for entailment checking.

    Lazy-loads the model on first call. Falls back to degraded mode
    if the model cannot be loaded.
    """

    def __init__(self):
        self._session: Any = None
        self._tokenizer: Any = None
        self._loaded = False
        self._load_failed = False
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_INFERENCE)

    def _load_model(self) -> bool:
        """Lazy load the ONNX model. Returns True if successful."""
        if self._loaded:
            return True
        if self._load_failed:
            return False

        try:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer

            model_name = "cross-encoder/nli-deberta-v3-base"
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._session = ORTModelForSequenceClassification.from_pretrained(
                model_name,
                export=True,
            )
            self._loaded = True
            logger.info("NLI model loaded successfully", model=model_name)
            return True
        except Exception as exc:
            self._load_failed = True
            logger.warning(
                "NLI model failed to load, degrading to lexical-only",
                error=str(exc),
            )
            return False

    def _degraded_result(self) -> NLIResult:
        """Return a degraded result when model is unavailable."""
        return NLIResult(
            entailment=0.0,
            contradiction=0.0,
            neutral=1.0,
            label=LABEL_NEUTRAL,
            degraded=True,
        )

    async def verify(self, claim: str, evidence: str) -> NLIResult:
        """Verify a claim against evidence using NLI.

        Args:
            claim: The claim text to verify
            evidence: The evidence text to verify against

        Returns:
            NLIResult with entailment/contradiction/neutral probabilities
        """
        if not claim.strip() or not evidence.strip():
            return self._degraded_result()

        if not self._load_model():
            return self._degraded_result()

        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    self._run_inference(claim, evidence),
                    timeout=INFERENCE_TIMEOUT_SECONDS,
                )
                return result
            except asyncio.TimeoutError:
                logger.warning("NLI inference timed out", timeout=INFERENCE_TIMEOUT_SECONDS)
                return self._degraded_result()
            except Exception as exc:
                logger.warning("NLI inference failed", error=str(exc))
                return self._degraded_result()

    async def _run_inference(self, claim: str, evidence: str) -> NLIResult:
        """Run NLI inference (runs in thread pool to avoid blocking)."""
        start = time.monotonic()

        def _predict():
            inputs = self._tokenizer(
                claim,
                evidence,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )
            outputs = self._session(**inputs)
            logits = outputs.logits.detach().cpu().numpy()[0]

            # Convert logits to probabilities
            import numpy as np
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()

            return {
                "contradiction": float(probs[0]),
                "neutral": float(probs[1]),
                "entailment": float(probs[2]),
            }

        loop = asyncio.get_event_loop()
        probs = await loop.run_in_executor(None, _predict)

        # Determine label
        label = LABEL_NEUTRAL
        max_prob = max(probs.values())
        if max_prob == probs["entailment"]:
            label = LABEL_ENTAILMENT
        elif max_prob == probs["contradiction"]:
            label = LABEL_CONTRADICTION

        inference_ms = (time.monotonic() - start) * 1000

        return NLIResult(
            entailment=probs["entailment"],
            contradiction=probs["contradiction"],
            neutral=probs["neutral"],
            label=label,
            degraded=False,
            inference_ms=inference_ms,
        )


_nli_verifier: NLIVerifier | None = None


def get_nli_verifier() -> NLIVerifier:
    """Get or create NLI verifier singleton."""
    global _nli_verifier
    if _nli_verifier is None:
        _nli_verifier = NLIVerifier()
    return _nli_verifier
