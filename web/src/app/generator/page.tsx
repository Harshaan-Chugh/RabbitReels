"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import ThemeToggle from "@/components/ThemeToggle";
import Navbar from "@/components/Navbar";
import { useVideoCounter } from "@/contexts/VideoCounterContext";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { v4 as uuid } from "uuid";
import { useRouter } from "next/navigation";

type Status =
  | { stage: "idle" }
  | { stage: "queued" | "rendering"; jobId: string; progress?: number }
  | { stage: "done"; jobId: string; downloadUrl: string }
  | { stage: "error"; msg: string };

const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost';
const API_BASE_URL = RAW_BASE.endsWith('/api') ? RAW_BASE : `${RAW_BASE}/api`;

export default function Generator() {
  const [theme, setTheme] = useState<"family_guy" | "rick_and_morty">("family_guy");
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<Status>({ stage: "idle" });
  const { darkMode, toggleDarkMode } = useTheme();
  const { authenticatedFetch, isAuthenticated, login } = useAuth();
  const { credits, refreshBalance } = useBilling();
  const { refreshVideoCount } = useVideoCounter();
  const router = useRouter();

  useEffect(() => {
    if (status.stage !== "queued" && status.stage !== "rendering") return;
    const id = status.jobId;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/videos/${id}`);
        if (!r.ok) return;
        const js = await r.json();
        if (js.status === "done") {
          setStatus({ stage: "done", jobId: id, downloadUrl: js.download_url });
          refreshVideoCount();
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
  const handleCreate = async () => {
    if (!prompt.trim()) return alert("Enter a prompt!");
    
    if (!isAuthenticated) {
      alert("Please log in to create videos!");
      login();
      return;
    }
    
    if (credits <= 0) {
      alert("You need credits to create videos! Redirecting to billing page...");
      router.push("/billing/");
      return;
    }
    
    const jobId = uuid();
    const body = { job_id: jobId, prompt, character_theme: theme };
    
    try {
      const r = await authenticatedFetch(`${API_BASE_URL}/videos`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const errorData = await r.json().catch(() => ({ detail: "Unknown error" }));
        if (r.status === 402) {
          alert("Insufficient credits! Redirecting to billing page...");
          router.push("/billing/");
          return;
        }
        return alert(`Error: ${errorData.detail || "Failed to create video"}`);
      }
      refreshBalance();
      setStatus({ stage: "queued", jobId });
    } catch (error) {
      alert(`Network error: ${error}`);
    }
  };

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="container mx-auto safe-area-inset pt-32 sm:pt-32 pb-20 max-w-4xl" style={{ paddingTop: 'max(128px, calc(128px + env(safe-area-inset-top)))' }}>        <div className="text-center space-y-4 mb-6 sm:mb-8">
          <h1 className={`text-3xl sm:text-5xl font-bold bg-gradient-to-r ${darkMode ? 'from-blue-400 to-purple-400' : 'from-blue-600 to-purple-600'} bg-clip-text text-transparent flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4`}>
            <Link href="/" className="hover:scale-110 transition-transform">
              <Image
                src="/rabbit_reels_logo.png"
                alt="RabbitReels Logo"
                width={50}
                height={50}
                className="rounded-full sm:w-[60px] sm:h-[60px]"
              />
            </Link>
            <span className="text-center">RabbitReels Generator</span>
          </h1>          <p className={`text-lg sm:text-xl px-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Create AI-powered short videos with your favorite characters
          </p>
          {isAuthenticated && (
            <div className={`inline-block px-4 py-2 rounded-lg ${
              credits > 0 
                ? darkMode ? 'bg-green-900 text-green-300' : 'bg-green-100 text-green-800'
                : darkMode ? 'bg-red-900 text-red-300' : 'bg-red-100 text-red-800'
            }`}>              💳 Credits: <span className="font-bold">{credits}</span>
              {credits === 0 && (
                <Link href="/billing/" className="ml-2 underline hover:no-underline">
                  Buy more
                </Link>
              )}
            </div>
          )}
        </div>

        <div className={`rounded-xl p-4 sm:p-8 shadow-xl space-y-6 sm:space-y-8 card ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="space-y-3">
            <label className={`block text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              Choose Characters
            </label>
            <ThemeToggle value={theme} onChange={setTheme} darkMode={darkMode} />
          </div>

          <div className="space-y-3">
            <label className={`block text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              What should they explain?
            </label>
            <textarea
              className={`w-full border p-4 sm:p-5 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-base sm:text-lg ${
                darkMode 
                  ? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400' 
                  : 'border-gray-300 bg-white text-gray-900 placeholder-gray-500'
              }`}
              rows={4}
              placeholder="e.g., Explain quantum entanglement in simple terms, or How do neural networks work?"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
            />
          </div>

          {status.stage === "idle" && (
            <button
              onClick={handleCreate}
              disabled={!prompt.trim()}
              className="bg-gradient-to-r from-green-500 to-green-600 text-white px-6 sm:px-10 py-4 sm:py-5 rounded-xl w-full font-bold text-lg sm:text-xl hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl min-h-[56px]">
              🐰 Create Video
            </button>
          )}

          {(status.stage === "queued" || status.stage === "rendering") && (
            <div className={`space-y-6 p-8 rounded-xl border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-blue-50 border-blue-200'}`}>
              <div className="flex items-center justify-between">
                <span className={`font-semibold text-lg ${darkMode ? 'text-gray-200' : 'text-blue-800'}`}>Job ID:</span>
                <code className={`text-base px-3 py-2 rounded-lg ${darkMode ? 'bg-gray-600 text-gray-200' : 'bg-blue-100 text-blue-700'}`}>
                  {status.jobId}
                </code>
              </div>
              
              <div className="space-y-3">
                <div className={`flex justify-between text-base ${darkMode ? 'text-gray-300' : 'text-blue-700'}`}>
                  <span>{status.stage === "queued" ? "Queued..." : "Rendering..."}</span>
                  <span className="font-semibold">{Math.round((status.progress ?? 0) * 100)}%</span>
                </div>
                <div className={`w-full h-4 rounded-full overflow-hidden ${darkMode ? 'bg-gray-600' : 'bg-blue-100'}`}>
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-4 transition-all duration-500 ease-out"
                    style={{ width: `${(status.progress ?? 0) * 100}%` }}
                  />
                </div>
              </div>
              
              <div className={`flex items-center justify-center space-x-3 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                <div className={`animate-spin h-6 w-6 border-3 border-t-transparent rounded-full ${darkMode ? 'border-blue-400' : 'border-blue-600'}`}></div>
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
            <div className={`space-y-6 p-8 rounded-xl border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-green-50 border-green-200'}`}>
              <div className={`flex items-center space-x-3 ${darkMode ? 'text-green-400' : 'text-green-700'}`}>
                <span className="text-3xl">✅</span>
                <span className="font-bold text-2xl">Video Ready!</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className={`font-semibold text-lg ${darkMode ? 'text-gray-200' : 'text-green-800'}`}>Job ID:</span>
                <code className={`text-base px-3 py-2 rounded-lg ${darkMode ? 'bg-gray-600 text-gray-200' : 'bg-green-100 text-green-700'}`}>
                  {status.jobId}
                </code>
              </div>
              
              <div className="space-y-4">
                <a
                  href={`${API_BASE_URL}${status.downloadUrl.startsWith('/api/') ? status.downloadUrl.substring(4) : status.downloadUrl}`}
                  className="bg-gradient-to-r from-purple-500 to-purple-600 text-white px-8 py-4 rounded-xl w-full inline-block text-center font-bold text-lg hover:from-purple-600 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl"
                  download>
                  ⬇️ Download MP4
                </a>
                
                <button
                  onClick={() => setStatus({ stage: "idle" })}
                  className={`text-lg font-medium underline w-full text-center py-3 ${darkMode ? 'text-purple-400 hover:text-purple-300' : 'text-purple-600 hover:text-purple-700'}`}>
                  Generate another video
                </button>
              </div>
            </div>
          )}

          {status.stage === "error" && (
            <div className={`space-y-6 p-8 rounded-xl border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-red-50 border-red-200'}`}>
              <div className={`flex items-center space-x-3 ${darkMode ? 'text-red-400' : 'text-red-700'}`}>
                <span className="text-3xl">❌</span>
                <span className="font-bold text-2xl">Error</span>
              </div>
              
              <p className={`text-lg ${darkMode ? 'text-red-400' : 'text-red-600'}`}>{status.msg}</p>
              
              <button
                onClick={() => setStatus({ stage: "idle" })}
                className={`px-6 py-4 rounded-xl transition-colors w-full font-bold text-lg ${darkMode ? 'bg-red-600 hover:bg-red-700' : 'bg-red-600 hover:bg-red-700'} text-white`}>
                Try Again
              </button>
            </div>
          )}
        </div>

        <div className={`text-center text-base space-y-3 mt-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <p>Powered by OpenAI, ElevenLabs & RabbitMQ</p>
          <p>Characters: Family Guy & Rick and Morty</p>
        </div>
      </main>
    </div>
  );
}
