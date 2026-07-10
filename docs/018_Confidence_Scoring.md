# 018 – Confidence Scoring

## Objective
Implement the confidence scoring service that quantifies how certain the intent detection is, using a second GPT-4o call that evaluates the content-to-intent alignment and returns a normalized score between 0.0 and 1.0.

## Scope
- `app/services/confidence_scoring.py` — confidence score calculator
- Structured GPT-4o prompt that returns a numeric score
- Score normalization and validation (clamp to [0.0, 1.0])
- Rule-based scoring adjustments for edge cases (keyword boosters)
- Integration point with agent router

## Out of Scope
- Intent detection (017)
- Agent routing (019)
- Storing scores (done in workflow 025)

## Functional Requirements
1. Accept `content` (string), `intent` (detected intent string), and optional `file_context`.
2. Return a float confidence score in range [0.0, 1.0].
3. Score < 0.4 indicates low confidence (should trigger escalation or `"unknown"` override).
4. Score ≥ 0.8 indicates high confidence (agent can proceed autonomously).
5. Scoring must complete within 10 seconds.
6. Apply keyword-based booster rules as a pre-pass before GPT-4o call to reduce API costs.

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with model `gpt-4o`
- `response_format={"type":"json_object"}` for reliable numeric output
- Pydantic model for response parsing
- Keyword booster rules in a configurable dict

## Folder Structure
```
backend/
└── app/
    └── services/
        └── confidence_scoring.py
```

## Files To Create

### `app/services/confidence_scoring.py`
```python
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
{
  "score": <float between 0.0 and 1.0>,
  "explanation": "<one sentence>"
}"""


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
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=10,
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
```

## Existing Files To Modify
None — new service only.

## API Contracts
Internal service only — no HTTP endpoint.

### Function Signature
```python
async def compute_confidence(
    content: str,
    intent: str,
    file_context: Optional[str] = None,
) -> float:
    ...
    # Returns: float in [0.0, 1.0]
```

## Request Examples
```python
from app.services.confidence_scoring import compute_confidence

# High confidence sales lead
score = await compute_confidence(
    content="We have a new enterprise lead from Acme Corp. They want a demo next Tuesday.",
    intent="sales_lead",
)
# score ≈ 0.85

# Low confidence (wrong intent)
score = await compute_confidence(
    content="We have a new enterprise lead from Acme Corp.",
    intent="invoice_processing",
)
# score ≈ 0.05
```

## Response Examples
```python
# High confidence
0.87

# Low confidence
0.12

# Fallback on error
0.5

# Unknown intent
0.0
```

## Database Tables
Not applicable.

## Business Logic
1. **Two-stage scoring**: Fast keyword check first (no API cost); GPT-4o only when keywords are inconclusive.
2. **Score of 0.0 for `"unknown"` intent**: no confidence in an unclassified message.
3. **Score < 0.4**: downstream agent router (019) should treat this as low-confidence and either return a generic response or escalate.
4. **Score ≥ 0.8**: high confidence — agent proceeds with full processing.
5. **Fallback 0.5**: on any error — neutral score that doesn't block or over-promote processing.
6. **Clamping**: final score always clamped to [0.0, 1.0] regardless of GPT-4o output.

## Validation Rules
- `intent` must be a string (one of the 5 allowed values); if `"unknown"`, returns 0.0 immediately.
- Parsed score clamped to [0.0, 1.0].
- Content truncated to 4000 chars for scoring prompt.

## Error Handling
| Scenario | Behavior |
|----------|----------|
| GPT-4o timeout (>10s) | Returns `0.5` (neutral fallback) |
| GPT-4o API error | Returns `0.5` |
| JSON parse failure | Returns `0.5` |
| Score out of range from GPT | Clamped to [0.0, 1.0] |
| Intent = "unknown" | Returns `0.0` immediately |

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
No state — pure function (aside from API calls).

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- `intent = "unknown"` → immediate `0.0` return (no API call).
- Very short content (1–2 words): keyword booster likely inconclusive; GPT-4o called; usually returns moderate score.
- Content entirely in non-English: GPT-4o handles it; keyword rules may not match (lower keyword score reliability).
- GPT-4o returns score `1.5`: clamped to `1.0`.
- GPT-4o returns score `-0.1`: clamped to `0.0`.
- `file_context` with invoice data but `intent="sales_lead"`: GPT-4o likely returns low score (0.1–0.2).

## Test Cases
1. `compute_confidence("enterprise lead demo", "sales_lead")` returns score ≥ 0.7.
2. `compute_confidence("invoice $500 due Nov 30", "invoice_processing")` returns score ≥ 0.7.
3. `compute_confidence("anything", "unknown")` returns `0.0` immediately (no API call).
4. GPT-4o timeout → returns `0.5`.
5. GPT-4o returns `{"score": 1.8}` → clamped to `1.0`.
6. GPT-4o returns invalid JSON → returns `0.5`.
7. `_keyword_score` with 4+ positive matches returns score ≥ 0.8.
8. `_keyword_score` with 0 positive + 2 negative returns `0.1`.
9. `_keyword_score` with inconclusive result returns `None`.
10. Score for sales content against `invoice_processing` intent is < 0.3.

## Acceptance Criteria
- [ ] Returns float in [0.0, 1.0] for all inputs
- [ ] `"unknown"` intent returns `0.0` without API call
- [ ] Keyword pre-pass reduces GPT-4o API calls for clear-cut cases
- [ ] 10-second timeout enforced
- [ ] Fallback to `0.5` on any error

## Definition of Done
- All test cases pass (mock OpenAI in tests)
- No mypy errors
- Keyword rules cover all 4 intent categories
- Score clamping tested at boundaries (0.0, 1.0)
