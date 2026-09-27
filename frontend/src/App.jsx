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
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      {/* Top bar: Toyoko logo (left) and GitHub fork ribbon (right) */}
      <div className="flex items-center justify-between -mb-8">
        <a href="https://www.toyoko.io" target="_blank" rel="noreferrer" className="p-2 -m-2">
          <img src="/toyoko-logo.png" alt="Toyoko" className="w-10 h-10 rounded-md" />
        </a>
        <span aria-hidden="true"></span>
      </div>
      <a
        href="https://github.com/ToyokoLabs/PaperJev"
        className="github-corner absolute top-0 right-0"
        aria-label="View source on GitHub"
      >
        <svg width="70" height="70" viewBox="0 0 250 250" style={{ fill: '#151513', color: '#fff', position: 'absolute', top: 0, border: 0, right: 0 }} aria-hidden="true">
          <path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path>
          <path
            d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,66.6 120.5,66.6 C122.0,64.3 123.4,63.1 125.4,63.1 C129.4,63.1 130.0,65.4 130.0,70.0 L130.0,80.5 C130.0,84.0 132.4,86.3 135.4,86.3 C142.4,86.3 149.4,80.9 149.4,69.2 C149.4,52.6 137.0,42.0 121.5,42.0 C100.7,42.0 86.3,57.7 86.3,80.5 C86.3,94.7 93.0,105.4 106.2,109.0 C110.5,110.1 113.4,113.0 113.4,116.5 C113.4,119.2 112.2,121.0 110.5,121.0 C107.9,121.0 103.5,117.8 96.2,116.2 C81.4,113.2 70.5,100.9 70.5,79.8 C70.5,50.6 92.4,29.0 124.0,29.0 C155.6,29.0 176.0,50.5 176.0,72.7 C176.0,92.4 163.2,110.6 141.6,110.6 C134.1,110.6 128.5,107.5 128.5,100.5 L128.5,91.0 C128.5,83.5 130.5,80.0 133.0,76.6 C136.5,71.9 137.0,70.0 137.0,66.0 C137.0,60.0 132.4,56.0 126.5,56.0 C114.0,56.0 104.0,66.7 104.0,86.0 C104.0,96.0 106.5,103.0 110.0,109.0 C109.5,113.0 108.0,116.0 106.0,118.0 C104.0,119.5 102.5,119.0 101.5,116.0 C99.0,109.5 95.0,99.5 95.0,84.5 C95.0,60.0 107.5,40.0 126.5,40.0 C146.0,40.0 156.5,56.0 156.5,72.0 C156.5,86.0 147.0,100.5 134.5,100.5 C129.0,100.5 124.0,97.5 124.0,91.0 L124.0,75.0 C124.0,70.5 122.5,68.0 120.0,68.0 C115.5,68.0 112.0,72.0 112.0,80.0 C112.0,88.0 114.5,94.5 119.5,99.0 C124.5,103.5 132.0,105.0 140.0,103.0 C152.0,100.0 160.0,90.0 160.0,74.0 C160.0,50.0 141.0,32.0 123.0,32.0 C100.5,32.0 82.5,52.0 82.5,82.0 C82.5,106.0 95.5,124.0 117.0,127.5 C121.5,128.3 124.5,130.5 124.0,134.5 C123.5,138.0 120.5,141.0 118.0,143.0 C115.5,144.5 112.5,145.0 110.0,143.5 C92.0,138.5 78.0,120.0 78.0,80.0 C78.0,44.0 100.0,22.0 124.0,22.0 C152.0,22.0 174.5,43.5 174.5,74.5 C174.5,102.5 156.0,126.0 132.5,126.0 C125.5,126.0 120.0,124.5 116.5,122.0 L116.0,128.5 C115.5,132.5 112.0,135.0 108.0,135.0 C104.0,135.0 100.5,132.5 98.5,128.0 C94.5,120.0 92.5,105.0 92.5,79.5 C92.5,49.5 112.5,20.0 142.5,20.0 Z"
            style={{ transformOrigin: '130px 106px' }}
            className="octo-arm"
          ></path>
        </svg>
      </a>

      <header className="mb-12 text-center mt-4">
        <h1 className="text-4xl font-bold text-slate-800 mb-2">PaperJev</h1>
        <p className="text-slate-600">Upload PDFs to extract themes and find matching PubMed papers</p>
      </header>

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
          />
          <label
            htmlFor="pdf-upload"
            className="cursor-pointer bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors inline-block mb-4"
          >
            Select PDF Papers
          </label>
          <div className="text-sm text-slate-500 mb-2">
            {files.length > 0
              ? `${files.length} files selected`
              : "No files selected"}
          </div>

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
              className="w-full p-3 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              rows="4"
              placeholder="Paste your summary.md content here to skip PDF analysis..."
              value={summaryText}
              onChange={(e) => setSummaryText(e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-2">
              If provided, the system will skip PDF parsing and go straight to PubMed search.
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
    </div>
  );
}