"""
Confidence Scoring Service

Computes how confident the intent classification is for a given submission.
Score range: 0.0 (no confidence) to 1.0 (maximum confidence).

Approach:
1. Apply fast keyword-booster rules (no API call)
2. If keyword rules give high-confidence result (>= 0.85), return immediately
3. Otherwise, call GPT-4o for nuanced scoring
"""
import json
import asyncio
import re
import structlog
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

logger = structlog.get_logger(__name__)

# ─── Keyword Booster Rules ────────────────────────────────────────────────────
# Format: { intent: { "positive": [keywords], "negative": [keywords] } }
# Positive keywords increase score; negative keywords decrease it.

KEYWORD_RULES: dict[str, dict[str, list[str]]] = {
    "sales_lead": {
        "positive": [
            "lead", "prospect", "demo", "trial", "pricing", "quote", "contract",
            "enterprise", "deal", "opportunity", "sales", "revenue", "customer",
            "interested in", "want to buy", "upgrade plan",
        ],
        "negative": ["bug", "error", "crash", "invoice", "payment", "broken"],
    },
    "customer_support": {
        "positive": [
            "bug", "error", "broken", "not working", "issue", "problem", "help",
            "support", "crash", "404", "500", "ticket", "refund", "complaint",
            "can't access", "login failed", "account locked",
        ],
        "negative": ["lead", "prospect", "demo", "invoice", "board"],
    },
    "invoice_processing": {
        "positive": [
            "invoice", "receipt", "payment", "billing", "due", "amount owed",
            "total", "subtotal", "tax", "net 30", "net 60", "purchase order",
            "po#", "vendor", "supplier", "accounts payable",
        ],
        "negative": ["bug", "lead", "board", "prospect", "error"],
    },
    "executive_summary": {
        "positive": [
            "board", "executive", "summary", "quarterly", "annual", "strategic",
            "kpi", "metrics", "performance", "market share", "roadmap",
            "investor", "stakeholder", "ceo", "cfo", "cto",
        ],
        "negative": ["bug", "error", "invoice", "lead", "broken"],
    },
}

SCORING_SYSTEM_PROMPT = """You are evaluating how well a piece of content matches a given intent category.

Score the confidence that the content's intent is "{intent}" on a scale from 0.0 to 1.0:
- 0.0 = The content has no relation to this intent at all
- 0.3 = Weak signal, could be this intent but unclear
- 0.5 = Moderate signal, about 50/50 chance this is the correct intent
- 0.7 = Strong signal, content likely matches this intent
- 0.9 = Very strong signal, content clearly matches this intent
- 1.0 = Perfect match, unambiguous

Return ONLY this JSON (no markdown, no explanation):
{{
  "score": <float between 0.0 and 1.0>,
  "explanation": "<one sentence>"
}}"""


# ─── Keyword Pre-Pass ─────────────────────────────────────────────────────────

def _keyword_score(content: str, intent: str) -> Optional[float]:
    """
    Fast keyword-based pre-scoring. Returns a score if keyword evidence is strong
    enough (>= 0.85 or <= 0.15), otherwise returns None to trigger GPT-4o.
    """
    rules = KEYWORD_RULES.get(intent)
    if not rules:
        return None

    content_lower = content.lower()
    positive_hits = sum(
        1 for kw in rules["positive"] if kw in content_lower
    )
    negative_hits = sum(
        1 for kw in rules["negative"] if kw in content_lower
    )

    total_positive = len(rules["positive"])

    if positive_hits >= 4 and negative_hits == 0:
        # Strong positive signal — high confidence
        score = min(0.9, 0.6 + (positive_hits / total_positive) * 0.4)
        logger.debug("keyword_high_confidence", intent=intent, score=score)
        return score

    if positive_hits == 0 and negative_hits >= 2:
        # Strong negative signal — low confidence
        logger.debug("keyword_low_confidence", intent=intent)
        return 0.1

    return None  # Inconclusive — use GPT-4o


# ─── Main Service ─────────────────────────────────────────────────────────────

async def compute_confidence(
    content: str,
    intent: str,
    file_context: Optional[str] = None,
) -> float:
    """
    Compute confidence score for the given intent classification.

    Args:
        content:      User's text submission
        intent:       Detected intent from intent_detection service
        file_context: Optional OCR text from attached document

    Returns:
        Float in range [0.0, 1.0]
    """
    if intent == "unknown":
        return 0.0

    full_text = content
    if file_context:
        full_text = f"{content}\n\n--- Document Content ---\n{file_context}"

    # 1. Keyword pre-pass (cheap, no API)
    keyword_result = _keyword_score(full_text, intent)
    if keyword_result is not None:
        logger.info(
            "confidence_from_keywords",
            intent=intent,
            score=keyword_result,
        )
        return keyword_result

    # 2. GPT-4o scoring
    try:
        score = await _gpt4o_score(full_text, intent)
        logger.info(
            "confidence_from_gpt4o",
            intent=intent,
            score=score,
        )
        return score
    except Exception as exc:
        logger.warning(
            "confidence_scoring_failed",
            intent=intent,
            error=str(exc),
        )
        # Conservative fallback: moderate confidence
        return 0.5


async def _gpt4o_score(text: str, intent: str) -> float:
    """Call GPT-4o to score the confidence."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY,  # type: ignore[call-arg]
        request_timeout=10,  # type: ignore[call-arg]
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    truncated = text[:4000]
    system = SCORING_SYSTEM_PROMPT.format(intent=intent)

    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content=f"Content to score:\n\n{truncated}\n\nIntent to evaluate: {intent}"
        ),
    ]

    response = await asyncio.wait_for(
        llm.ainvoke(messages),
        timeout=10.0,
    )

    if not isinstance(response.content, str):
        return 0.5

    return _parse_score(response.content)


def _parse_score(raw: str) -> float:
    """Parse score from GPT-4o response. Returns 0.5 on parse failure."""
    try:
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.5))
        # Clamp to valid range
        return max(0.0, min(1.0, score))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("score_parse_failed", error=str(exc), raw=raw[:100])
        return 0.5
