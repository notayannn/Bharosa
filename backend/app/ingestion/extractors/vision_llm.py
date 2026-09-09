from app.ingestion.extractors.base import Extractor, ExtractedData


class VisionLLMExtractor(Extractor):
    """
    Phase 2. Fallback for stylized/cropped slips Tesseract can't read
    cleanly. Deliberately unimplemented for the demo — cut to avoid
    extra LLM API cost on an edge case we can avoid with a clean test image.
    """

    def extract(self, file_path: str) -> ExtractedData:
        raise NotImplementedError("VisionLLMExtractor is a Phase 2 feature.")