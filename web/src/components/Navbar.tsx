"use client";

import { useState } from "react";

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
}

export default function Navbar({ darkMode, toggleDarkMode }: NavbarProps) {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  const handleGoogleAuth = () => {
    // TODO: Implement Google OAuth
    console.log("Google auth not implemented yet");
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement form authentication
    console.log("Form auth not implemented yet");
  };

  return (
    <>
      <nav className={`fixed top-0 left-0 right-0 z-50 ${darkMode ? 'bg-gray-900/95' : 'bg-white/95'} backdrop-blur-sm border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          {/* Logo/Brand */}
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🐰</span>
            <span className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              RabbitReels
            </span>
          </div>

          {/* Right side buttons */}
          <div className="flex items-center space-x-4">
            {/* Auth buttons */}
            <button
              onClick={() => {
                setIsLogin(true);
                setShowAuthModal(true);
              }}
              className={`px-4 py-2 rounded-lg transition-colors ${
                darkMode
                  ? 'text-gray-300 hover:text-white hover:bg-gray-800'
                  : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Log in
            </button>
            <button
              onClick={() => {
                setIsLogin(false);
                setShowAuthModal(true);
              }}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                darkMode
                  ? 'border-gray-600 text-gray-300 hover:bg-gray-800'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Sign up
            </button>

            {/* Dark mode toggle */}
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg transition-colors ${
                darkMode
                  ? 'text-gray-300 hover:text-white hover:bg-gray-800'
                  : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {darkMode ? "☀️" : "🌙"}
            </button>
          </div>
        </div>
      </nav>

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className={`w-full max-w-md rounded-xl p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex justify-between items-center mb-6">
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {isLogin ? 'Log in' : 'Sign up'}
              </h2>
              <button
                onClick={() => setShowAuthModal(false)}
                className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}
              >
                ×
              </button>
            </div>

            {/* Google Auth Button */}
            <button
              onClick={handleGoogleAuth}
              className={`w-full flex items-center justify-center space-x-3 p-3 rounded-lg border transition-colors mb-4 ${
                darkMode
                  ? 'border-gray-600 hover:bg-gray-700 text-white'
                  : 'border-gray-300 hover:bg-gray-50 text-gray-900'
              }`}
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className={`text-center mb-4 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              or
            </div>

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="space-y-4">
              <input
                type="email"
                placeholder="Email"
                className={`w-full p-3 rounded-lg border ${
                  darkMode
                    ? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400'
                    : 'border-gray-300 bg-white text-gray-900 placeholder-gray-500'
                } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                required
              />
              <input
                type="password"
                placeholder="Password"
                className={`w-full p-3 rounded-lg border ${
                  darkMode
                    ? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400'
                    : 'border-gray-300 bg-white text-gray-900 placeholder-gray-500'
                } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                required
              />
              <button
                type="submit"
                className="w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                {isLogin ? 'Log in' : 'Sign up'}
              </button>
            </form>

            <div className={`text-center mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                {isLogin ? 'Sign up' : 'Log in'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
