import json
import re
import argparse
import logging
from pathlib import Path
from typing import List

from pdf_summarizer import OllamaClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Same judgment as the JEV version's is_relevant question
SYSTEM_PROMPT = (
    "You are a scientific relevance assessor. You will be given a research paper "
    "abstract and a themes summary. Reply ONLY with a single number between 0.0 and 1.0 "
    "indicating how relevant the paper is to the summary: 1.0 = highly relevant, "
    "0.0 = not relevant at all. No other text."
)

# First standalone number in [0, 1]; tolerates "%", trailing punctuation, and "0.75."
SCORE_RE = re.compile(r"(?:^|[\s(\[])([01](?:\.\d+)?%?)(?=$|[\s.,;)\]%])")


def _parse_score(reply: str) -> float | None:
    """Extracts a relevance score in [0, 1] from the model's reply, or None."""
    text = reply.strip()
    match = SCORE_RE.search(text)
    if not match:
        return None
    try:
        score = float(match.group(1).rstrip("%"))
    except ValueError:
        return None
    if "%" in match.group(1):
        score /= 100.0
    return min(max(score, 0.0), 1.0)


class RelevanceFilterLLM:
    """Evaluates the relevance of papers against a summary of themes, using an LLM via Ollama.

    Drop-in alternative to relevance_filter.RelevanceFilter (JEV/TypeSafe):
    same inputs, same output shape.
    """

    def __init__(self, ollama_config_path: str = "ollama_config.json"):
        self.client = OllamaClient(config_path=ollama_config_path)

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

        logger.info(f"Filtering {len(papers)} papers against the summary...")

        for paper in papers:
            # Use the abstract as the primary text for evaluation
            abstract = paper.get("abstract", "")
            if not abstract or abstract == "No abstract available":
                logger.warning(f"Paper {paper.get('pmid', 'unknown')} has no valid abstract. Skipping.")
                continue

            try:
                prompt = (
                    f"THEMES SUMMARY:\n{summary_text}\n\n"
                    f"PAPER ABSTRACT:\n{abstract}\n\n"
                    "Relevance score (0.0-1.0):"
                )
                reply = self.client.generate(prompt, system_prompt=SYSTEM_PROMPT)
                score = _parse_score(reply)

                if score is None:
                    logger.error(f"Could not parse a score from the model reply for paper "
                                 f"{paper.get('pmid')}: {reply[:200]!r}")
                    continue

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
    parser = argparse.ArgumentParser(description="Relevance Filter (Ollama LLM variant)")
    parser.add_argument("--papers", default="papers.json", help="Input papers JSON file")
    parser.add_argument("--summary", default="summary.md", help="Input themes summary file")
    parser.add_argument("--output", default="relevant_papers.json", help="Output JSON file")
    args = parser.parse_args()

    try:
        filter_tool = RelevanceFilterLLM()
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