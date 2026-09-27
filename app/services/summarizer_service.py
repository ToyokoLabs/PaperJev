import logging
from pathlib import Path
from typing import List
import fitz # PyMuPDF
import ollama
from app.core.config import config

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self):
        self.client = ollama.Client(host=config.ollama_url)
        self.model = config.ollama_model
        self.params = config.ollama_params

    def extract_text(self, pdf_path: Path) -> str:
        text = []
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (b[1], b[0]))
                for b in blocks:
                    if b[4].strip():
                        text.append(b[4])
            doc.close()
        except Exception as e:
            logger.error(f"Extraction error {pdf_path.name}: {e}")
        return "\n".join(text)

    def summarize_pdfs(self, pdf_paths: List[Path], session_dir: Path) -> str:
        # Map Phase
        individual_summaries = []
        map_prompt = (
            "You are an expert scientific research analyst. Analyze the provided research paper text. "
            "Extract and synthesize the following: 1. Primary objective, 2. Methodology, 3. Key findings, 4. Main conclusion. "
            "Maintain technical rigor."
        )

        for path in pdf_paths:
            text = self.extract_text(path)
            if not text.strip(): continue

            response = self.client.generate(
                model=self.model,
                prompt=text,
                system=map_prompt,
                options=self.params
            )
            individual_summaries.append(f"Paper: {path.name}\nAnalysis: {response['response']}\n")

        # Reduce Phase
        reduce_prompt = (
            "You are a senior scientific reviewer. Identify 3-5 common themes across these papers. "
            "Provide a clear, general summary of the topics they collectively cover. "
            "Focus only on shared subjects and overlapping areas."
        )

        concatenated = "\n\n".join(individual_summaries)
        final_response = self.client.generate(
            model=self.model,
            prompt=concatenated,
            system=reduce_prompt,
            options=self.params
        )

        summary_text = final_response['response']
        with open(session_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(summary_text)

        return summary_text
