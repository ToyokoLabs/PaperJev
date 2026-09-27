import json
import time
import logging
from typing import List, Optional
from Bio import Entrez
from models import Paper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class PubMedClient:
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the PubMed client using credentials from a config file.
        """
        self.config = self._load_config(config_path)
        self.email = self.config.get("NCBI_EMAIL")
        self.api_key = self.config.get("NCBI_API_KEY")

        if not self.email:
            raise ValueError("NCBI_EMAIL is required in the config file.")

        # Configure Biopython Entrez
        Entrez.email = self.email
        Entrez.api_key = self.api_key
        Entrez.tool = "BiologyPaperFetcher"

    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)

    def search_papers(self, query: str, days: int = 7, retmax: int = 1000) -> List[str]:
        """
        Search for PMIDs of papers matching the query from the last X days.
        """
        logger.info(f"Searching PubMed for '{query}' (last {days} days)...")
        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                reldate=days,
                datetype="pdat",
                retmax=retmax
            )
            record = Entrez.read(handle)
            handle.close()
            pmids = record.get("IdList", [])
            logger.info(f"Found {len(pmids)} papers.")
            return pmids
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def fetch_papers_details(self, pmids: List[str], batch_size: int = 50, progress_callback=None) -> List[Paper]:
        """
        Fetch detailed information for a list of PMIDs in batches.
        """
        if not pmids:
            return []

        papers = []
        total = len(pmids)
        for i in range(0, total, batch_size):
            batch = pmids[i : i + batch_size]
            logger.info(f"Fetching batch {i // batch_size + 1} ({len(batch)} papers)...")

            if progress_callback:
                progress = int(((i + len(batch)) / total) * 100)
                progress_callback(progress)

            try:
                ids = ",".join(batch)
                handle = Entrez.efetch(
                    db="pubmed",
                    id=ids,
                    rettype="abstract",
                    retmode="xml"
                )
                xml_data = handle.read()
                handle.close()

                papers.extend(self._parse_xml(xml_data))

                # Rate limit protection: Small sleep between batches
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"Error fetching batch: {e}")
                continue

        return papers

    def _parse_xml(self, xml_data: str) -> List[Paper]:
        """
        Parse the Entrez XML output to extract Paper objects.
        """
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data)
        parsed_papers = []

        for article in root.findall(".//PubmedArticle"):
            try:
                pmid = article.find(".//PMID").text

                # Title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Unknown Title"

                # Journal
                journal_elem = article.find(".//Title")
                # Note: The .find(".//Title") might be ambiguous in the XML,
                # usually we want Journal -> Title
                # Let's be more specific:
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else "Unknown Journal"

                # Abstract
                abstract_parts = article.findall(".//AbstractText")
                abstract = " ".join([p.text for p in abstract_parts if p.text])

                if not abstract or not abstract.strip():
                    continue

                # Date
                date_elem = article.find(".//PubDate/Year")
                year = date_elem.text if date_elem is not None else ""
                month_elem = article.find(".//PubDate/Month")
                month = month_elem.text if month_elem is not None else ""
                pub_date = f"{year}-{month}".strip("-")

                parsed_papers.append(Paper(
                    pmid=pmid,
                    title=title,
                    journal=journal,
                    abstract=abstract if abstract else "No abstract available",
                    pub_date=pub_date
                ))
            except Exception as e:
                logger.warning(f"Failed to parse article: {e}")
                continue

        return parsed_papers

    def get_recent_biology_papers(self, search_term: str = "biology", days: int = 7, retmax: int = 1000) -> List[Paper]:
        """
        High-level method to search and fetch recent biology papers.
        """
        pmids = self.search_papers(search_term, days=days, retmax=retmax)
        return self.fetch_papers_details(pmids)
