"use client";

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { validateToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
      console.log('OAuth callback received token, storing and validating...');
        // Store the token
      localStorage.setItem('jwt_token', token);
      
      // Trigger a custom event to refresh auth state
      window.dispatchEvent(new Event('auth-refresh'));
      
      // Immediately validate the token to update AuthContext state
      if (validateToken) {
        validateToken(token).then(() => {
          console.log('Token validated, redirecting to home...');
          // Use router push instead of window.location for better UX
          router.push('/');
        }).catch((error) => {
          console.error('Token validation failed:', error);
          router.push('/?error=auth_failed');
        });
      } else {
        // Fallback
        router.push('/');
      }
    } else {
      console.error('No token found in OAuth callback');
      router.push('/?error=auth_failed');
    }
  }, [searchParams, router, validateToken]);

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
