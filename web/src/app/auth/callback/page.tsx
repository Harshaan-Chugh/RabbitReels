"use client";

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      console.log('OAuth callback received token, storing and redirecting to home...');
      
      // Store the token
      localStorage.setItem('jwt_token', token);
      
      // Redirect to home page (not generator)
      // The AuthProvider will automatically detect the token and update the user state
      router.push('/');
    } else {
      console.error('No token found in OAuth callback');
      // No token found, redirect to home with error
      router.push('/?error=auth_failed');
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Completing sign in...
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Please wait while we complete your authentication.
        </p>
      </div>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={null}>
      <AuthCallbackContent />
    </Suspense>
  );
}
