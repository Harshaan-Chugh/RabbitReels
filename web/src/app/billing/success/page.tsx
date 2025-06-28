"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { useTheme } from "@/contexts/ThemeContext";
import Navbar from "@/components/Navbar";

function SuccessContent() {
  const { darkMode } = useTheme();
  const { isAuthenticated, authenticatedFetch } = useAuth();
  const { refreshBalance } = useBilling();
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'needs_manual_processing'>('loading');
  const [message, setMessage] = useState('');
  const [credits, setCredits] = useState(0);
  const [currentBalance, setCurrentBalance] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const sessionIdParam = searchParams.get('session_id');
    
    if (!sessionIdParam) {
      setStatus('error');
      setMessage('No session ID provided');
      return;
    }

    setSessionId(sessionIdParam);

    const verifyPayment = async () => {
      try {
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';
        const response = await fetch(`${API_BASE_URL}/billing/success?session_id=${sessionIdParam}`);
        
        if (response.ok) {
          const data = await response.json();
          setMessage(data.message);
          setCredits(data.credits || 0);
          setCurrentBalance(data.current_balance || 0);
          
          // Handle different statuses from the API
          if (data.status === 'needs_manual_processing') {
            setStatus('needs_manual_processing');
          } else if (data.status === 'success') {
            setStatus('success');
          
          // Refresh the user's balance
          if (isAuthenticated) {
            setTimeout(() => {
              refreshBalance();
            }, 2000);
            }
          } else {
            setStatus('error');
            setMessage(data.message || 'Unknown payment status');
          }
        } else {
          setStatus('error');
          setMessage('Failed to verify payment');
        }
      } catch (error) {
        console.error('Error verifying payment:', error);
        setStatus('error');
        setMessage('Error verifying payment');
      }
    };

    verifyPayment();
  }, [searchParams, isAuthenticated, refreshBalance]);

  const handleManualProcessing = async () => {
    if (!sessionId || !authenticatedFetch) {
      setMessage('Unable to process payment manually');
      return;
    }

    setIsProcessing(true);
    
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';
      const response = await authenticatedFetch(`${API_BASE_URL}/billing/process-payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (response.ok) {
        const data = await response.json();
        setStatus('success');
        setMessage(data.message);
        setCurrentBalance(data.new_balance);
        
        // Refresh the user's balance
        setTimeout(() => {
          refreshBalance();
        }, 1000);
      } else {
        const errorData = await response.json();
        setMessage(errorData.detail || 'Failed to process payment manually');
      }
    } catch (error) {
      console.error('Error processing payment manually:', error);
      setMessage('Error processing payment manually');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleContinue = () => {
    router.push('/generator');
  };

  const handleViewBilling = () => {
    router.push('/billing/');
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4 py-20">
      <div className={`text-center p-8 rounded-xl shadow-xl max-w-md w-full ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-pink-500 border-t-transparent mx-auto mb-6"></div>
            <h1 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Verifying Payment...
            </h1>
            <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Please wait while we confirm your purchase.
            </p>
          </>
        )}

        {status === 'needs_manual_processing' && (
          <>
            <div className="text-6xl mb-6">⚠️</div>
            <h1 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Payment Needs Processing
            </h1>
            <p className={`text-sm mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Your payment was successful, but we need to manually process it in development mode.
            </p>
            <div className={`p-4 rounded-lg mb-6 ${darkMode ? 'bg-yellow-900 bg-opacity-20 border border-yellow-600' : 'bg-yellow-100 border border-yellow-300'}`}>
              <div className="text-lg font-bold text-yellow-600">
                {credits} Credits Purchased
              </div>
              <div className="text-sm text-yellow-600 mt-1">
                Click below to activate them
              </div>
            </div>
            <div className="space-y-3">
              <button
                onClick={handleManualProcessing}
                disabled={isProcessing}
                className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-bold py-3 px-6 rounded-full hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? (
                  <>
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    Processing...
                  </>
                ) : (
                  '✅ Activate Credits'
                )}
              </button>
              <button
                onClick={handleViewBilling}
                className={`w-full py-3 px-6 rounded-full font-bold transition-all duration-300 ${
                  darkMode
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                View Billing
              </button>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="text-6xl mb-6">🎉</div>
            <h1 className={`text-3xl font-bold mb-4 text-green-500`}>
              Payment Successful!
            </h1>
            <p className={`text-lg mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              {message}
            </p>
            {credits > 0 && (
              <div className={`p-4 rounded-lg mb-6 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
                <div className="text-2xl font-bold text-gradient bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent">
                  +{credits} Credits Added
                </div>
                {currentBalance > 0 && (
                  <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Total Balance: {currentBalance} credits
                  </div>
                )}
              </div>
            )}
            <div className="space-y-3">
              <button
                onClick={handleContinue}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-3 px-6 rounded-full hover:shadow-lg transition-all duration-300"
              >
                🐰 Create Your First Video
              </button>
              <button
                onClick={handleViewBilling}
                className={`w-full py-3 px-6 rounded-full font-bold transition-all duration-300 ${
                  darkMode
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                View Billing
              </button>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="text-6xl mb-6">❌</div>
            <h1 className={`text-3xl font-bold mb-4 text-red-500`}>
              Payment Error
            </h1>
            <p className={`text-lg mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              {message}
            </p>
            <div className="space-y-3">
              <button
                onClick={handleViewBilling}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-3 px-6 rounded-full hover:shadow-lg transition-all duration-300"
              >
                Try Again
              </button>
              <button
                onClick={() => router.push('/')}
                className={`w-full py-3 px-6 rounded-full font-bold transition-all duration-300 ${
                  darkMode
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                Go Home
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default function BillingSuccessPage() {
  const { darkMode, toggleDarkMode } = useTheme();

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <Suspense fallback={
        <main className="flex flex-col items-center justify-center min-h-screen px-4 py-20">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-pink-500 border-t-transparent"></div>
        </main>
      }>
        <SuccessContent />
      </Suspense>
    </div>
  );
}
