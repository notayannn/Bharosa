from app.ingestion.extractors.base import Extractor, ExtractedData


class BankStatementExtractor(Extractor):
    """
    Phase 2. Tabular PDF bank-statement parsing via Camelot/pdfplumber.
    Not required by any Phase 1 acceptance criterion — cut for the demo.
    """

    def extract(self, file_path: str) -> ExtractedData:
        raise NotImplementedError("BankStatementExtractor is a Phase 2 feature.")