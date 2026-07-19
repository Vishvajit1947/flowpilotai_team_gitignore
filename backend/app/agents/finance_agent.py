"""
Finance Agent

Processes invoice and financial document submissions.
Extracts structured data, detects anomalies, and recommends payment actions.
"""
import json
import asyncio
import structlog
from typing import Any
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


class ChatOpenAI:
    def __new__(cls, *args, **kwargs):
        from app.services.llm import get_llm
        temp = kwargs.get("temperature", 0.1)
        response_format_json = False
        if "model_kwargs" in kwargs and kwargs["model_kwargs"].get("response_format", {}).get("type") == "json_object":
            response_format_json = True
        return get_llm(temperature=temp, response_format_json=response_format_json)


async def _extract_invoice_data(text: str) -> dict[str, Any]:
    is_mock = settings.is_mock_mode
    if is_mock:
        text_lower = text.lower()
        import re
        invoice_num_match = re.search(r'(?:inv-|invoice\s*#?\s*)(\w+\d+[\w\d-]*)', text_lower)
        invoice_num = invoice_num_match.group(1).upper() if invoice_num_match else "INV-2026-9081"
        
        amount_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', text_lower)
        total_amount = 1728.00
        if amount_match:
            try:
                total_amount = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                pass
        subtotal = round(total_amount / 1.08, 2)
        tax = round(total_amount - subtotal, 2)
        
        vendor = "Cloudflare, Inc."
        if "cloudflare" in text_lower:
            vendor = "Cloudflare, Inc."
        elif "amazon" in text_lower or "aws" in text_lower:
            vendor = "Amazon Web Services"
        elif "google" in text_lower or "gcp" in text_lower:
            vendor = "Google Cloud Platform"
        elif "acme" in text_lower:
            vendor = "Acme Corp"
        elif "microsoft" in text_lower or "azure" in text_lower:
            vendor = "Microsoft Corp"
        
        return {
            "document_type": "invoice",
            "vendor_name": vendor,
            "vendor_contact": f"payments@{vendor.lower().replace(' ', '').replace(',', '')}.com",
            "invoice_number": invoice_num,
            "invoice_date": "2026-07-11",
            "due_date": "2026-07-25",
            "payment_terms": "Net 14",
            "currency": "USD",
            "subtotal": subtotal,
            "tax_amount": tax,
            "total_amount": total_amount,
            "line_items": [
                {
                    "description": f"Subscription Services for {vendor}",
                    "quantity": 1,
                    "unit_price": subtotal,
                    "total": subtotal
                }
            ],
            "payment_recommendation": "approve",
            "anomalies": [],
            "action_items": [
                f"Verify {vendor} payment banking details match internal records",
                f"Log invoice {invoice_num} in accounting ERP ledger",
                f"Approve payment of ${total_amount:,.2f} before due date July 25, 2026"
            ],
            "summary": f"Cloudflare invoice {invoice_num} for security services and CDN shielding totaling ${total_amount:,.2f}. No anomalies detected." if vendor == "Cloudflare, Inc." else f"Simulated {vendor} invoice {invoice_num} totaling ${total_amount:,.2f}. No anomalies detected.",
            "confidence": 0.95
        }

    llm: Any = ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        openai_api_key=settings.OPENAI_API_KEY,  # type: ignore[call-arg]
        request_timeout=90,  # type: ignore[call-arg]
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    truncated = text[:8000]  # Longer limit for OCR-heavy documents
    messages = [
        SystemMessage(content=FINANCE_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract financial data from:\n\n{truncated}"),
    ]
    response = await asyncio.wait_for(llm.ainvoke(messages), timeout=90.0)

    raw = response.content
    if not isinstance(raw, str):
        raw = str(raw)

    try:
        return json.loads(raw)
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
