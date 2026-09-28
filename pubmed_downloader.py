import argparse
import json
from pubmed_client import PubMedClient
import logging

def save_papers_to_json(papers, filename="papers.json"):
    """
    Saves the list of Paper objects to a JSON file.
    """
    # Convert dataclass objects to dictionaries for JSON serialization
    data = [paper.__dict__ for paper in papers]
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Successfully saved {len(papers)} papers to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Download recent biology papers from NCBI PubMed.")
    parser.add_argument("--count", type=int, default=1000,
                        help="Number of papers to download (default: 1000)")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1")

    # Initialize the client
    try:
        client = PubMedClient()
    except Exception as e:
        print(f"Error initializing PubMedClient: {e}")
        print("Please ensure config.json has a valid NCBI_EMAIL.")
        return

    # Define search term
    search_term = "biology"

    print(f"Fetching up to {args.count} recent papers for search term: {search_term}...")
    papers = client.get_recent_biology_papers(search_term=search_term, days=7, retmax=args.count)

    if not papers:
        print("No papers found or an error occurred.")
        return

    # Save all papers to JSON
    save_papers_to_json(papers)

    print(f"\nSuccessfully retrieved {len(papers)} papers.")
    print("-" * 80)
    print("Preview of first 3 results:")
    for i, paper in enumerate(papers[:3], 1):
        print(f"{i}. {paper.title}")
        print(f"   Journal: {paper.journal}")
        print(f"   Abstract: {paper.abstract[:200]}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
