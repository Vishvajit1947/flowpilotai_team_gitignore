# 017 – Intent Detection

## Objective
Implement the intent detection service that uses OpenAI GPT-4o to classify the intent of a user's inbox submission into one of the predefined categories (sales, support, finance, executive, or unknown) by sending a structured prompt and parsing the JSON response.

## Scope
- `app/services/intent_detection.py` — GPT-4o based intent classifier
- Structured prompt template
- JSON response parsing with fallback
- Supported intents: `sales_lead`, `customer_support`, `invoice_processing`, `executive_summary`, `unknown`
- Integration with the agent routing pipeline

## Out of Scope
- Confidence scoring (018 — separate service)
- Agent routing (019)
- LangGraph workflow (025)

## Functional Requirements
1. Accept `content` (text string) and optional `file_context` (OCR text from a document).
2. Return detected `intent` (string from allowed set) and `raw_response` for debugging.
3. Use GPT-4o with `response_format={"type":"json_object"}` for reliable JSON output.
4. If GPT-4o call fails or returns invalid JSON, return `intent = "unknown"`.
5. Calls must complete within 15 seconds (enforced by timeout).
6. Cache results for identical content (in-memory LRU cache with 256 entries).

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with model `gpt-4o`
- Pydantic output parsing (`JsonOutputParser`)
- `functools.lru_cache` not suitable for async — use `cachetools.TTLCache` with async lock
- Structured system prompt stored as a constant
- `OPENAI_API_KEY` from settings

## Folder Structure
```
backend/
└── app/
    └── services/
        └── intent_detection.py
```

## Files To Create

### `app/services/intent_detection.py`
```python
"""
Intent Detection Service

Uses GPT-4o to classify inbox submission intent into predefined categories.
"""
import json
import asyncio
import structlog
from typing import Optional
from cachetools import TTLCache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

logger = structlog.get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

ALLOWED_INTENTS = {
    "sales_lead",
    "customer_support",
    "invoice_processing",
    "executive_summary",
    "unknown",
}

SYSTEM_PROMPT = """You are an AI assistant that classifies business messages and documents
into intent categories. Analyze the given content and return ONLY a JSON object.

Available intent categories:
- "sales_lead": Messages about new prospects, sales opportunities, demos, pricing inquiries, or deal negotiations
- "customer_support": Bug reports, feature requests, user complaints, account issues, or technical problems
- "invoice_processing": Invoices, receipts, payment requests, financial documents, or billing disputes
- "executive_summary": Board updates, strategic reports, market analysis, KPI reviews, or high-level business summaries
- "unknown": Does not clearly fit any of the above categories

Return ONLY this JSON structure (no markdown, no explanation):
{
  "intent": "<one of the five categories above>",
  "reasoning": "<brief one-sentence explanation>"
}"""

# In-memory cache: key = content hash, value = (intent, reasoning)
# TTL = 1 hour, max 256 entries
_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)
_cache_lock = asyncio.Lock()


# ─── Service ──────────────────────────────────────────────────────────────────

class IntentDetectionResult:
    def __init__(self, intent: str, reasoning: str, from_cache: bool = False):
        self.intent = intent
        self.reasoning = reasoning
        self.from_cache = from_cache


async def detect_intent(
    content: str,
    file_context: Optional[str] = None,
) -> IntentDetectionResult:
    """
    Detect the intent of the given content using GPT-4o.

    Args:
        content:      The user's text submission
        file_context: Optional OCR-extracted text from an attached document

    Returns:
        IntentDetectionResult with intent and reasoning
    """
    # Build full text for classification
    full_text = content
    if file_context:
        full_text = f"{content}\n\n--- Attached Document ---\n{file_context}"

    # Cache key based on content hash
    import hashlib
    cache_key = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

    async with _cache_lock:
        if cache_key in _cache:
            cached = _cache[cache_key]
            logger.debug("intent_cache_hit", cache_key=cache_key[:8])
            return IntentDetectionResult(
                intent=cached["intent"],
                reasoning=cached["reasoning"],
                from_cache=True,
            )

    # Call GPT-4o
    try:
        result = await _call_gpt4o(full_text)
    except Exception as exc:
        logger.warning(
            "intent_detection_failed",
            error=str(exc),
            content_length=len(content),
        )
        return IntentDetectionResult(
            intent="unknown",
            reasoning="Intent detection service unavailable",
        )

    # Store in cache
    async with _cache_lock:
        _cache[cache_key] = {"intent": result.intent, "reasoning": result.reasoning}

    logger.info(
        "intent_detected",
        intent=result.intent,
        content_length=len(content),
    )
    return result


async def _call_gpt4o(text: str) -> IntentDetectionResult:
    """Internal: call GPT-4o with timeout and parse response."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=15,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    # Truncate to ~6000 chars to stay within token limits
    truncated = text[:6000]
    if len(text) > 6000:
        truncated += "\n[Content truncated for analysis]"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Classify this content:\n\n{truncated}"),
    ]

    response = await asyncio.wait_for(
        llm.ainvoke(messages),
        timeout=15.0,
    )

    return _parse_response(response.content)


def _parse_response(raw: str) -> IntentDetectionResult:
    """Parse GPT-4o JSON response. Returns 'unknown' on any parse failure."""
    try:
        parsed = json.loads(raw)
        intent = parsed.get("intent", "unknown")
        reasoning = parsed.get("reasoning", "")

        if intent not in ALLOWED_INTENTS:
            logger.warning("intent_invalid_value", value=intent)
            intent = "unknown"

        return IntentDetectionResult(intent=intent, reasoning=reasoning)
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("intent_parse_failed", error=str(exc), raw=raw[:200])
        return IntentDetectionResult(
            intent="unknown",
            reasoning="Failed to parse intent response",
        )
```

### Add to `requirements.txt`
```
cachetools==5.3.3
```

## Existing Files To Modify
None beyond requirements.

## API Contracts
This is an internal service — not an HTTP endpoint. Called by the agent router (019).

### Function Signature
```python
async def detect_intent(
    content: str,
    file_context: Optional[str] = None,
) -> IntentDetectionResult:
    ...
```

### Return Value
```python
@dataclass
class IntentDetectionResult:
    intent: str          # one of ALLOWED_INTENTS
    reasoning: str       # one-sentence explanation
    from_cache: bool     # True if returned from cache
```

## Request Examples
```python
# Usage
from app.services.intent_detection import detect_intent

result = await detect_intent(
    content="We have a new enterprise prospect from Acme Corp, they want a demo next week.",
    file_context=None,
)
# result.intent == "sales_lead"
# result.reasoning == "Message discusses a new enterprise prospect and demo request."
```

## Response Examples
```python
# Sales lead
IntentDetectionResult(intent="sales_lead", reasoning="Message is about a new enterprise prospect requesting a product demo.", from_cache=False)

# Invoice
IntentDetectionResult(intent="invoice_processing", reasoning="Document contains invoice line items and payment terms.", from_cache=False)

# Unknown (fallback)
IntentDetectionResult(intent="unknown", reasoning="Intent detection service unavailable", from_cache=False)
```

## Database Tables
Not applicable — no direct DB interaction.

## Business Logic
1. Content is truncated to 6000 characters before sending to GPT-4o (max token safety).
2. If file context is provided, it's appended after the user's text with a separator.
3. Temperature is set to `0.0` for deterministic, consistent results.
4. `response_format={"type":"json_object"}` ensures GPT-4o returns valid JSON.
5. Cache key is SHA-256 of the full text (content + file_context combined).
6. Cache TTL is 1 hour — same content can be re-submitted after 1 hour and gets a fresh classification.
7. `asyncio.wait_for` wraps the OpenAI call to enforce 15-second timeout.

## Validation Rules
- `intent` in response must be one of the 5 allowed values; invalid values are replaced with `"unknown"`.
- `content` truncated at 6000 chars to prevent token overflow.

## Error Handling
| Scenario | Behavior |
|----------|----------|
| OpenAI API unreachable | Returns `intent="unknown"` with log warning |
| Timeout (>15s) | `asyncio.TimeoutError` caught → `intent="unknown"` |
| Invalid JSON response | `_parse_response` returns `intent="unknown"` |
| Invalid intent value | Replaced with `"unknown"` |
| Cache lock contention | Lock is async — minimal blocking |

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
In-memory `TTLCache(maxsize=256, ttl=3600)` — not persistent across restarts.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Empty `content` string: should not reach this service (validated at API level in 016), but if it does, GPT-4o will return `"unknown"`.
- `file_context` only (no text content): truncation still applies; classification based solely on document text.
- Content in non-English language: GPT-4o handles multilingual input; intent classification still works.
- Network retry: no automatic retry — single attempt, fallback to `"unknown"` on failure.
- Thread safety: `TTLCache` is not thread-safe; protected by `asyncio.Lock()`.

## Test Cases
1. `detect_intent("We have a new sales lead from Acme Corp")` returns `"sales_lead"`.
2. `detect_intent("My login is broken, error 500")` returns `"customer_support"`.
3. `detect_intent("Invoice #12345 for $4500 due Nov 30")` returns `"invoice_processing"`.
4. `detect_intent("Q3 board presentation highlights")` returns `"executive_summary"`.
5. `detect_intent("What time is it in Tokyo?")` returns `"unknown"`.
6. Second call with same content returns `from_cache=True`.
7. OpenAI timeout returns `intent="unknown"` (mock timeout).
8. Invalid JSON from OpenAI returns `intent="unknown"`.
9. Intent value `"spam"` from GPT-4o is replaced with `"unknown"`.
10. Content > 6000 chars is truncated before API call.

## Acceptance Criteria
- [ ] Correctly classifies all 5 intent categories
- [ ] Returns `"unknown"` on API failure
- [ ] Caching prevents duplicate API calls for identical content
- [ ] 15-second timeout enforced
- [ ] Content truncated to 6000 chars
- [ ] Invalid intent values fall back to `"unknown"`

## Definition of Done
- All test cases pass (mock OpenAI in tests)
- No mypy errors
- `cachetools` added to `requirements.txt`
- System prompt finalized and tested against all 5 intent categories
