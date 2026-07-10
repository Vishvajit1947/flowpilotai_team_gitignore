# 028 – Invoice Extraction

## Objective
Build the `POST /api/v1/documents/extract-invoice` endpoint that accepts a file URL, runs OCR, passes the extracted text through the Finance Agent for structured data extraction, and returns a normalized invoice data object — without creating an inbox submission.

## Scope
- `POST /api/v1/documents/extract-invoice` — standalone invoice extraction endpoint
- OCR → Finance Agent pipeline (no LangGraph, direct service calls)
- `app/api/v1/endpoints/documents.py` — document intelligence routes
- Pydantic response schema for invoice data

## Out of Scope
- Document Intelligence UI page (029)
- File upload (015 — file_url provided in request body)
- Full workflow/inbox submission (025/016)

## Functional Requirements
1. Accept `file_url` (HTTPS URL to Supabase Storage) in request body.
2. Run OCR on the file to extract raw text.
3. Pass OCR text through Finance Agent to extract structured invoice fields.
4. Return structured invoice data with payment recommendation.
5. No `InboxSubmission` record created — this is a pure extraction endpoint.
6. Requires authentication.
7. Respond within 45 seconds (OCR + Finance Agent combined).

## Technical Requirements
- FastAPI route with `CurrentUser` dependency
- Direct calls to `ocr_service.extract_text_from_url()` and `finance_agent`
- Pydantic response model
- `asyncio.wait_for` for 45s timeout

## Folder Structure
```
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── endpoints/
    │           └── documents.py
    └── schemas/
        └── documents.py
```

## Files To Create

### `app/schemas/documents.py`
```python
from typing import Any, List, Optional
from pydantic import BaseModel, field_validator


class InvoiceExtractionRequest(BaseModel):
    file_url: str

    @field_validator("file_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("file_url must be an HTTPS URL")
        return v


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class InvoiceExtractionResponse(BaseModel):
    document_type: str
    vendor_name: Optional[str]
    vendor_contact: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    payment_terms: Optional[str]
    currency: str
    subtotal: Optional[float]
    tax_amount: Optional[float]
    total_amount: Optional[float]
    line_items: List[LineItem]
    payment_recommendation: str
    anomalies: List[str]
    action_items: List[str]
    summary: str
    confidence: float
    raw_text_length: int  # How many chars OCR extracted
```

### `app/api/v1/endpoints/documents.py`
```python
"""
Document Intelligence API

Provides standalone document processing endpoints without creating inbox submissions.
"""
import asyncio
import structlog
from fastapi import APIRouter, status
from app.api.deps import CurrentUser
from app.core.exceptions import ValidationError
from app.schemas.documents import InvoiceExtractionRequest, InvoiceExtractionResponse, LineItem
from app.services.ocr_service import extract_text_from_url
from app.agents.finance_agent import _extract_invoice_data, _build_response

logger = structlog.get_logger(__name__)
router = APIRouter()

EXTRACTION_TIMEOUT = 45.0


@router.post(
    "/extract-invoice",
    response_model=InvoiceExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured invoice data from a document",
    description=(
        "Runs OCR on the provided file URL and uses AI to extract invoice fields. "
        "Does not create an inbox submission."
    ),
)
async def extract_invoice(
    body: InvoiceExtractionRequest,
    current_user: CurrentUser,
) -> InvoiceExtractionResponse:
    logger.info(
        "invoice_extraction_start",
        user_id=str(current_user.id),
        file_url=body.file_url[:80],
    )

    try:
        result = await asyncio.wait_for(
            _run_extraction(body.file_url),
            timeout=EXTRACTION_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        raise ValidationError("Document processing timed out. Please try a smaller file.")
    except Exception as exc:
        logger.error("invoice_extraction_failed", error=str(exc))
        raise ValidationError(f"Document processing failed: {str(exc)}")


async def _run_extraction(file_url: str) -> InvoiceExtractionResponse:
    """Run OCR + Finance Agent extraction pipeline."""
    # Step 1: OCR
    raw_text = await extract_text_from_url(file_url)

    if not raw_text:
        # No text extracted — still run finance agent with empty text
        raw_text = "[No text extracted from document]"

    # Step 2: Finance Agent extraction
    # Pass as "user note: (none)" + document content
    combined = f"User note: Direct invoice extraction request.\n\n--- Document Content ---\n{raw_text}"
    raw_result = await _extract_invoice_data(combined)

    # Step 3: Build response
    agent_response = _build_response(raw_result)
    structured = agent_response.structured_data

    line_items = [
        LineItem(
            description=item.get("description"),
            quantity=item.get("quantity"),
            unit_price=item.get("unit_price"),
            total=item.get("total"),
        )
        for item in structured.get("line_items", [])
    ]

    return InvoiceExtractionResponse(
        document_type=structured.get("document_type", "invoice"),
        vendor_name=structured.get("vendor_name"),
        vendor_contact=structured.get("vendor_contact"),
        invoice_number=structured.get("invoice_number"),
        invoice_date=structured.get("invoice_date"),
        due_date=structured.get("due_date"),
        payment_terms=structured.get("payment_terms"),
        currency=structured.get("currency", "USD"),
        subtotal=structured.get("subtotal"),
        tax_amount=structured.get("tax_amount"),
        total_amount=structured.get("total_amount"),
        line_items=line_items,
        payment_recommendation=structured.get("payment_recommendation", "review"),
        anomalies=structured.get("anomalies", []),
        action_items=agent_response.action_items,
        summary=agent_response.summary,
        confidence=agent_response.confidence,
        raw_text_length=len(raw_text),
    )
```

## Files To Modify

### `app/api/v1/router.py` — include documents router
```python
from app.api.v1.endpoints import auth, inbox, documents

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
```

## API Contracts

### `POST /api/v1/documents/extract-invoice`
```
Method:  POST
Path:    /api/v1/documents/extract-invoice
Auth:    Bearer token
Content-Type: application/json

Request:
{
  "file_url": "https://project.supabase.co/storage/v1/object/public/flowpilot-uploads/user/invoice.pdf"
}

Response 200:
{
  "document_type": "invoice",
  "vendor_name": "TechSupplies Inc",
  "invoice_number": "INV-2024-0042",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-14",
  "payment_terms": "Net 30",
  "currency": "USD",
  "subtotal": 4500.00,
  "tax_amount": 360.00,
  "total_amount": 4860.00,
  "line_items": [
    { "description": "Cloud Storage 100TB", "quantity": 1, "unit_price": 4500.00, "total": 4500.00 }
  ],
  "payment_recommendation": "approve",
  "anomalies": [],
  "action_items": ["Verify against PO#4521", "Route for approval"],
  "summary": "Valid invoice from TechSupplies Inc for $4,860.00...",
  "confidence": 0.91,
  "raw_text_length": 847
}

Response 422 (timeout):
{
  "detail": "Document processing timed out. Please try a smaller file.",
  "status_code": 422
}
```

## Request Examples
```bash
curl -X POST http://localhost:8000/api/v1/documents/extract-invoice \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"file_url":"https://abc.supabase.co/storage/v1/object/public/uploads/user/invoice.pdf"}'
```

## Response Examples
```json
{
  "document_type": "invoice",
  "vendor_name": "TechSupplies Inc",
  "total_amount": 4860.00,
  "payment_recommendation": "approve",
  "anomalies": [],
  "confidence": 0.91,
  "raw_text_length": 847
}
```

## Database Tables
**No writes** — this is a read-only extraction endpoint.

## Business Logic
1. Direct service calls (no LangGraph) — faster and simpler for a standalone extraction.
2. `raw_text_length` returned so the frontend can show "OCR extracted N characters".
3. If OCR produces no text, a placeholder is passed to Finance Agent; it will likely return `payment_recommendation: "review"` with anomalies.
4. 45-second total timeout covers OCR (30s) + Finance Agent (25s) with some overlap.

## Validation Rules
- `file_url`: must start with `https://`.
- Timeout: 45 seconds total.

## Error Handling
| Scenario | Status |
|----------|--------|
| Invalid file_url | 422 |
| OCR timeout | 422 with timeout message |
| Finance Agent error | 422 with error message |
| Unauthenticated | 401 |

## UI Behavior
Not applicable — see 029 for Document Intelligence UI.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Image with no text → OCR returns `""` → Finance Agent gets placeholder → confidence < 0.3.
- PDF with tables: Tesseract may not perfectly align columns, but GPT-4o handles noisy OCR text well.
- `_extract_invoice_data` and `_build_response` imported directly from `finance_agent.py` — must be importable standalone (no state dependency).

## Test Cases
1. Valid invoice PDF → structured data extracted, `payment_recommendation="approve"`.
2. Image with no text → `raw_text_length=0` (placeholder), `payment_recommendation="review"`.
3. Non-https URL → 422 validation error.
4. Timeout after 45s → 422 with timeout message.
5. Unauthenticated request → 401.
6. `line_items` is a list of `LineItem` objects.
7. `anomalies` populated when invoice has missing fields.

## Acceptance Criteria
- [ ] `POST /extract-invoice` returns structured invoice data
- [ ] OCR + Finance Agent pipeline works end-to-end
- [ ] 45-second timeout enforced
- [ ] No `InboxSubmission` record created
- [ ] `raw_text_length` present in response

## Definition of Done
- All test cases pass
- No mypy errors
- Documents router registered in `api_router`
- `_extract_invoice_data` and `_build_response` are importable without side effects
