import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, FileText, CheckCircle, AlertCircle, Download } from 'lucide-react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [files, setFiles] = useState([]);
  const [summaryText, setSummaryText] = useState("");
  const [paperCount, setPaperCount] = useState(1000);
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState("");
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Polling for status
  useEffect(() => {
    let interval;
    if (sessionId && status !== "completed" && status?.indexOf("Error") === -1) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${sessionId}`);
          setStatus(res.data.status);
          if (res.data.status === "completed") {
            const resultsRes = await axios.get(`${API_BASE}/results/${sessionId}`);
            setResults(resultsRes.data);
            clearInterval(interval);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [sessionId, status]);

  const handleFileChange = (e) => {
    setFiles([...e.target.files]);
  };

  const hasFiles = files.length > 0;
  const hasSummary = summaryText.trim().length > 0;

  const extractProgress = (statusText) => {
    if (!statusText) return 0;
    const match = statusText.match(/(\d+)%/);
    return match ? parseInt(match[1], 10) : 0;
  };

  const startAnalysis = async () => {
    if (files.length === 0 && !summaryText) return alert("Please upload PDFs or provide a summary");

    setIsLoading(true);
    const formData = new FormData();
    files.forEach(file => formData.append("files", file));
    if (summaryText) {
      formData.append("summary_text", summaryText);
    }
    formData.append("paper_count", paperCount);

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData);
      setSessionId(res.data.session_id);
      setStatus("Starting pipeline...");
    } catch (e) {
      alert("Upload failed: " + e.message);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto flex flex-col">
      {/* Top bar: Toyoko logo (left) */}
      <div className="flex items-center">
        <a href="https://www.toyoko.io" target="_blank" rel="noreferrer" className="p-2 -m-2">
          <img src="/toyoko-logo.png" alt="Toyoko" className="w-10 h-10 rounded-md" />
        </a>
      </div>

      <header className="mb-8 text-center mt-4">
        <h1 className="text-4xl font-bold text-slate-800 mb-2">PaperJev</h1>
        <p className="text-slate-600">Upload PDFs to extract themes and find matching PubMed papers</p>
      </header>

      <div className="mb-8 p-5 bg-blue-50/60 rounded-xl border border-blue-100 text-left text-sm text-slate-600 leading-relaxed">
        <p className="font-semibold text-slate-700 mb-1">What this tool does</p>
        <p>
          PaperJev finds recent scientific papers related to your research. Give it a set of your
          own papers (or a written summary of your research themes), and it will:
        </p>
        <ol className="list-decimal ml-5 mt-2 space-y-1">
          <li>Summarize your PDFs and synthesize their common themes with an LLM (or use the summary you paste);</li>
          <li>Download a batch of recent biology papers from NCBI PubMed (the search covers the last 7 days; it is a broad biology search, not yet matched to your themes);</li>
          <li>Filter the search results by relevance against your themes, so you only see papers worth reading.</li>
        </ol>
        <p className="mt-2">
          Uploading papers and pasting a summary are alternatives — provide just one. The paper count controls how many results are fetched from PubMed.
        </p>
      </div>

      {!sessionId ? (
        <div className="bg-white p-12 rounded-2xl shadow-xl border border-slate-200 text-center">
          <div className="mb-6 flex justify-center">
            <div className="p-4 bg-blue-50 rounded-full">
              <i className="fa-solid fa-newspaper text-4xl text-blue-500"></i>
            </div>
          </div>

          <input
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
            id="pdf-upload"
            disabled={hasSummary}
          />
          <label
            htmlFor="pdf-upload"
            className={`cursor-pointer bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors inline-block mb-4 ${hasSummary ? "opacity-50 pointer-events-none" : ""}`}
          >
            Select PDF Papers
          </label>
          <div className="text-sm text-slate-500 mb-2">
            {hasFiles ? (
              <>
                {files.length} {files.length === 1 ? "file" : "files"} selected
                <button
                  onClick={() => setFiles([])}
                  className="ml-2 text-blue-600 hover:underline text-xs"
                >
                  clear
                </button>
              </>
            ) : (
              "No files selected"
            )}
          </div>
          {hasSummary && (
            <div className="text-xs text-slate-400 mb-4">
              Disabled because a themes summary is provided — clear the text area to select PDFs instead.
            </div>
          )}

          <div className="flex items-center gap-3 mb-2">
            <div className="flex-1 h-px bg-slate-200"></div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">OR</span>
            <div className="flex-1 h-px bg-slate-200"></div>
          </div>

          <div className="mb-8 p-6 bg-slate-50 rounded-xl border border-slate-200 text-left">
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Existing Themes Summary (Optional)
            </label>
            <textarea
              className={`w-full p-3 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all ${hasFiles ? "opacity-50 cursor-not-allowed" : ""}`}
              rows="4"
              placeholder="Paste your summary.md content here to skip PDF analysis..."
              value={summaryText}
              disabled={hasFiles}
              onChange={(e) => setSummaryText(e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-2">
              {hasFiles
                ? "Disabled because PDF papers are selected — clear the selection to paste a summary instead."
                : "If provided, the system will skip PDF parsing and go straight to PubMed search."}
            </p>
          </div>

          <div className="mb-8 p-6 bg-slate-50 rounded-xl border border-slate-200 text-left">
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Papers to Download from NCBI
            </label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                className="w-full p-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                value={paperCount === 0 ? "" : paperCount}
                onChange={(e) => setPaperCount(e.target.value === "" ? 0 : parseInt(e.target.value, 10))}
                min="1"
                max="5000"
              />
              <span className="text-xs text-slate-500 whitespace-nowrap">
                Default: 1000
              </span>
            </div>
          </div>

          <button
            onClick={startAnalysis}
            disabled={(files.length === 0 && !summaryText) || isLoading}
            className="w-full py-4 bg-slate-900 text-white rounded-xl font-bold text-lg hover:bg-slate-800 disabled:bg-slate-300 transition-all flex items-center justify-center gap-2"
          >
            {isLoading && <Loader2 className="w-5 h-5 animate-spin" />}
            Start Analysis
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Status Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                {status === "completed" ? (
                  <CheckCircle className="w-6 h-6 text-green-500" />
                ) : status?.indexOf("Error") !== -1 ? (
                  <AlertCircle className="w-6 h-6 text-red-500" />
                ) : (
                  <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                )}
                <span className="font-medium text-slate-700">{status}</span>
              </div>
              {status === "completed" && (
                <button
                  onClick={() => window.location.reload()}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Start New Analysis
                </button>
              )}
            </div>

            {/* Progress Bar */}
            {status !== "completed" && status?.indexOf("Error") === -1 && (
              <div className="w-full bg-slate-100 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${extractProgress(status)}%` }}
                ></div>
              </div>
            )}
          </div>

          {results && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Theme Summary */}
              <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <div className="flex items-center gap-2 mb-4 border-b pb-2">
                  <FileText className="w-5 h-5 text-slate-500" />
                  <h2 className="font-bold text-slate-800">Synthesized Themes</h2>
                </div>
                <div className="text-slate-600 whitespace-pre-wrap text-sm leading-relaxed">
                  {results.summary}
                </div>
              </div>

              {/* Relevant Papers */}
              <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <div className="flex items-center justify-between mb-4 border-b pb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-slate-500" />
                    <h2 className="font-bold text-slate-800">Relevant PubMed Papers</h2>
                  </div>
                  <button
                    className="p-2 hover:bg-slate-100 rounded-md text-slate-600 transition-colors"
                    title="Download JSON"
                    onClick={() => {
                      const blob = new Blob([JSON.stringify(results.relevant_papers, null, 2)], { type: 'application/json' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'relevant_papers.json';
                      a.click();
                    }}
                  >
                    <Download className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                  {results.relevant_papers.map((paper, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="flex justify-between items-start mb-1">
                        <h3 className="font-semibold text-sm text-slate-800 leading-tight">{paper.title}</h3>
                        <span className="text-xs font-mono bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          {paper.relevance_score?.toFixed(3)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 italic mb-2">{paper.journal}</p>
                      <p className="text-xs text-slate-600 line-clamp-3">{paper.abstract}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <footer className="mt-auto pt-12 text-center text-sm text-slate-500">
        View the source on{' '}
        <a
          href="https://github.com/ToyokoLabs/PaperJev"
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 hover:underline"
        >
          GitHub
        </a>
        {' '}· Released under the{' '}
        <a
          href="https://www.gnu.org/licenses/gpl-3.0.en.html"
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 hover:underline"
        >
          GNU GPL v3
        </a>
      </footer>
    </div>
  );
}