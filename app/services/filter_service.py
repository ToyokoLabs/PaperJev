import logging
from typing import List
from pathlib import Path
from typesafe_sdk import TypeSafeClient, Noul
from app.core.config import config

logger = logging.getLogger(__name__)

class RelevanceService:
    def __init__(self):
        self.client = TypeSafeClient(api_key=config.typesafe_api_key, timeout=120.0)

    def filter_papers(self, papers: List[dict], summary_text: str, session_dir: Path) -> List[dict]:
        relevant_papers = []
        relevance_question = Noul(instructions="Is this paper helpful or related to the subject described in the themes summary?")

        for paper in papers:
            abstract = paper.get("abstract", "")
            if not abstract or abstract == "No abstract available":
                continue

            try:
                response = self.client.system_one(
                    state={"article": abstract, "summary": summary_text},
                    questions={"is_relevant": relevance_question},
                    model="jev-1.13.0",
                )
                score = response.answers["is_relevant"].noul
                if score > 0.5:
                    paper_with_score = paper.copy()
                    paper_with_score["relevance_score"] = score
                    relevant_papers.append(paper_with_score)
            except Exception as e:
                logger.error(f"Error filtering paper {paper.get('pmid')}: {e}")

        return relevant_papers
