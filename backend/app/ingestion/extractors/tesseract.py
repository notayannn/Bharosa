import pytesseract
from PIL import Image

from app.ingestion.extractors.base import Extractor, ExtractedData


class TesseractExtractor(Extractor):
    """Phase 1 default — handles clean photographed slips/receipts."""

    def extract(self, file_path: str) -> ExtractedData:
        image = Image.open(file_path)
        raw_text = pytesseract.image_to_string(image)

        return ExtractedData(raw_text=raw_text, confidence=0.7)