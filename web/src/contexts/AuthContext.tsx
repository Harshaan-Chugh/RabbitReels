"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

interface User {
  sub: string;
  email: string;
  name: string;
  picture?: string;
  iat: number;
  exp: number;
  jti: string;
}

interface UserProfile {
  sub: string;
  email: string;
  name: string;
  picture?: string;
  created_at: number;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  loading: boolean;
  authenticatedFetch: (url: string, options?: RequestInit) => Promise<Response>;
  emailLogin: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  validateToken: (token: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost';

  const fetchProfile = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data.profile);
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  }, [API_BASE_URL]);

  const validateToken = useCallback(async (token: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        
        // Also fetch the full profile
        await fetchProfile(token);
      } else {
        // Token is invalid, remove it
        localStorage.removeItem('jwt_token');
        setUser(null);
        setProfile(null);
      }
    } catch (error) {
      console.error('Error validating token:', error);
      localStorage.removeItem('jwt_token');
      setUser(null);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [API_BASE_URL, fetchProfile]);

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      validateToken(token);
    } else {
      setLoading(false);
    }
  }, [validateToken]);
  // Listen for storage changes (when token is set from another tab/window)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'jwt_token') {
        if (e.newValue) {
          validateToken(e.newValue);
        } else {
          // Token was removed
          setUser(null);
          setProfile(null);
          setLoading(false);
        }
      }
    };

    const handleAuthRefresh = () => {
      const token = localStorage.getItem('jwt_token');
      if (token) {
        validateToken(token);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth-refresh', handleAuthRefresh);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);      window.removeEventListener('auth-refresh', handleAuthRefresh);
    };
  }, [validateToken]);
  const login = useCallback(() => {
    // Redirect to the OAuth login endpoint
    window.location.href = `${API_BASE_URL}/api/auth/login`;
  }, [API_BASE_URL]);

  const emailLogin = useCallback(async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token;
        
        // Store the token
        localStorage.setItem('jwt_token', token);
        
        // Validate the token and set user state
        await validateToken(token);
        
        return { success: true };
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
        return { success: false, error: Array.isArray(errorData.detail) ? errorData.detail[0].msg : errorData.detail || 'Login failed' };
      }
    } catch (error) {
      console.error('Email login error:', error);
      return { success: false, error: 'Network error. Please try again.' };
    }
  }, [API_BASE_URL, validateToken]);

  const logout = useCallback(() => {
    localStorage.removeItem('jwt_token');
    setUser(null);
    setProfile(null);
  }, []);
  const authenticatedFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    const token = localStorage.getItem('jwt_token');
    console.log('authenticatedFetch called for:', url);
    console.log('Token exists:', !!token);
    if (!token) {
      console.error('No authentication token found');
      throw new Error('No authentication token found');
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    };

    console.log('Making authenticated request to:', url);
    return fetch(url, {
      ...options,
      headers,
    });
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      profile,
      isAuthenticated: !!user,
      login,
      logout,
      loading,
      authenticatedFetch,
      emailLogin,
      validateToken
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
