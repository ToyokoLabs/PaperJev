import json
import logging
from pathlib import Path
from typing import List

from typesafe_sdk import TypeSafeClient, Noul, NoulAnswer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RelevanceFilter:
    """Evaluates the relevance of papers against a summary of themes."""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.api_key = self.config.get("TYPESAFE_API_KEY")

        if not self.api_key:
            raise ValueError("TYPE_SAFE_API_KEY is required in the config file.")

        self.client = TypeSafeClient(api_key=self.api_key, timeout=120.0)

    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)

    def filter_papers(self, papers_path: str, summary_path: str) -> List[dict]:
        """
        Reads papers and summary, then filters for relevance.
        """
        # Load papers
        with open(papers_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)

        # Load summary
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_text = f.read()

        relevant_papers = []

        # Define the Noul question for binary relevance
        relevance_question = Noul(
            instructions="Is this paper helpful or related to the subject described in the themes summary?"
        )

        logger.info(f"Filtering {len(papers)} papers against the summary...")

        for paper in papers:
            # Use the abstract as the primary text for evaluation
            abstract = paper.get("abstract", "")
            if not abstract or abstract == "No abstract available":
                logger.warning(f"Paper {paper.get('pmid', 'unknown')} has no valid abstract. Skipping.")
                continue

            try:
                # Use system_one for a fast, binary classification
                # state: The information the model uses to answer
                # questions: The specific question(s) to answer
                response = self.client.system_one(
                    state={
                        "article": abstract,
                        "summary": summary_text
                    },
                    questions={
                        "is_relevant": relevance_question
                    },
                    model="jev-1.13.0", # Using the model mentioned in your base code
                )

                answer = response.answers["is_relevant"]
                score = answer.noul
                is_relevant = score > 0.5

                if is_relevant:
                    # Add the score to the paper data before saving
                    paper_with_score = paper.copy()
                    paper_with_score["relevance_score"] = score
                    relevant_papers.append(paper_with_score)
                    logger.info(f"Paper {paper.get('pmid')} -> Relevant (p={score:.3f})")
                else:
                    logger.info(f"Paper {paper.get('pmid')} -> Not Relevant (p={score:.3f})")

            except Exception as e:
                logger.error(f"Error evaluating paper {paper.get('pmid')}: {e}")
                continue

        return relevant_papers

def main():
    # Input/Output files
    PAPERS_FILE = "papers.json"
    SUMMARY_FILE = "summary.md"
    OUTPUT_FILE = "relevant_papers.json"

    try:
        filter_tool = RelevanceFilter()
        relevant = filter_tool.filter_papers(PAPERS_FILE, SUMMARY_FILE)

        # Save the relevant papers to a new file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(relevant, f, indent=4, ensure_ascii=False)

        print(f"\nFiltering complete. {len(relevant)} out of {len(relevant) + (len(relevant) if not relevant else 0)} papers were found relevant.")
        print(f"Results saved to {OUTPUT_FILE}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
