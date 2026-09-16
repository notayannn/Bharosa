import os

from app.ingestion.extractors.base import Extractor, ExtractedData
from app.ingestion.extractors.tesseract import TesseractExtractor

__all__ = ["Extractor", "ExtractedData", "get_extractor"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PDF_EXTENSIONS = {".pdf"}


def get_extractor(file_path: str) -> Extractor:
    _, ext = os.path.splitext(file_path.lower())

    if ext in IMAGE_EXTENSIONS:
        return TesseractExtractor()
    if ext in PDF_EXTENSIONS:
        raise NotImplementedError("PDF ingestion (BankStatementExtractor) is Phase 2.")

    raise ValueError(f"Unsupported file type: {ext}")