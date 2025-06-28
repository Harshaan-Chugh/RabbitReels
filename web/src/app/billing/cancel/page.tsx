"use client";

import { useRouter } from "next/navigation";
import { useTheme } from "@/contexts/ThemeContext";
import Navbar from "@/components/Navbar";

export default function BillingCancelPage() {
  const { darkMode, toggleDarkMode } = useTheme();
  const router = useRouter();

  const handleTryAgain = () => {
    router.push('/billing/');
  };

  const handleGoHome = () => {
    router.push('/');
  };

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="flex flex-col items-center justify-center min-h-screen px-4 py-20">
        <div className={`text-center p-8 rounded-xl shadow-xl max-w-md w-full ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="text-6xl mb-6">😔</div>
          <h1 className={`text-3xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Payment Cancelled
          </h1>
          <p className={`text-lg mb-8 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            No worries! Your payment was cancelled and no charges were made to your account.
          </p>
          
          <div className="space-y-3">
            <button
              onClick={handleTryAgain}
              className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-3 px-6 rounded-full hover:shadow-lg transition-all duration-300"
            >
              Try Again
            </button>
            <button
              onClick={handleGoHome}
              className={`w-full py-3 px-6 rounded-full font-bold transition-all duration-300 ${
                darkMode
                  ? 'bg-gray-700 text-white hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
              }`}
            >
              Go Home
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
