import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import config
from app.services.summarizer_service import SummarizerService
from app.services.pubmed_service import PubMedService
from app.services.filter_service import RelevanceService
from typesafe_sdk import Noul

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Biology Paper Analysis API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session store: { session_id: { status: str, result: Any } }
sessions: Dict[str, Dict[str, Any]] = {}

# Initialize Services
summarizer = SummarizerService()
pubmed = PubMedService()
relevance = RelevanceService()

# Base directory for session files
BASE_SESSION_DIR = Path("/tmp/bio_papers_sessions")
BASE_SESSION_DIR.mkdir(parents=True, exist_ok=True)

def _generate_text(response) -> str:
    """Extract the text from an Ollama generate() result.

    The client may return a GenerateResponse object (newer ollama versions),
    a plain dict, or a raw string depending on version.
    """
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response["response"]
    return response.response

def run_pipeline(session_id: str, pdf_paths: list[Path], paper_count: int = 1000):
    """
    Orchestrates the full pipeline:
    PDFs -> Summary -> NCBI Search -> Relevance Filter
    """
    try:
        session_dir = BASE_SESSION_DIR / session_id
        session_dir.mkdir(exist_ok=True)

        total_pdfs = len(pdf_paths)

        # 1. Summarize Uploaded PDFs
        intermediate_summaries = []
        for idx, path in enumerate(pdf_paths, 1):
            progress = int((idx / total_pdfs) * 100)
            sessions[session_id]["status"] = f"Analyzing {path.name} ({idx}/{total_pdfs}): Extracting text... {progress}%"

            text = summarizer.extract_text(path)
            if not text.strip():
                continue

            sessions[session_id]["status"] = f"Analyzing {path.name} ({idx}/{total_pdfs}): Summarizing... {progress}%"
            summary = summarizer.client.generate(
                model=summarizer.model,
                prompt=text,
                system="You are an expert scientific research analyst. Summarize the following text from a research paper. Extract the primary objective, the methodology used, the key findings, and the main conclusion. Maintain technical rigor.",
                options=summarizer.params
            )
            # Handle the different return formats across ollama versions
            intermediate_summaries.append(f"Paper: {path.name}\nAnalysis: {_generate_text(summary)}\n")


        sessions[session_id]["status"] = "Synthesizing common themes... 100%"
        concatenated = "\n\n".join(intermediate_summaries)
        summary_response = summarizer.client.generate(
            model=summarizer.model,
            prompt=concatenated,
            system="You are a scientific research analyst. Identify the common themes across these papers. Provide a clear, general summary of the topics they collectively cover.",
            options=summarizer.params
        )
        summary_text = _generate_text(summary_response)


        with open(session_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(summary_text)

        # 2. Download from NCBI
        sessions[session_id]["status"] = "Downloading matching papers from NCBI..."
        papers = pubmed.fetch_relevant_papers("biology", session_dir, retmax=paper_count)

        # 3. Filter for Relevance
        total_papers = len(papers)
        relevant_papers = []

        for idx, paper in enumerate(papers, 1):
            progress = int((idx / total_papers) * 100)
            sessions[session_id]["status"] = f"Filtering paper {idx}/{total_papers}: {paper.get('title', 'Unknown')}... {progress}%"

            try:
                relevance_question = Noul(instructions="Is this paper helpful or related to the subject described in the themes summary?")
                response = relevance.client.system_one(
                    state={"article": paper.get("abstract", ""), "summary": summary_text},
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

        # Finalize
        sessions[session_id]["status"] = "completed"
        sessions[session_id]["result"] = {
            "summary": summary_text,
            "relevant_papers": relevant_papers
        }
        logger.info(f"Pipeline completed for session {session_id}")

    except Exception as e:
        logger.error(f"Pipeline failed for {session_id}: {e}")
        sessions[session_id]["status"] = f"Error: {str(e)}"

@app.post("/upload")
async def upload_pdfs(background_tasks: BackgroundTasks, files: Optional[list[UploadFile]] = File(None), summary_text: Optional[str] = Form(None), paper_count: int = Form(1000)):
    """
    Uploads PDFs and optionally provides an existing summary to skip PDF analysis.
    """
    if not files and not summary_text:
        raise HTTPException(status_code=400, detail="Please upload PDFs or provide a summary.")

    session_id = str(uuid.uuid4())
    session_dir = BASE_SESSION_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = []
    if files:
        for file in files:
            if file.content_type == "application/pdf":
                path = session_dir / file.filename
                with open(path, "wb") as f:
                    f.write(await file.read())
                pdf_paths.append(path)

    if not pdf_paths and not summary_text:
        raise HTTPException(status_code=400, detail="No valid PDF files uploaded and no summary provided.")

    sessions[session_id] = {"status": "starting", "result": {"summary": summary_text}, "ncbi_papers": None, "paper_count": paper_count}

    if summary_text:
        sessions[session_id]["status"] = "Downloading recent biology papers from NCBI..."
        background_tasks.add_task(run_ncbi_only, session_id)
    else:
        if not pdf_paths:
            raise HTTPException(status_code=400, detail="No valid PDFs found.")
        background_tasks.add_task(run_pipeline, session_id, pdf_paths, paper_count)

    return {"session_id": session_id}

def run_ncbi_only(session_id: str):
    """Helper to run only the NCBI and Filter steps when summary is already provided."""
    try:
        session_dir = BASE_SESSION_DIR / session_id
        summary_text = sessions[session_id]["result"]["summary"]
        paper_count = sessions[session_id].get("paper_count", 1000)

        def download_progress(pct):
            sessions[session_id]["status"] = f"Downloading recent biology papers from NCBI... {pct}%"

        sessions[session_id]["status"] = "Starting NCBI download... 0%"
        papers = pubmed.fetch_relevant_papers("biology", session_dir, retmax=paper_count, progress_callback=download_progress)
        sessions[session_id]["ncbi_papers"] = papers

        total_papers = len(papers)
        relevant_papers = []

        for idx, paper in enumerate(papers, 1):
            progress = int((idx / total_papers) * 100)
            sessions[session_id]["status"] = f"Filtering paper {idx}/{total_papers}: {paper.get('title', 'Unknown')}... {progress}%"

            try:
                relevance_question = Noul(instructions="Is this paper helpful or related to the subject described in the themes summary?")
                response = relevance.client.system_one(
                    state={"article": paper.get("abstract", ""), "summary": summary_text},
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

        sessions[session_id]["status"] = "completed"
        sessions[session_id]["result"]["relevant_papers"] = relevant_papers
        logger.info(f"Filtered pipeline completed for session {session_id}")
    except Exception as e:
        logger.error(f"NCBI-only pipeline failed for {session_id}: {e}")
        sessions[session_id]["status"] = f"Error: {str(e)}"

@app.post("/download-ncbi/{session_id}")
async def trigger_ncbi(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    summary_text = sessions[session_id].get("result", {}).get("summary")
    if not summary_text:
        summary_text = "biology"

    sessions[session_id]["status"] = "Downloading from NCBI..."

    async def ncbi_task():
        try:
            session_dir = BASE_SESSION_DIR / session_id
            papers = pubmed.fetch_relevant_papers("biology", session_dir)
            sessions[session_id]["ncbi_papers"] = papers
            sessions[session_id]["status"] = "NCBI Download completed"
        except Exception as e:
            sessions[session_id]["status"] = f"NCBI Error: {str(e)}"

    background_tasks.add_task(ncbi_task)
    return {"message": "NCBI download started"}

@app.post("/run-jev/{session_id}")
async def trigger_jev(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    papers = sessions[session_id].get("ncbi_papers")
    summary_text = sessions[session_id].get("result", {}).get("summary")

    if not papers or not summary_text:
        raise HTTPException(status_code=400, detail="Missing NCBI papers or theme summary. Please run the previous steps first.")

    sessions[session_id]["status"] = "Filtering for relevance..."

    async def jev_task():
        try:
            session_dir = BASE_SESSION_DIR / session_id
            relevant_papers = relevance.filter_papers(papers, summary_text, session_dir)

            sessions[session_id]["status"] = "completed"
            if "result" not in sessions[session_id]:
                sessions[session_id]["result"] = {}
            sessions[session_id]["result"]["relevant_papers"] = relevant_papers
        except Exception as e:
            logger.error(f"JEV Error: {e}")
            sessions[session_id]["status"] = f"JEV Error: {str(e)}"

    background_tasks.add_task(jev_task)
    return {"message": "JEV filtering started"}

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    return sessions[session_id]

@app.get("/results/{session_id}")
async def get_results(session_id: str):
    if session_id not in sessions or sessions[session_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Results not ready or session not found.")
    return sessions[session_id]["result"]

# Serve the built React frontend when it exists (Docker image); no-op in dev mode
from fastapi.staticfiles import StaticFiles

_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
