"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

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
  emailRegister: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      validateToken(token);
    } else {
      setLoading(false);
    }
  }, []);  const validateToken = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        
        // Also fetch the full profile
        fetchProfile(token);
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
  };

  const fetchProfile = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
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
  };
  const login = () => {
    // Redirect to the OAuth login endpoint
    window.location.href = `${API_BASE_URL}/auth/login`;
  };  const emailLogin = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
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
  };  const emailRegister = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name }),
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
        const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
        return { success: false, error: Array.isArray(errorData.detail) ? errorData.detail[0].msg : errorData.detail || 'Registration failed' };
      }
    } catch (error) {
      console.error('Email registration error:', error);
      return { success: false, error: 'Network error. Please try again.' };
    }
  };
  const logout = () => {
    localStorage.removeItem('jwt_token');
    setUser(null);
    setProfile(null);
  };

  const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      throw new Error('No authentication token found');
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    };

    return fetch(url, {
      ...options,
      headers,
    });
  };  return (
    <AuthContext.Provider value={{
      user,
      profile,
      isAuthenticated: !!user,
      login,
      logout,
      loading,
      authenticatedFetch,
      emailLogin,
      emailRegister
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
