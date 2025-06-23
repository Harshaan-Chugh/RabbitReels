"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { useTheme } from "@/contexts/ThemeContext";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import Image from "next/image";

export default function BillingPage() {
  const { darkMode, toggleDarkMode } = useTheme();
  const { isAuthenticated, login, user } = useAuth();
  const { credits, creditPackages, purchaseCredits, refreshBalance, loading } = useBilling();
  const [purchasing, setPurchasing] = useState<number | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      refreshBalance();
    }
  }, [isAuthenticated, refreshBalance]);

  const handlePurchase = async (packageCredits: number) => {
    try {
      setPurchasing(packageCredits);
      await purchaseCredits(packageCredits);
    } catch (error) {
      console.error("Purchase failed:", error);
      alert("Purchase failed. Please try again.");
    } finally {
      setPurchasing(null);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
        <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
        
        <main className="flex flex-col items-center justify-center min-h-screen px-4 py-20">
          <div className={`text-center p-8 rounded-xl shadow-xl ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <h1 className={`text-4xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Please Sign In
            </h1>
            <p className={`text-lg mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              You need to be signed in to access billing information.
            </p>
            <button
              onClick={login}
              className="bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-3 px-6 rounded-full hover:shadow-lg transition-all duration-300"
            >
              Sign In with Google
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 'bg-gradient-to-br from-blue-50 to-purple-50'}`}>
      <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      
      <main className="container mx-auto px-4 py-20">        {/* Header */}
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center space-x-3 mb-6 hover:opacity-80 transition-opacity">
            <Image 
              src="/rabbit_reels_logo.png" 
              alt="RabbitReels Logo" 
              width={60} 
              height={60}
              className="rounded-lg"
            />
            <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              RabbitReels
            </span>
          </Link>
          <h1 className={`text-5xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Credits & Billing
          </h1>
          <p className={`text-xl ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Fuel your creativity with AI-powered video generation
          </p>
        </div>

        {/* Current Balance */}
        <div className="flex justify-center mb-12">
          <div className={`p-6 rounded-xl shadow-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} text-center`}>
            <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Current Balance
            </h2>
            {loading ? (
              <div className="animate-pulse">
                <div className={`h-8 w-20 mx-auto rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
              </div>
            ) : (
              <div className="text-4xl font-bold text-gradient bg-gradient-to-r from-pink-500 to-purple-600 bg-clip-text text-transparent">
                {credits} Credits
              </div>
            )}
            <p className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              1 credit = 1 video generation
            </p>
          </div>
        </div>

        {/* Credit Packages */}
        <div className="max-w-4xl mx-auto">
          <h2 className={`text-3xl font-bold text-center mb-8 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Purchase Credits
          </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {creditPackages.map((pkg) => (
              <div
                key={pkg.credits}
                className={`relative p-6 rounded-xl shadow-xl transition-all duration-300 hover:shadow-2xl hover:-translate-y-2 ${
                  pkg.popular 
                    ? `ring-2 ring-pink-500 ${darkMode ? 'bg-gradient-to-br from-pink-900/30 to-purple-900/30' : 'bg-gradient-to-br from-pink-50 to-purple-50'}` 
                    : darkMode ? 'bg-gray-800' : 'bg-white'
                }`}
              >
                {pkg.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10">
                    <span className="bg-gradient-to-r from-pink-500 to-purple-600 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg">
                      MOST POPULAR
                    </span>
                  </div>
                )}                
                <div className={`text-center ${pkg.popular ? 'pt-4' : 'pt-0'}`}>
                  <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {pkg.credits} Credits
                  </h3>
                  
                  <div className="mb-4">
                    <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      ${pkg.price_dollars}
                    </div>
                    {pkg.savings_percent > 0 && (
                      <div className="text-green-500 text-sm font-semibold">
                        Save {pkg.savings_percent}%
                      </div>
                    )}
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      ${(pkg.price_dollars / pkg.credits).toFixed(2)} per credit
                    </div>
                  </div>

                  <button
                    onClick={() => handlePurchase(pkg.credits)}
                    disabled={purchasing === pkg.credits}
                    className={`w-full py-3 px-4 rounded-lg font-bold transition-all duration-300 ${
                      pkg.popular
                        ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg'
                        : darkMode
                        ? 'bg-gray-700 text-white hover:bg-gray-600'
                        : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                    } ${
                      purchasing === pkg.credits 
                        ? 'opacity-50 cursor-not-allowed' 
                        : 'hover:shadow-lg hover:-translate-y-1'
                    }`}
                  >
                    {purchasing === pkg.credits ? (
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent mr-2"></div>
                        Processing...
                      </div>
                    ) : (
                      'Purchase'
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-2xl mx-auto mt-16">
          <h2 className={`text-3xl font-bold text-center mb-8 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-6">
            <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
              <h3 className={`text-lg font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                How do credits work?
              </h3>
              <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Each video generation costs 1 credit. Credits never expire and can be used anytime.
              </p>
            </div>
            
            <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
              <h3 className={`text-lg font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                What payment methods do you accept?
              </h3>
              <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                We accept all major credit cards, debit cards, and various digital payment methods through Stripe.
              </p>
            </div>
            
            <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
              <h3 className={`text-lg font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Are there any refunds?
              </h3>
              <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Due to the computational costs of AI video generation, credits are non-refundable. However, please contact support if you encounter any issues.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
