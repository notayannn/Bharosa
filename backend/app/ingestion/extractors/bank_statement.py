from app.ingestion.extractors.base import Extractor, ExtractedData


class BankStatementExtractor(Extractor):

    def extract(self, file_path: str) -> ExtractedData:
        raise NotImplementedError("BankStatementExtractor is a Phase 2 feature.")