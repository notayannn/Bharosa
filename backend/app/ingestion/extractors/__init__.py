import os

from app.ingestion.extractors.base import Extractor, ExtractedData
from app.ingestion.extractors.tesseract import TesseractExtractor

__all__ = ["Extractor", "ExtractedData", "get_extractor"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PDF_EXTENSIONS = {".pdf"}


def get_extractor(file_path: str) -> Extractor:
    """
    Routes an uploaded file to the right extractor based on its file
    extension. Only the image path is wired up for Phase 1 — PDF routing
    raises until BankStatementExtractor is implemented in Phase 2.

    Extension-based routing (rather than python-magic's content-sniffing)
    is intentional here, not a compromise: python-magic has no clean
    native-Windows story, and since the upload form only accepts specific
    file types to begin with, the extension is already a trustworthy signal
    by the time a file reaches this function.
    """
    _, ext = os.path.splitext(file_path.lower())

    if ext in IMAGE_EXTENSIONS:
        return TesseractExtractor()
    if ext in PDF_EXTENSIONS:
        raise NotImplementedError("PDF ingestion (BankStatementExtractor) is Phase 2.")

    raise ValueError(f"Unsupported file type: {ext}")