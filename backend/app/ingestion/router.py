import magic
from app.ingestion.extractors.base import Extractor, ExtractedData
from app.ingestion.extractors.tesseract import TesseractExtractor


class UnsupportedFileType(Exception):
    pass

_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_extractor_for_file(file_path: str) -> Extractor:
    """
    Detects the uploaded file's real type from its bytes (not the filename
    extension, which is trivially wrong or spoofable) and returns the
    Extractor strategy that should handle it.
    """
    mime_type = magic.from_file(file_path, mime=True)

    if mime_type in _IMAGE_MIME_TYPES:
        return TesseractExtractor()

    if mime_type == "application/pdf":
        from app.ingestion.extractors.bank_statement import BankStatementExtractor
        return BankStatementExtractor()  # raises NotImplementedError by design

    raise UnsupportedFileType(
        f"No extractor available for '{mime_type}'. Upload a photographed "
        "slip (jpg/png) for this demo."
    )


def extract(file_path: str) -> ExtractedData:
    extractor = get_extractor_for_file(file_path)
    return extractor.extract(file_path)