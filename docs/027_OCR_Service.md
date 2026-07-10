# 027 – OCR Service

## Objective
Implement the backend OCR service that downloads a file from a Supabase Storage URL, performs optical character recognition using Tesseract, and returns the extracted text. Supports PDF (via pdf2image conversion) and image files (PNG, JPG).

## Scope
- `app/services/ocr_service.py` — OCR extraction service
- PDF → image conversion using `pdf2image`
- Image → text extraction using `pytesseract`
- File download from Supabase public URL via HTTP
- Text cleanup and normalization
- Multi-page PDF support (concatenate all pages)

## Out of Scope
- Document intelligence AI analysis (028)
- Finance agent OCR integration (023 calls this service)
- File upload (015)

## Functional Requirements
1. Download file from HTTPS URL (Supabase Storage public URL).
2. Detect file type from URL extension or Content-Type header.
3. For PDFs: convert each page to image (300 DPI), run OCR on each, join results.
4. For images: run OCR directly.
5. Return extracted text as a single string with pages separated by `\n\n--- Page N ---\n\n`.
6. Timeout download + OCR at 30 seconds total.
7. Return empty string if OCR produces no text (don't raise).
8. Support English language OCR (configurable).

## Technical Requirements
- `pytesseract` 0.3.10
- `Pillow` 10.3.0
- `pdf2image` 1.17.0
- `httpx` for async file download
- Tesseract binary must be installed on the system (`tesseract-ocr` package)
- `pdf2image` requires `poppler` (`poppler-utils` on Linux/Mac)

## Folder Structure
```
backend/
└── app/
    └── services/
        └── ocr_service.py
```

## Files To Create

### `app/services/ocr_service.py`
```python
"""
OCR Service

Downloads files from Supabase Storage URLs and extracts text using Tesseract.

System requirements:
  - tesseract-ocr: sudo apt-get install tesseract-ocr
  - poppler-utils: sudo apt-get install poppler-utils  (for PDF support)
"""
import asyncio
import io
import re
import tempfile
import os
import structlog
from typing import Optional
import httpx
from PIL import Image
import pytesseract

logger = structlog.get_logger(__name__)

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
PDF_CONTENT_TYPE = "application/pdf"
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15MB (slightly above upload limit for safety)
OCR_TIMEOUT_SECONDS = 30
OCR_DPI = 300
OCR_LANG = "eng"


class OCRError(Exception):
    """Raised when OCR processing fails unrecoverably."""
    pass


async def extract_text_from_url(file_url: str) -> str:
    """
    Download a file from a Supabase Storage URL and extract text via OCR.

    Args:
        file_url: HTTPS public URL from Supabase Storage

    Returns:
        Extracted text string (empty string if no text found)

    Raises:
        OCRError: If file cannot be downloaded or is unsupported type
    """
    try:
        return await asyncio.wait_for(
            _extract(file_url),
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("ocr_timeout", file_url=file_url, timeout=OCR_TIMEOUT_SECONDS)
        return ""
    except OCRError:
        raise
    except Exception as exc:
        logger.error("ocr_unexpected_error", file_url=file_url, error=str(exc))
        return ""


async def _extract(file_url: str) -> str:
    """Internal extraction logic."""
    # Download file
    file_bytes, content_type = await _download_file(file_url)

    if not file_bytes:
        return ""

    # Determine file type
    ext = _get_extension(file_url).lower()
    is_pdf = (content_type == PDF_CONTENT_TYPE) or (ext == ".pdf")
    is_image = (content_type in SUPPORTED_IMAGE_TYPES) or (
        ext in {".png", ".jpg", ".jpeg"}
    )

    if is_pdf:
        return await asyncio.to_thread(_ocr_pdf, file_bytes)
    elif is_image:
        return await asyncio.to_thread(_ocr_image, file_bytes)
    else:
        logger.warning("ocr_unsupported_type", content_type=content_type, ext=ext)
        return ""


async def _download_file(url: str) -> tuple[bytes, str]:
    """Download file from URL. Returns (bytes, content_type)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        content_length = int(response.headers.get("content-length", 0))

        if content_length > MAX_FILE_SIZE_BYTES:
            raise OCRError(f"File too large for OCR: {content_length} bytes")

        file_bytes = response.content
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise OCRError("File exceeds maximum size for OCR processing")

        logger.info(
            "ocr_file_downloaded",
            url=url[:80],
            size_bytes=len(file_bytes),
            content_type=content_type,
        )

        return file_bytes, content_type


def _ocr_pdf(file_bytes: bytes) -> str:
    """Convert PDF to images and run OCR on each page. Blocking — run in thread."""
    from pdf2image import convert_from_bytes

    try:
        images = convert_from_bytes(
            file_bytes,
            dpi=OCR_DPI,
            fmt="PNG",
        )
    except Exception as exc:
        logger.error("pdf_conversion_failed", error=str(exc))
        return ""

    if not images:
        return ""

    page_texts = []
    for i, image in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(image, lang=OCR_LANG)
            cleaned = _clean_text(text)
            if cleaned:
                if len(images) > 1:
                    page_texts.append(f"--- Page {i} ---\n{cleaned}")
                else:
                    page_texts.append(cleaned)
        except Exception as exc:
            logger.warning("ocr_page_failed", page=i, error=str(exc))
            continue

    result = "\n\n".join(page_texts)
    logger.info("ocr_pdf_complete", pages=len(images), chars_extracted=len(result))
    return result


def _ocr_image(file_bytes: bytes) -> str:
    """Run OCR on a single image. Blocking — run in thread."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if necessary (e.g., RGBA PNG)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        text = pytesseract.image_to_string(image, lang=OCR_LANG)
        result = _clean_text(text)
        logger.info("ocr_image_complete", chars_extracted=len(result))
        return result
    except Exception as exc:
        logger.error("ocr_image_failed", error=str(exc))
        return ""


def _clean_text(raw: str) -> str:
    """Clean OCR output: normalize whitespace, remove garbage characters."""
    if not raw:
        return ""

    # Remove non-printable characters except newlines and tabs
    cleaned = re.sub(r"[^\x20-\x7E\n\t]", "", raw)
    # Normalize multiple spaces to single space
    cleaned = re.sub(r" {3,}", "  ", cleaned)
    # Normalize multiple newlines to max 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


def _get_extension(url: str) -> str:
    """Extract file extension from URL path."""
    path = url.split("?")[0]  # Remove query params
    _, ext = os.path.splitext(path)
    return ext
```

## Existing Files To Modify
- `requirements.txt` — already includes `pytesseract`, `Pillow`, `pdf2image`, `httpx`

## API Contracts
Internal service — not an HTTP endpoint.

### Function Signature
```python
async def extract_text_from_url(file_url: str) -> str:
    """Returns extracted text or empty string on failure."""
```

## Request Examples
```python
from app.services.ocr_service import extract_text_from_url

text = await extract_text_from_url(
    "https://abc.supabase.co/storage/v1/object/public/flowpilot-uploads/user-id/invoice.pdf"
)
# Returns: "INVOICE #1234\nVendor: TechCorp\nTotal: $4,500.00\n..."
```

## Response Examples
```
"INVOICE #INV-2024-0042\n\nTechSupplies Inc\n1234 Main Street\nSan Francisco, CA 94102\n\nBill To: Acme Corp\n\nDate: January 15, 2024\nDue: February 14, 2024\n\nDescription                    Qty    Unit Price    Total\nCloud Storage 100TB             1     $4,500.00     $4,500.00\n\nSubtotal: $4,500.00\nTax (8%): $360.00\nTotal: $4,860.00"
```

## Database Tables
Not applicable — pure file processing.

## Business Logic
1. CPU-bound operations (`_ocr_pdf`, `_ocr_image`) run in `asyncio.to_thread()` to avoid blocking the event loop.
2. PDFs with multiple pages: each page extracted separately and joined with `--- Page N ---` separator.
3. Total timeout of 30s includes download + OCR time.
4. Failures are non-fatal: return empty string, not an exception (workflow continues without OCR).
5. RGBA PNGs converted to RGB before OCR (Tesseract requires RGB or grayscale).

## Validation Rules
- File size: max 15MB (slightly above upload limit for safety).
- File type: PDF, PNG, JPG/JPEG only.
- Unsupported types: return empty string (no exception).

## Error Handling
| Scenario | Behavior |
|----------|----------|
| Download failure (404, 403) | `httpx` raises, caught → returns `""` |
| File too large | `OCRError` raised → caught in workflow → returns `""` |
| Tesseract not installed | `pytesseract.TesseractNotFoundError` → returns `""` |
| Corrupted PDF | `pdf2image` exception caught → returns `""` |
| Timeout (30s) | `asyncio.TimeoutError` caught → returns `""` |
| Unsupported file type | Returns `""` with warning log |

## UI Behavior
Not applicable.

## Component Breakdown
Not applicable.

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
- No extractable text: returns `""` (valid — many images have no text).

## Edge Cases
- Scanned PDF with very low DPI: `convert_from_bytes` uses 300 DPI override — may reduce accuracy.
- Password-protected PDF: `pdf2image` raises exception → returns `""`.
- PNG with RGBA transparency: converted to RGB automatically.
- URL with query params (e.g., Supabase token): `_get_extension` strips query params before extracting extension.
- Large multi-page PDF (100 pages): all pages OCR'd. May hit 30s timeout — acceptable, returns partial text.
- Tesseract not installed: raises `TesseractNotFoundError` — document this system requirement prominently.

## Test Cases
1. JPEG invoice → extracted text contains dollar amounts.
2. Single-page PDF → text extracted without page separator.
3. Multi-page PDF → page separators `--- Page N ---` present.
4. File > 15MB → `OCRError` raised.
5. Timeout (mock slow download) → returns `""`.
6. RGBA PNG → converted to RGB before OCR, no errors.
7. Unsupported `.txt` file → returns `""`.
8. `_clean_text` removes non-printable characters.
9. `_get_extension("https://example.com/file.pdf?token=abc")` returns `".pdf"`.

## Acceptance Criteria
- [ ] PDF text extraction works for single and multi-page PDFs
- [ ] Image text extraction works for PNG and JPEG
- [ ] 30-second total timeout enforced
- [ ] Non-fatal failures return empty string
- [ ] CPU-bound OCR runs in thread (doesn't block event loop)
- [ ] System requirements documented (Tesseract, Poppler)

## Definition of Done
- All test cases pass (use test fixtures with known OCR outputs)
- No mypy errors
- System requirements (tesseract, poppler) documented in README / Dockerfile
- `asyncio.to_thread` used for CPU-bound operations
