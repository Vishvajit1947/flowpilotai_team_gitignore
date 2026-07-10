# 023 – Finance Agent

## Objective
Implement the Finance Agent — a LangGraph node that processes financial documents and invoice-related submissions using GPT-4o, extracts structured invoice/payment data, validates amounts, identifies anomalies, and generates an accounts payable action plan.

## Scope
- `app/agents/finance_agent.py` — finance agent node function
- Invoice data extraction: vendor, amounts, line items, due date, payment terms
- Currency normalization to USD
- Anomaly detection: duplicate invoices, missing fields, unusual amounts
- Payment prioritization based on due date and amount
- Integration with OCR output from `file_text`

## Out of Scope
- Actual payment processing (not in v1)
- Accounting system integration
- Tax calculation

## Functional Requirements
1. Extract structured invoice data: vendor name, invoice number, total amount, due date, line items.
2. Detect anomalies: missing required fields, duplicate invoice number indicators, amounts out of normal range.
3. Generate payment recommendation: `approve`, `hold`, `review`.
4. Calculate days until due and classify urgency.
5. Extract all line items as a list of `{description, quantity, unit_price, total}`.
6. Complete within 25 seconds (OCR documents may be longer).

## Technical Requirements
- `langchain-openai` `ChatOpenAI` with `gpt-4o`
- `response_format={"type":"json_object"}`
- Handles both text submissions and OCR-extracted invoice text
- Currency parsing: handles `$`, `€`, `£`, `¥` — normalizes to numeric float

## Folder Structure
```
backend/
└── app/
    └── agents/
        └── finance_agent.py
```

## Files To Create

### `app/agents/finance_agent.py`
```python
"""
Finance Agent

Processes invoice and financial document submissions.
Extracts structured data, detects anomalies, and recommends payment actions.
"""
import json
import asyncio
import structlog
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState, add_step
from app.agents.types import AgentResponse
from app.core.config import settings
from app.db.models.inbox import AgentType

logger = structlog.get_logger(__name__)

FINANCE_SYSTEM_PROMPT = """You are an expert accounts payable AI assistant.
Analyze the financial document or invoice description and extract structured data.

Return ONLY this JSON (no markdown):
{
  "document_type": "<'invoice' | 'receipt' | 'purchase_order' | 'credit_note' | 'other'>",
  "vendor_name": "<vendor/supplier name or 'Unknown'>",
  "vendor_contact": "<vendor email or phone or null>",
  "invoice_number": "<invoice/receipt number or null>",
  "invoice_date": "<ISO date string YYYY-MM-DD or null>",
  "due_date": "<ISO date string YYYY-MM-DD or null>",
  "payment_terms": "<e.g. 'Net 30', 'Due on receipt', etc. or null>",
  "currency": "<3-letter ISO currency code, e.g. 'USD', 'EUR'>",
  "subtotal": <numeric float or null>,
  "tax_amount": <numeric float or null>,
  "total_amount": <numeric float or null>,
  "line_items": [
    {
      "description": "<item description>",
      "quantity": <numeric or null>,
      "unit_price": <numeric float or null>,
      "total": <numeric float or null>
    }
  ],
  "payment_recommendation": "<'approve' | 'hold' | 'review'>",
  "anomalies": ["<list of detected issues, e.g. 'Missing invoice number', 'Amount inconsistency'>"],
  "action_items": ["<3-5 AP team action items>"],
  "summary": "<2-3 sentence summary for the finance team>",
  "confidence": <float 0.0-1.0>
}

Payment recommendation guide:
- approve: All required fields present, amounts consistent, no anomalies
- hold: Missing payment details, amount ambiguous, pending PO match
- review: Anomalies detected, unusual amount, potential duplicate

Required fields for approval: vendor_name, invoice_number, total_amount, due_date"""


async def finance_agent_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: Process a financial document submission."""
    content = state.get("content", "")
    file_text = state.get("file_text")

    full_text = content
    if file_text:
        # For finance, document text takes priority
        full_text = f"User note: {content}\n\n--- Invoice/Document Content ---\n{file_text}"

    logger.info(
        "finance_agent_start",
        submission_id=state.get("submission_id"),
        has_file=bool(file_text),
    )

    try:
        raw_result = await _extract_invoice_data(full_text)
        response = _build_response(raw_result)

        logger.info(
            "finance_agent_complete",
            submission_id=state.get("submission_id"),
            document_type=raw_result.get("document_type"),
            total_amount=raw_result.get("total_amount"),
            recommendation=raw_result.get("payment_recommendation"),
        )

        return {
            "agent_response": response.to_dict(),
            **add_step(state, "finance_agent_node", {
                "document_type": raw_result.get("document_type"),
                "total_amount": raw_result.get("total_amount"),
                "recommendation": raw_result.get("payment_recommendation"),
                "anomalies_count": len(raw_result.get("anomalies", [])),
            }),
        }

    except Exception as exc:
        logger.error("finance_agent_error", submission_id=state.get("submission_id"), error=str(exc))
        return {
            "agent_error": f"Finance agent error: {str(exc)}",
            **add_step(state, "finance_agent_node", {}, error=str(exc)),
        }


async def _extract_invoice_data(text: str) -> dict[str, Any]:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY,
        request_timeout=25,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    truncated = text[:8000]  # Longer limit for OCR-heavy documents
    messages = [
        SystemMessage(content=FINANCE_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract financial data from:\n\n{truncated}"),
    ]
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=25.0)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return _fallback_response()


def _build_response(data: dict[str, Any]) -> AgentResponse:
    valid_recommendations = {"approve", "hold", "review"}
    recommendation = data.get("payment_recommendation", "review")
    if recommendation not in valid_recommendations:
        recommendation = "review"

    total_amount = data.get("total_amount")
    if total_amount is not None:
        try:
            total_amount = float(total_amount)
        except (ValueError, TypeError):
            total_amount = None

    anomalies = data.get("anomalies", [])
    if not isinstance(anomalies, list):
        anomalies = []

    line_items = data.get("line_items", [])
    if not isinstance(line_items, list):
        line_items = []

    action_items = data.get("action_items", [])
    if not isinstance(action_items, list):
        action_items = [str(action_items)]

    confidence = float(data.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    # Auto-hold if anomalies detected and recommendation is approve
    if anomalies and recommendation == "approve":
        recommendation = "review"

    return AgentResponse(
        agent_type=AgentType.finance,
        summary=data.get("summary", "Financial document processed."),
        structured_data={
            "document_type": data.get("document_type", "invoice"),
            "vendor_name": data.get("vendor_name", "Unknown"),
            "vendor_contact": data.get("vendor_contact"),
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "due_date": data.get("due_date"),
            "payment_terms": data.get("payment_terms"),
            "currency": data.get("currency", "USD"),
            "subtotal": data.get("subtotal"),
            "tax_amount": data.get("tax_amount"),
            "total_amount": total_amount,
            "line_items": line_items,
            "payment_recommendation": recommendation,
            "anomalies": anomalies,
        },
        action_items=action_items[:5],
        confidence=confidence,
        metadata={
            "has_anomalies": bool(anomalies),
            "recommendation": recommendation,
        },
    )


def _fallback_response() -> dict[str, Any]:
    return {
        "document_type": "invoice",
        "vendor_name": "Unknown",
        "vendor_contact": None,
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "payment_terms": None,
        "currency": "USD",
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
        "line_items": [],
        "payment_recommendation": "review",
        "anomalies": ["Automated extraction failed — manual review required"],
        "action_items": ["Manually review the attached document", "Contact vendor for clarification"],
        "summary": "Financial document received. Automated extraction failed — manual review required.",
        "confidence": 0.2,
    }
```

## Existing Files To Modify
None.

## API Contracts
LangGraph node — not an HTTP endpoint.

## Request Examples
```python
state = {
    "content": "Please process this invoice from TechSupplies Inc",
    "file_text": "INVOICE #INV-2024-0042\nTechSupplies Inc\nDate: 2024-01-15\nDue: 2024-02-14\nItem: Cloud Storage 100TB x 1 = $4,500.00\nTax (8%): $360.00\nTotal: $4,860.00",
}
result = await finance_agent_node(state)
```

## Response Examples
```json
{
  "agent_response": {
    "agent_type": "finance",
    "structured_data": {
      "vendor_name": "TechSupplies Inc",
      "invoice_number": "INV-2024-0042",
      "total_amount": 4860.00,
      "due_date": "2024-02-14",
      "payment_recommendation": "approve",
      "anomalies": [],
      "line_items": [{"description": "Cloud Storage 100TB", "quantity": 1, "unit_price": 4500.00, "total": 4500.00}]
    }
  }
}
```

## Database Tables
No direct DB interaction.

## Business Logic
- If anomalies are detected but recommendation is `"approve"`, auto-downgrade to `"review"`.
- OCR-heavy documents use 8000 char limit (vs 6000 for text submissions).
- Temperature `0.0` for maximum accuracy in number extraction.
- Missing required fields (invoice_number, total_amount, due_date) → anomaly added + `"hold"` recommendation.

## Validation Rules
- `payment_recommendation` must be `"approve"`, `"hold"`, or `"review"`.
- `total_amount` must be numeric; non-numeric strings → `None`.
- `anomalies` must be a list.
- `confidence` clamped to [0.0, 1.0].

## Error Handling
| Scenario | Behavior |
|----------|----------|
| Timeout | `_fallback_response()` with `"review"` recommendation |
| JSON parse failure | `_fallback_response()` |
| Non-numeric amount | Sets `total_amount = None` |
| Anomalies + approve | Auto-downgrades to `"review"` |

## UI Behavior
Not applicable.

## Test Cases
1. Complete invoice → `payment_recommendation = "approve"`.
2. Invoice with missing invoice_number → anomaly detected, `"hold"` recommendation.
3. Amount inconsistency → `"review"` recommendation.
4. OCR text with line items → all line items extracted.
5. Fallback on JSON parse failure → `"review"` recommendation.
6. Anomalies present + `approve` recommendation → auto-downgraded to `"review"`.
7. Non-numeric `total_amount` → `None`.

## Acceptance Criteria
- [ ] Invoice data extracted with all fields
- [ ] Anomaly detection flags missing fields
- [ ] Payment recommendation correct per rules
- [ ] Line items extracted as structured list
- [ ] Auto-downgrade from approve to review when anomalies present

## Definition of Done
- All test cases pass
- No mypy errors
- Temperature 0.0 for deterministic number extraction
