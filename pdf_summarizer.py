import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
import ollama

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF text extraction from a directory."""

    def __init__(self, directory_path: str):
        self.directory_path = Path(directory_path)
        if not self.directory_path.is_dir():
            raise ValueError(f"The path {directory_path} is not a valid directory.")

    def get_pdf_files(self) -> List[Path]:
        """Returns a list of PDF files in the directory."""
        return list(self.directory_path.glob("*.pdf"))

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extracts text from a PDF, attempting to preserve reading order
        in multi-column scientific layouts.
        """
        logger.info(f"Extracting text from {pdf_path.name}...")
        text = []
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                # get_text("blocks") returns a list of tuples: (x0, y0, x1, y1, "text", block_no, block_type)
                blocks = page.get_text("blocks")

                # Sort blocks to handle multi-column layouts:
                # 1. Primary sort by top coordinate (y0)
                # 2. Secondary sort by left coordinate (x0)
                # This is a basic heuristic; for advanced layouts, we'd separate columns.
                blocks.sort(key=lambda b: (b[1], b[0]))

                for b in blocks:
                    if b[4].strip():
                        text.append(b[4])

            doc.close()
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path.name}: {e}")

        return "\n".join(text)

class OllamaClient:
    """Handles interaction with the local Ollama API."""

    def __init__(self, config_path: str = "ollama_config.json"):
        self.config = self._load_config(config_path)
        self.model = self.config.get("model", "llama3")
        self.url = self.config.get("ollama_url", "http://localhost:11434")
        self.params = self.config.get("parameters", {})

        # Initialize the Ollama client with the base URL
        self.client = ollama.Client(host=self.url)

    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Sends a prompt to the LLM and returns the generated text."""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                options=self.params
            )
            return response['response']
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return f"Error generating response: {e}"

class Summarizer:
    """Orchestrates the PDF extraction and summarization flow."""

    def __init__(self, processor: PDFProcessor, client: OllamaClient):
        self.processor = processor
        self.client = client

    def summarize_all(self) -> str:
        pdf_files = self.processor.get_pdf_files()
        if not pdf_files:
            return "No PDF files found in the specified directory."

        # 1. Map Phase: Summarize each PDF individually
        individual_summaries = []
        map_system_prompt = (
            "You are an expert scientific research analyst. Analyze the provided research paper text. "
            "Extract and synthesize the following with high precision: "
            "1. The primary research objective and hypothesis. "
            "2. A detailed description of the methodology and experimental design. "
            "3. The key empirical findings and quantitative results. "
            "4. The main conclusion and its implications for the field. "
            "Maintain technical rigor and preserve specific terminology."
        )

        for pdf in pdf_files:
            text = self.processor.extract_text(pdf)
            if not text.strip():
                logger.warning(f"No text extracted from {pdf.name}. Skipping.")
                continue

            logger.info(f"Analyzing {pdf.name} using cloud-backed model...")
            summary = self.client.generate(prompt=text, system_prompt=map_system_prompt)
            individual_summaries.append(f"Paper: {pdf.name}\nAnalysis: {summary}\n")

        if not individual_summaries:
            return "No valid text could be extracted from the PDFs."

        # 2. Reduce Phase: Synthesize common themes
        logger.info("Synthesizing common themes...")
        reduce_system_prompt = (
            "You are a scientific research analyst. You are provided with summaries of multiple research papers. "
            "Your sole task is to identify the common themes across these papers. "
            "Provide a clear, general summary of the topics they collectively cover. "
            "Focus only on the shared subjects and overlapping areas of research."
        )

        concatenated_summaries = "\n\n".join(individual_summaries)
        final_summary = self.client.generate(prompt=concatenated_summaries, system_prompt=reduce_system_prompt)

        return final_summary

def save_summary_to_markdown(summary: str, filename: str = "summary.md"):
    """
    Saves the final summary to a Markdown file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Research Synthesis: Common Themes\n\n")
            f.write(summary)
        print(f"Successfully saved final summary to {filename}")
    except Exception as e:
        logger.error(f"Failed to save summary to file: {e}")

def main():
    parser = argparse.ArgumentParser(description="PDF Theme Summarizer")
    parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Path to the directory containing PDF files"
    )
    args = parser.parse_args()

    try:
        # Initialize components
        processor = PDFProcessor(args.dir)
        client = OllamaClient()
        summarizer = Summarizer(processor, client)

        # Run the process
        result = summarizer.summarize_all()

        # Save to Markdown file
        save_summary_to_markdown(result)

        print("\n" + "="*40)
        print("FINAL ONE-PAGE SUMMARY (Preview)")
        print("="*40 + "\n")
        print(result)
        print("\n" + "="*40)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
