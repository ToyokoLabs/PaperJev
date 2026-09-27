from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Paper:
    """
    Represents a biology paper retrieved from PubMed.
    """
    pmid: str
    title: str
    journal: str
    abstract: Optional[str]
    pub_date: Optional[str] = None
