"use client";

import { useTheme } from "@/contexts/ThemeContext";
import { useVideoCounter } from "@/contexts/VideoCounterContext";
import Navbar from "@/components/Navbar";
import Image from "next/image";

export default function Home() {
  const { darkMode, toggleDarkMode } = useTheme();
  const { videoCount } = useVideoCounter();

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="flex flex-col items-center justify-center min-h-screen px-4 py-20">
        {/* Logo/Brain Image */}
        <div className="mb-8">
          <div className={`w-48 h-48 rounded-full flex items-center justify-center ${darkMode ? 'bg-gray-700' : 'bg-white'} shadow-2xl mb-6`}>
            <Image
              src="/rabbit_reels_logo.png"
              alt="RabbitReels Logo"
              width={120}
              height={120}
              className="rounded-full"
            />
          </div>
        </div>

        {/* Title */}
        <h1 className={`text-6xl font-bold text-center mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          RABBITREELS
        </h1>

        {/* Subtitle */}
        <p className={`text-xl text-center mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          {videoCount.toLocaleString()} videos generated 🐰☠️
        </p>

        {/* Main Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 relative">
          {/* "Star my repo!" callout - positioned above the "Run Locally" button */}
          <div className="absolute -top-10 right-0 sm:right-0 sm:-top-10 text-center sm:transform sm:-translate-x-1/2 sm:left-auto sm:right-[calc(50%-32px)]">
            <span className={`text-xs font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'} bg-white dark:bg-gray-800 px-2 py-1 rounded-full shadow border whitespace-nowrap`}>
              ⭐ Star my repo!
            </span>
          </div>

          {/* FIX: Changed from <Link> to <a> to ensure correct URL navigation */}
          <a href="/generator/">
            <button className="w-full sm:w-auto bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-4 px-8 rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300 text-xl">
              🐰 Create Video
            </button>
          </a>
          <a href="https://github.com/Harshaan-Chugh/RabbitReels" target="_blank" rel="noopener noreferrer">
            <button className={`w-full py-4 px-6 rounded-xl font-bold text-lg border transition-colors ${
              darkMode
                ? 'border-gray-600 text-gray-300 hover:bg-gray-700'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}>
              ⭐ Run Locally (free)
            </button>
          </a>
        </div>

        {/* Footer */}
        <div className={`text-center text-sm mt-16 space-y-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <p>Powered by OpenAI, ElevenLabs & RabbitMQ</p>
          <p>Characters: Family Guy & Rick and Morty</p>
        </div>
      </main>
    </div>
  );
}
