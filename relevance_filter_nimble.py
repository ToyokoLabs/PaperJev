import json
import argparse
import logging
from typing import List

from typesafe_sdk import TypeSafeClient, Noul

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class RelevanceFilterNimble:
    """Evaluates the relevance of papers against a summary of themes, using the local Nimble decision model.

    Drop-in replacement for relevance_filter.RelevanceFilter (JEV/TypeSafe cloud):
    same inputs, same output shape, but the model runs through Ollama instead of
    the TypeSafe cloud API.
    """

    def __init__(self, ollama_config_path: str = "ollama_config.json"):
        self.config = self._load_config(ollama_config_path)

        ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        # TypeSafe SDK expects an API root; Ollama exposes the compatible
        # endpoints under /v1, so make sure the URL ends with /v1.
        base_url = ollama_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        # Ollama does not require a real API key, but the SDK requires a
        # non-empty value for its Authorization header.
        api_key = self.config.get("TYPESAFE_API_KEY", "ollama")

        self.client = TypeSafeClient(
            api_key=api_key,
            base_url=base_url,
            model="nimble",
            timeout=120.0,
        )

    def _load_config(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
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
                response = self.client.system_one(
                    state={
                        "article": abstract,
                        "summary": summary_text
                    },
                    questions={
                        "is_relevant": relevance_question
                    },
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
    # Input/Output files (overridable; defaults match relevance_filter.py)
    parser = argparse.ArgumentParser(description="Relevance Filter (Nimble / local Ollama variant)")
    parser.add_argument("--papers", default="papers.json", help="Input papers JSON file")
    parser.add_argument("--summary", default="summary.md", help="Input themes summary file")
    parser.add_argument("--output", default="relevant_papers.json", help="Output JSON file")
    args = parser.parse_args()

    try:
        filter_tool = RelevanceFilterNimble()
        relevant = filter_tool.filter_papers(args.papers, args.summary)

        # Save the relevant papers to a new file
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(relevant, f, indent=4, ensure_ascii=False)

        print(f"\nFiltering complete. {len(relevant)} papers were found relevant.")
        print(f"Results saved to {args.output}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
