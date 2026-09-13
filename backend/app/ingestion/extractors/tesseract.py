import re

import pytesseract
from PIL import Image

from app.ingestion.extractors.base import Extractor, ExtractedData

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Demo-level heuristics only -- real production slips are messy enough that
# this would eventually move to the vision-LLM fallback (vision_llm.py,
# currently a Phase 2 stub). Good enough for a clean test slip image.
_AMOUNT_PATTERN = re.compile(
    r"(?:rs\.?|pkr)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)
_TXN_PATTERN = re.compile(
    r"(?:txn|transaction|ref(?:erence)?)[\s#:\-]*([A-Za-z0-9]{5,20})", re.IGNORECASE
)


class TesseractExtractor(Extractor):
    """Phase 1 default — handles clean photographed slips/receipts."""

    def extract(self, file_path: str) -> ExtractedData:
        image = Image.open(file_path)
        raw_text = pytesseract.image_to_string(image)

        amount = None
        amount_match = _AMOUNT_PATTERN.search(raw_text)
        if amount_match:
            try:
                amount = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                amount = None

        transaction_id = None
        txn_match = _TXN_PATTERN.search(raw_text)
        if txn_match:
            transaction_id = txn_match.group(1)

        # Confidence reflects whether we actually found structured data, not
        # just whether OCR ran without crashing.
        confidence = 0.7 if (amount is not None or transaction_id is not None) else 0.3

        return ExtractedData(
            raw_text=raw_text,
            amount=amount,
            transaction_id=transaction_id,
            confidence=confidence,
        )