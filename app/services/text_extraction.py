"""Derived text extraction for stored digital books."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import AppError


class PDFTextExtractionService:
    """Extracts text from PDFs without treating it as the canonical document."""

    def validate(self, content: bytes) -> None:
        try:
            PdfReader(BytesIO(content))
        except (PdfReadError, ValueError, OSError) as exc:
            raise AppError(422, "INVALID_PDF", "The uploaded file is not a valid PDF") from exc

    def extract(self, content: bytes) -> str | None:
        try:
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            return text or None
        except (PdfReadError, ValueError, OSError):
            # A readable original remains useful even if its text layer cannot be extracted.
            return None
