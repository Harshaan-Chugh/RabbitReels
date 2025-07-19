"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { useVideoCounter } from "@/contexts/VideoCounterContext";
import { useVideoHistory } from "@/contexts/VideoHistoryContext";
import Image from "next/image";
import Link from "next/link";
import CelebrationDialog from './CelebrationDialog';
import clsx from "clsx";
import { useTheme } from "@/contexts/ThemeContext";

interface NavbarProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
}

function CodeInput({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const { darkMode } = useTheme();
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, idx: number) => {
    const val = e.target.value.replace(/\D/g, "");
    if (!val) return;
    const newValue = value.substring(0, idx) + val[0] + value.substring(idx + 1);
    onChange(newValue);
    if (val && idx < 5) inputs.current[idx + 1]?.focus();
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, idx: number) => {
    if (e.key === "Backspace" && !value[idx] && idx > 0) {
      onChange(value.substring(0, idx - 1) + value.substring(idx));
      inputs.current[idx - 1]?.focus();
    }
  };
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData("Text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) onChange(pasted);
  };
  return (
    <div className="flex gap-2 justify-center mt-4 mb-2">
      {[...Array(6)].map((_, idx) => (
        <input
          key={idx}
          ref={el => { inputs.current[idx] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value[idx] || ""}
          onChange={e => handleChange(e, idx)}
          onKeyDown={e => handleKeyDown(e, idx)}
          onPaste={handlePaste}
          disabled={disabled}
          className={clsx("w-10 h-12 text-2xl text-center rounded-md border focus:outline-none font-mono",
            darkMode ? "bg-gray-700 border-gray-600 text-white" : "bg-gray-100 border-gray-300 text-gray-900")}
        />
      ))}
    </div>
  );
}

export default function Navbar({ darkMode, toggleDarkMode }: NavbarProps) {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showVideoHistory, setShowVideoHistory] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({ email: '', password: '', name: '' });
  const { user, profile, isAuthenticated, login, logout, loading, emailLogin, validateToken } = useAuth();
  const { credits, loading: creditsLoading, refreshBalance } = useBilling();
  const { videoCount } = useVideoCounter();
  const { videos, loading: videoHistoryLoading, fetchVideos } = useVideoHistory();
  const profileMenuRef = useRef<HTMLDivElement>(null);// Close profile menu when clicking outside
  const [showCelebration, setShowCelebration] = useState(false);
  const [signupStep, setSignupStep] = useState<1 | 2>(1);
  const [verificationCode, setVerificationCode] = useState("");

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };  }, []);

  useEffect(() => {
    if (
      isAuthenticated &&
      user?.sub &&
      credits === 1 &&
      videoCount === 0 &&
      !loading &&
      !creditsLoading
    ) {
      const flagKey = `celebration_shown_${user.sub}`;
      if (!localStorage.getItem(flagKey) && !showCelebration) {
        setShowCelebration(true);
      }
    }
  }, [isAuthenticated, user, credits, videoCount, loading, creditsLoading, showCelebration]);

  const handleGoogleAuth = () => {
    login();
  };  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError(null);

    try {
      if (isLogin) {
        const result = await emailLogin(formData.email, formData.password);
        if (result.success) {
          setShowAuthModal(false);
          setFormData({ email: '', password: '', name: '' });
          setFormError(null);
          setShowCelebration(true);
          await refreshBalance?.();
          window.dispatchEvent(new Event('auth-refresh'));
        } else if (result.error) {
          setFormError(result.error);
        } else {
          setFormError('Authentication failed');
        }
      } else {
        if (signupStep === 1) {
          const res = await fetch('/api/auth/request-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: formData.email })
          });
          if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || data.message || 'Failed to send code');
          }
          setSignupStep(2);
          return;
        } else {
          const res = await fetch('/api/auth/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: formData.email, password: formData.password, name: formData.name, code: verificationCode })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.message || 'Verification failed');
          const token = data.access_token;
          localStorage.setItem('jwt_token', token);
          await validateToken(token);
          await refreshBalance?.();
        setShowAuthModal(false);
        setFormData({ email: '', password: '', name: '' });
          setVerificationCode('');
          setSignupStep(1);
          setShowCelebration(true);
        window.dispatchEvent(new Event('auth-refresh'));
        }
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error');
    } finally {
      setFormLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (formError) {
      setFormError(null);
    }
  };

  const handleCelebrationClose = () => {
    if (user?.sub) {
      localStorage.setItem(`celebration_shown_${user.sub}`, 'true');
    }
    setShowCelebration(false);
  };

  return (
    <>
      <nav className={`fixed top-0 left-0 right-0 z-50 ${darkMode ? 'bg-gray-900/95' : 'bg-white/95'} backdrop-blur-sm border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'} safe-area-top`}>
        <div className="container mx-auto safe-area-inset py-2 flex items-center justify-between">          {/* Logo/Brand */}
          <Link href="/" className="flex items-center space-x-2 hover:opacity-80 transition-opacity min-h-[44px]">
            <Image 
              src="/rabbit_reels_logo.png" 
              alt="RabbitReels Logo" 
              width={32} 
              height={32}
              className="rounded"
            />
            <span className={`text-lg sm:text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              RabbitReels
            </span>
          </Link>          {/* Right side buttons */}
          <div className="flex items-center space-x-2 sm:space-x-4">
            {loading ? (
              <div className="animate-pulse flex space-x-4">
                <div className="rounded-full bg-gray-300 h-8 w-8"></div>
              </div>
            ) : isAuthenticated ? (
              <>                {/* Credits Display */}
                <Link 
                  href="/billing/"
                  className={`flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 py-2 rounded-lg transition-colors min-h-[44px] ${
                    darkMode 
                      ? 'bg-gray-800 text-white hover:bg-gray-700' 
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  <span className="text-xs sm:text-sm font-medium">
                    {creditsLoading ? '...' : credits} <span className="hidden sm:inline">Credits</span>
                  </span>
                  <span className="text-xs">💳</span>
                </Link>

                {/* User Profile Menu */}
                <div className="relative" ref={profileMenuRef}>
                <button
                  onClick={() => setShowProfileMenu(!showProfileMenu)}
                  className="flex items-center space-x-1 sm:space-x-3 px-2 sm:px-3 py-2 rounded-lg hover:bg-opacity-10 hover:bg-gray-500 transition-colors min-h-[44px]"
                >                  {profile?.picture ? (
                    <Image
                      src={profile.picture}
                      alt={user?.name || 'User'}
                      width={32}
                      height={32}
                      className="rounded-full"
                    />
                  ) : (
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${darkMode ? 'bg-gray-600 text-white' : 'bg-gray-300 text-gray-700'}`}>
                      {user?.name?.charAt(0).toUpperCase() || 'U'}
                    </div>
                  )}
                  <span className={`hidden md:block text-sm ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {user?.name}
                  </span>
                  <svg className={`w-4 h-4 transition-transform ${showProfileMenu ? 'rotate-180' : ''} ${darkMode ? 'text-white' : 'text-gray-900'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Profile Dropdown */}
                {showProfileMenu && (
                  <div className={`absolute right-0 mt-2 w-64 rounded-lg shadow-lg ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border z-50`}>
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center space-x-3">                        {profile?.picture ? (
                          <Image
                            src={profile.picture}
                            alt={user?.name || 'User'}
                            width={40}
                            height={40}
                            className="rounded-full"
                          />
                        ) : (
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-semibold ${darkMode ? 'bg-gray-600 text-white' : 'bg-gray-300 text-gray-700'}`}>
                            {user?.name?.charAt(0).toUpperCase() || 'U'}
                          </div>
                        )}
                        <div>
                          <p className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                            {user?.name}
                          </p>
                          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {user?.email}
                          </p>
                        </div>
                      </div>                    </div>
                    <div className="py-1">
                      <button
                        onClick={() => {
                          setShowVideoHistory(true);
                          setShowProfileMenu(false);
                          fetchVideos(); // Refresh videos when opening modal
                        }}
                        className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
                      >
                        📽️ My Videos
                      </button>
                      <Link
                        href="/billing/"
                        className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
                        onClick={() => setShowProfileMenu(false)}
                      >
                        💳 Billing & Credits
                      </Link>
                      <button
                        onClick={() => {
                          logout();
                          setShowProfileMenu(false);
                        }}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
                      >
                        Sign out
                      </button>
                    </div>
                  </div>                )}
              </div>
              </>
            ) : (
              /* Auth buttons for unauthenticated users */              <>                <button
                  onClick={() => {
                    setIsLogin(true);
                    setShowAuthModal(true);
                    setFormData({ email: '', password: '', name: '' });
                    setFormError(null);
                  }}
                  className={`px-3 sm:px-4 py-2 rounded-lg transition-colors min-h-[44px] text-sm sm:text-base ${
                    darkMode
                      ? 'text-gray-300 hover:text-white hover:bg-gray-800'
                      : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Log in
                </button>
                <div className="flex items-center space-x-1 sm:space-x-2">
                <button
                  onClick={() => {
                    setIsLogin(false);
                    setShowAuthModal(true);
                    setFormData({ email: '', password: '', name: '' });
                    setFormError(null);
                  }}
                  className={`px-3 sm:px-4 py-2 rounded-lg border transition-colors min-h-[44px] text-sm sm:text-base ${
                    darkMode
                      ? 'border-gray-600 text-gray-300 hover:bg-gray-800'
                      : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  Sign up
                </button>
                  <span className={`hidden sm:inline-block px-2 sm:px-3 py-1 rounded-full text-xs font-semibold ${darkMode ? 'bg-pink-900/60 text-pink-200' : 'bg-pink-100 text-pink-600'}`}>🎁 1 free video credit for new users!</span>
                </div>
              </>
            )}

            {/* Dark mode toggle */}
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg transition-colors min-h-[44px] min-w-[44px] ${
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 safe-area-inset">
          <div className={`w-full max-w-md rounded-xl p-4 sm:p-6 modal ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex justify-between items-center mb-6">
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {isLogin ? 'Log in' : 'Sign up'}
              </h2>              <button
                onClick={() => {
                  setShowAuthModal(false);
                  setFormData({ email: '', password: '', name: '' });
                  setFormError(null);
                }}
                className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}
              >
                ×
              </button>
            </div>

            {!isLogin && (
              <div className={`mb-4 text-center text-sm font-semibold ${darkMode ? 'text-pink-300' : 'text-pink-600'}`}>🎁 Get 1 free video credit when you sign up!</div>
            )}

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
            </div>            {/* Form */}
            <form onSubmit={handleFormSubmit} className="space-y-4">
              {!isLogin && signupStep === 1 && (
                <>
                <input
                  type="text"
                  name="name"
                  placeholder="Full Name"
                  value={formData.name}
                  onChange={handleInputChange}
                    className={`w-full p-3 rounded-lg border ${darkMode? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400':'border-gray-300 bg-white text-gray-900 placeholder-gray-500'} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    required
                    disabled={formLoading}
                  />
                  <input
                    type="email"
                    name="email"
                    placeholder="Email"
                    value={formData.email}
                    onChange={handleInputChange}
                    className={`w-full p-3 rounded-lg border ${darkMode? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400':'border-gray-300 bg-white text-gray-900 placeholder-gray-500'} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    required
                    disabled={formLoading}
                  />
                  <input
                    type="password"
                    name="password"
                    placeholder="Password"
                    value={formData.password}
                    onChange={handleInputChange}
                    className={`w-full p-3 rounded-lg border ${darkMode? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400':'border-gray-300 bg-white text-gray-900 placeholder-gray-500'} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                    required
                  disabled={formLoading}
                />
                </>
              )}

              {isLogin && (
                <>
              <input
                type="email"
                name="email"
                placeholder="Email"
                value={formData.email}
                onChange={handleInputChange}
                    className={`w-full p-3 rounded-lg border ${darkMode? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400':'border-gray-300 bg-white text-gray-900 placeholder-gray-500'} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                required
                disabled={formLoading}
              />
              <input
                type="password"
                name="password"
                placeholder="Password"
                value={formData.password}
                onChange={handleInputChange}
                    className={`w-full p-3 rounded-lg border ${darkMode? 'border-gray-600 bg-gray-700 text-white placeholder-gray-400':'border-gray-300 bg-white text-gray-900 placeholder-gray-500'} focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                required
                disabled={formLoading}
              />
                </>
              )}

              {!isLogin && signupStep === 2 && (
                <>
                  <div className={`text-sm text-center ${darkMode?'text-gray-300':'text-gray-700'}`}>Enter the 6-digit verification code sent to your email.</div>
                  <CodeInput value={verificationCode} onChange={setVerificationCode} disabled={formLoading}/>
                </>
              )}
              
              {formError && (
                <div className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
                  {formError}
                </div>
              )}
              
              <button
                type="submit"
                disabled={formLoading}
                className="w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {formLoading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{isLogin ? 'Logging in...' : signupStep===1 ? 'Send code' : 'Verify'}</span>
                  </div>
                ) : (
                  isLogin ? 'Log in' : signupStep===1 ? 'Send verification code' : 'Verify & Sign up'
                )}
              </button>
            </form>            <div className={`text-center mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  setFormData({ email: '', password: '', name: '' });
                  setFormError(null);
                }}
                className="text-blue-600 hover:text-blue-700 font-medium"
                disabled={formLoading}
              >
                {isLogin ? 'Sign up' : 'Log in'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Video History Modal */}
      {showVideoHistory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 safe-area-inset">
          <div className={`w-full max-w-4xl max-h-[80vh] rounded-xl modal ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex justify-between items-center p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                My Videos
              </h2>
              <button
                onClick={() => setShowVideoHistory(false)}
                className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}
              >
                ×
              </button>
            </div>
            
            <div className="p-4 sm:p-6 max-h-[60vh] overflow-y-auto">
              {videoHistoryLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span className={`ml-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Loading videos...</span>
                </div>
              ) : videos.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-4xl mb-4">🎬</div>
                  <p className={`text-lg ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>No videos yet</p>
                  <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Create your first video to see it here!
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {videos.map((video) => {
                    const getThemeImage = (theme: string) => {
                      if (theme === "family_guy") return "/family_guy.jpeg";
                      if (theme === "rick_and_morty") return "/rick_and_morty.jpeg";
                      return "";
                    };
                    
                    const formatThemeName = (theme: string) => {
                      if (theme === "family_guy") return "Family Guy";
                      if (theme === "rick_and_morty") return "Rick And Morty";
                      return theme.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase());
                    };
                    
                    return (
                      <div
                        key={video.id}
                        className={`rounded-lg border transition-all hover:shadow-md overflow-hidden ${
                          darkMode 
                            ? 'border-gray-600 bg-gray-700 hover:bg-gray-600' 
                            : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                        }`}
                      >
                        {/* Character Theme Image Header */}
                        <div 
                          className="h-32 relative"
                          style={{
                            backgroundImage: `url(${getThemeImage(video.character_theme)})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                          }}
                        >
                          <div className={`absolute inset-0 ${
                            darkMode ? 'bg-gray-900/70' : 'bg-black/50'
                          }`} />
                          <div className="absolute top-2 left-2 right-2 flex justify-between items-start">
                            <span className="text-white font-bold text-sm drop-shadow-lg">
                              {formatThemeName(video.character_theme)}
                            </span>
                            <div className={`text-xs px-2 py-1 rounded-full ${
                              video.status === 'done' 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                : video.status === 'error'
                                ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                : video.status === 'rendering'
                                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-200'
                            }`}>
                              {video.status}
                            </div>
                          </div>
                        </div>
                        
                        {/* Content */}
                        <div className="p-4">
                          <p className={`text-sm mb-3 font-medium ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                            {video.prompt.length > 120 ? video.prompt.substring(0, 120) + '...' : video.prompt}
                          </p>
                          
                          <div className="flex justify-between items-center">
                            <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                              {new Date(video.created_at).toLocaleDateString()}
                            </span>
                            
                                                        {video.status === 'done' && video.download_url && (
                              <a
                                href={`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost'}${video.download_url.startsWith('/api/') ? video.download_url.substring(4) : video.download_url}`}    
                                download
                                className="text-xs px-4 py-2 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold hover:shadow-lg transition-all duration-300 hover:from-pink-600 hover:to-purple-700"
                              >
                                Download
                              </a>
                            )}
                            
                            {video.status === 'error' && (
                              <span className={`text-xs ${darkMode ? 'text-red-400' : 'text-red-500'}`}>
                                Failed
                              </span>
                            )}
                            
                            {video.status === 'rendering' && (
                              <span className={`text-xs ${darkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
                                Processing...
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            
            <div className="p-4 sm:p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => {
                  fetchVideos();
                }}
                disabled={videoHistoryLoading}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  darkMode
                    ? 'bg-gray-600 text-white hover:bg-gray-500 disabled:bg-gray-700'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:bg-gray-100'
                }`}
              >
                {videoHistoryLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Celebration Dialog */}
      {showCelebration && (
        <CelebrationDialog
          open={showCelebration}
          onClose={handleCelebrationClose}
          darkMode={darkMode}
        />
      )}
    </>
  );
}
