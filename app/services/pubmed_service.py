import logging
from typing import List
from pathlib import Path
from Bio import Entrez
from app.core.config import config

logger = logging.getLogger(__name__)

class PubMedService:
    def __init__(self):
        Entrez.email = config.ncbi_email
        Entrez.api_key = config.ncbi_api_key
        Entrez.tool = "BiologyPaperFetcher"

    def fetch_relevant_papers(self, query: str, session_dir: Path, retmax: int = 1000, progress_callback=None) -> List[dict]:
        """
        Search and fetch detailed papers from PubMed.
        """
        from pubmed_client import PubMedClient
        client = PubMedClient()

        pmids = client.search_papers(query, retmax=retmax)
        papers = client.fetch_papers_details(pmids, progress_callback=progress_callback)

        # Convert Paper objects to dicts for JSON compatibility
        results = [p.__dict__ for p in papers]

        # Save to session directory
        import json
        with open(session_dir / "papers.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return results
