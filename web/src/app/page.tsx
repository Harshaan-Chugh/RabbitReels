"use client";

import { useState, useEffect } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import { v4 as uuid } from "uuid";

type Status =
  | { stage: "idle" }
  | { stage: "queued" | "rendering"; jobId: string; progress?: number }
  | { stage: "done"; jobId: string; downloadUrl: string }
  | { stage: "error"; msg: string };

export default function Home() {
  const [theme, setTheme] = useState<"family_guy" | "rick_and_morty">("family_guy");
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<Status>({ stage: "idle" });

  // Polling hook -------------------------------------------------------
  useEffect(() => {
    if (status.stage !== "queued" && status.stage !== "rendering") return;
    const id = status.jobId;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/videos/${id}`);
        if (!r.ok) return; // ignore 404 while queue spins up
        const js = await r.json();
        if (js.status === "done") {
          setStatus({ stage: "done", jobId: id, downloadUrl: js.download_url });
          clearInterval(t);
        } else if (js.status === "error") {
          setStatus({ stage: "error", msg: js.error_msg || "unknown error" });
          clearInterval(t);
        } else {
          setStatus({ ...status, progress: js.progress ?? 0.5 });
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    }, 5000);
    return () => clearInterval(t);
  }, [status]);

  // Submit -------------------------------------------------------------
  const handleCreate = async () => {
    if (!prompt.trim()) return alert("Enter a prompt!");
    const jobId = uuid();
    const body = { job_id: jobId, prompt, character_theme: theme };
    
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/videos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const msg = await r.text();
        return alert(`Error: ${msg}`);
      }
      setStatus({ stage: "queued", jobId });
    } catch (error) {
      alert(`Network error: ${error}`);
    }
  };

  // Render -------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="text-center space-y-4 mb-8">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            🎬 RabbitReels Generator
          </h1>
          <p className="text-gray-600 text-xl">
            Create AI-powered short videos with your favorite characters
          </p>
        </div>

        <div className="bg-white rounded-xl p-8 shadow-xl space-y-8">
          <div className="space-y-3">
            <label className="block text-lg font-semibold text-gray-800">
              Choose Characters
            </label>
            <ThemeToggle value={theme} onChange={setTheme} />
          </div>

          <div className="space-y-3">
            <label className="block text-lg font-semibold text-gray-800">
              What should they explain?
            </label>
            <textarea
              className="w-full border border-gray-300 p-5 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-lg"
              rows={5}
              placeholder="e.g., Explain quantum entanglement in simple terms, or How do neural networks work?"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
            />
          </div>

          {status.stage === "idle" && (
            <button
              onClick={handleCreate}
              disabled={!prompt.trim()}
              className="bg-gradient-to-r from-green-500 to-green-600 text-white px-10 py-5 rounded-xl w-full font-bold text-xl hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl">
              🎬 Create Video
            </button>
          )}

          {(status.stage === "queued" || status.stage === "rendering") && (
            <div className="space-y-6 bg-blue-50 p-8 rounded-xl border border-blue-200">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-blue-800 text-lg">Job ID:</span>
                <code className="text-base bg-blue-100 px-3 py-2 rounded-lg text-blue-700">
                  {status.jobId}
                </code>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-base text-blue-700">
                  <span>{status.stage === "queued" ? "Queued..." : "Rendering..."}</span>
                  <span className="font-semibold">{Math.round((status.progress ?? 0) * 100)}%</span>
                </div>
                <div className="w-full bg-blue-100 h-4 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-4 transition-all duration-500 ease-out"
                    style={{ width: `${(status.progress ?? 0) * 100}%` }}
                  />
                </div>
              </div>
              
              <div className="flex items-center justify-center space-x-3 text-blue-600">
                <div className="animate-spin h-6 w-6 border-3 border-blue-600 border-t-transparent rounded-full"></div>
                <span className="text-lg font-medium">
                  {status.stage === "queued" 
                    ? "Waiting in queue..." 
                    : "Generating your video..."
                  }
                </span>
              </div>
            </div>
          )}

          {status.stage === "done" && (
            <div className="space-y-6 bg-green-50 p-8 rounded-xl border border-green-200">
              <div className="flex items-center space-x-3 text-green-700">
                <span className="text-3xl">✅</span>
                <span className="font-bold text-2xl">Video Ready!</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-semibold text-green-800 text-lg">Job ID:</span>
                <code className="text-base bg-green-100 px-3 py-2 rounded-lg text-green-700">
                  {status.jobId}
                </code>
              </div>
              
              <div className="space-y-4">
                <a
                  href={`${process.env.NEXT_PUBLIC_API_BASE}${status.downloadUrl}`}
                  className="bg-gradient-to-r from-purple-500 to-purple-600 text-white px-8 py-4 rounded-xl w-full inline-block text-center font-bold text-lg hover:from-purple-600 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl"
                  download>
                  ⬇️ Download MP4
                </a>
                
                <button
                  onClick={() => setStatus({ stage: "idle" })}
                  className="text-purple-600 hover:text-purple-700 text-lg font-medium underline w-full text-center py-3">
                  Generate another video
                </button>
              </div>
            </div>
          )}

          {status.stage === "error" && (
            <div className="space-y-6 bg-red-50 p-8 rounded-xl border border-red-200">
              <div className="flex items-center space-x-3 text-red-700">
                <span className="text-3xl">❌</span>
                <span className="font-bold text-2xl">Error</span>
              </div>
              
              <p className="text-red-600 text-lg">{status.msg}</p>
              
              <button
                onClick={() => setStatus({ stage: "idle" })}
                className="bg-red-600 text-white px-6 py-4 rounded-xl hover:bg-red-700 transition-colors w-full font-bold text-lg">
                Try Again
              </button>
            </div>
          )}
        </div>

        <div className="text-center text-base text-gray-500 space-y-3 mt-8">
          <p>Powered by OpenAI, ElevenLabs & RabbitMQ</p>
          <p>Characters: Family Guy & Rick and Morty</p>
        </div>
      </main>
    </div>
  );
}
