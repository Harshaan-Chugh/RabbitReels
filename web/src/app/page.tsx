"use client";

import { useTheme } from "@/contexts/ThemeContext";
import { useVideoCounter } from "@/contexts/VideoCounterContext";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import Navbar from "@/components/Navbar";
import AnimatedCounter from "@/components/AnimatedCounter";
import Image from "next/image";
import Link from "next/link";

export default function Home() {
  const { darkMode, toggleDarkMode } = useTheme();
  const { videoCount } = useVideoCounter();
  const { isAuthenticated, loading } = useAuth();
  const { credits } = useBilling();

  console.log('Home page render - isAuthenticated:', isAuthenticated, 'loading:', loading, 'credits:', credits);

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="flex flex-col items-center justify-center min-h-screen safe-area-inset pt-32 pb-20">
        <div className="mb-6 sm:mb-8">
          <div className={`w-32 h-32 sm:w-48 sm:h-48 rounded-full flex items-center justify-center ${darkMode ? 'bg-gray-700' : 'bg-white'} shadow-2xl mb-4 sm:mb-6`}>
            <Image
              src="/rabbit_reels_logo.png"
              alt="RabbitReels Logo"
              width={80}
              height={80}
              className="rounded-full sm:w-[120px] sm:h-[120px]"
            />
          </div>
        </div>

        <h1 className={`text-4xl sm:text-6xl font-bold text-center mb-4 px-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          RABBITREELS
        </h1>

        <p className={`text-lg sm:text-xl text-center mb-2 px-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          <AnimatedCounter 
            target={videoCount} 
            duration={2500}
          /> videos generated 🐰☠️
        </p>

        <div className="mt-6 sm:mt-8 flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-4 px-4 w-full max-w-2xl">
          <Link href="/generator" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-4 px-8 rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300 text-lg sm:text-xl min-h-[56px]">
              {isAuthenticated && credits > 0 ? `🐰 Create Video (${credits} credits)` : '🐰 Create Video'}
            </button>
          </Link>
          
          <div className="relative w-full sm:w-auto">
            <div className="absolute -top-3 -right-1 sm:-top-2 sm:-right-1 z-10">
              <span className={`text-xs font-bold ${darkMode ? 'text-blue-400' : 'text-blue-600'} bg-white dark:bg-gray-800 px-2 py-1 rounded-full shadow border whitespace-nowrap`}>
                ⭐ Star my repo!
              </span>
            </div>
            <a href="https://github.com/Harshaan-Chugh/RabbitReels" target="_blank" rel="noopener noreferrer" className="block w-full sm:w-auto">
              <button className={`w-full py-4 px-6 rounded-xl font-bold text-lg border transition-colors min-h-[56px] ${
                darkMode
                  ? 'border-gray-600 text-gray-300 hover:bg-gray-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}>
                ⭐ Run Locally (free)
              </button>
            </a>
          </div>
        </div>

        <div className={`text-center text-sm mt-16 space-y-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <p>Powered by OpenAI, ElevenLabs & RabbitMQ</p>
          <p>Characters: Family Guy & Rick and Morty</p>
        </div>
      </main>
    </div>
  );
}
