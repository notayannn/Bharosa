from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractedData:
    raw_text: str
    amount: float | None = None
    transaction_id: str | None = None
    confidence: float = 0.0


class Extractor(ABC):
    """
    Every ingestion strategy (Tesseract, vision-LLM, bank-statement parser)
    implements this. The ingestion router picks a strategy by file type;
    the Reconciliation Agent only ever consumes an ExtractedData object,
    never a provider-specific format.
    """

    @abstractmethod
    def extract(self, file_path: str) -> ExtractedData:
        raise NotImplementedError