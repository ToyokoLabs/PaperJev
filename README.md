# Biology Paper Toolset

A set of Python modules for retrieving and analyzing scientific biology papers.

Every module can be run **from the command line** or **through the bundled web app (GUI)** — the two are alternatives that drive the same pipeline. See each module's "In the web app" note below, and [The Web App (GUI alternative)](#the-web-app-gui-alternative) for setup.

## Prerequisites

This project uses `uv` for dependency and environment management. If you don't have it installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```

---

## Module 1: PubMed Downloader
Downloads recent biology-related papers from NCBI PubMed and saves them to a JSON file.

### Configuration
Update `config.json` with your NCBI credentials:
```json
{
    "NCBI_EMAIL": "your.email@example.com",
    "NCBI_API_KEY": "your_api_key_here"
}
```

### Usage
Run the main script to fetch papers from the last 7 days:
```bash
uv run main.py
```
- **Output**: All retrieved papers (title, journal, abstract) are saved to `papers.json`.

### In the web app
Upload PDFs or paste an existing summary and the app downloads matching recent papers from NCBI automatically (adjustable paper count in the upload form). The download runs over the same `PubMedClient` as the CLI.

---

## Module 2: PDF Theme Summarizer
Reads a directory of PDF papers and uses a local Ollama instance (proxying to cloud models) to summarize the common themes.

### Configuration
Update `ollama_config.json` with your model settings:
```json
{
    "ollama_url": "http://localhost:11434",
    "model": "your-cloud-model-name",
    "parameters": {
        "temperature": 0.3,
        "num_ctx": 32768
    }
}
```

### Usage
Run the summarizer by providing the path to the directory containing your PDFs:
```bash
uv run pdf_summarizer.py --dir /path/to/your/pdfs
```
- **Output**: A one-page summary of shared topics and common themes is saved to `summary.md`.

### In the web app
Upload the PDFs in the GUI and the themes summary is synthesized for you — shown in the **Synthesized Themes** card (and saved to the session directory as `summary.md`).

---

## Module 3: Relevance Filter
Evaluates downloaded papers against the themes summary and keeps the relevant ones.

### Configuration
Add your TypeSafe API key to `config.json`:
```json
{
    "NCBI_EMAIL": "your.email@example.com",
    "NCBI_API_KEY": "your_api_key_here",
    "TYPESAFE_API_KEY": "your_typesafe_api_key_here"
}
```

### Usage
Run the filter after Modules 1 and 2 (it reads `papers.json` and `summary.md` from the repo root):
```bash
uv run relevance_filter.py
```
- **Output**: Papers found relevant are saved to `relevant_papers.json`.

An Ollama-based alternative that avoids the TypeSafe API:
```bash
uv run relevance_filter_LLM.py
```
Same inputs and output; uses `ollama_config.json` instead of the TypeSafe key.

### In the web app
Filtering runs automatically after the NCBI download completes; results appear in the **Relevant PubMed Papers** card with their relevance scores, downloadable as JSON.

---

## The Web App (GUI alternative)
All three steps can also be driven from the browser. The app is published as a multi-architecture image (`linux/amd64` + `linux/arm64`):
[dnalinux/jevpapers](https://hub.docker.com/r/dnalinux/jevpapers)

### Configuration
Create your config files in the repo root (they are mounted into the container at runtime; no secrets are baked into the image):
```bash
cp config.json.sample config.json
```
Then fill `config.json` with your own credentials (NCBI email/API key and `TYPESAFE_API_KEY`). Ensure an Ollama instance is reachable — by default the app connects to `http://host.docker.internal:11434` (Ollama running on the Docker host). Edit `ollama_config.json` for model settings, or set the `OLLAMA_URL` environment variable to point elsewhere.

### Usage
```bash
docker compose up -d --build   # build locally
# or pull the published image (skips the build):
docker compose pull && docker compose up -d
```
Then open **http://localhost:8000** in your browser.

- Logs: `docker compose logs -f app`
- Stop: `docker compose down` (session artifacts on the `bio_sessions` volume are preserved)
- Publish an updated image: `docker compose build && docker compose push`
- Rebuild the multi-arch image: `docker buildx build --platform linux/amd64,linux/arm64 -t dnalinux/jevpapers:latest --push .`

**Note**: in-flight analysis sessions live in app memory and are lost when the container restarts.