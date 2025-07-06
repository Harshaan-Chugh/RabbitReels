"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useAuth } from './AuthContext';

interface UserVideo {
  id: string;
  job_id: string;
  title: string;
  character_theme: string;
  prompt: string;
  status: 'queued' | 'rendering' | 'done' | 'error';
  download_url?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

interface VideoHistoryContextType {
  videos: UserVideo[];
  loading: boolean;
  error: string | null;
  fetchVideos: () => Promise<void>;
  refreshVideos: () => Promise<void>;
}

const VideoHistoryContext = createContext<VideoHistoryContextType | undefined>(undefined);

export function VideoHistoryProvider({ children }: { children: ReactNode }) {
  const [videos, setVideos] = useState<UserVideo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, authenticatedFetch } = useAuth();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost';

  const fetchVideos = useCallback(async () => {
    if (!isAuthenticated) {
      setVideos([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('Fetching user videos...');
      const response = await authenticatedFetch(`${API_BASE_URL}/user/videos`);
      
      if (response.ok) {
        const data = await response.json();
        setVideos(data.videos || []);
        console.log('Successfully fetched user videos:', data.videos?.length || 0);
      } else {
        const errorText = await response.text();
        console.error('Failed to fetch user videos:', response.status, errorText);
        setError('Failed to fetch video history');
      }
    } catch (err) {
      console.error('Error fetching user videos:', err);
      setError('Failed to fetch video history');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, authenticatedFetch, API_BASE_URL]);

  const refreshVideos = useCallback(async () => {
    await fetchVideos();
  }, [fetchVideos]);

  // Fetch videos when user logs in
  useEffect(() => {
    if (isAuthenticated) {
      fetchVideos();
    } else {
      setVideos([]);
      setError(null);
    }
  }, [isAuthenticated, fetchVideos]);

  const value: VideoHistoryContextType = {
    videos,
    loading,
    error,
    fetchVideos,
    refreshVideos,
  };

  return (
    <VideoHistoryContext.Provider value={value}>
      {children}
    </VideoHistoryContext.Provider>
  );
}

export function useVideoHistory() {
  const context = useContext(VideoHistoryContext);
  if (context === undefined) {
    throw new Error('useVideoHistory must be used within a VideoHistoryProvider');
  }
  return context;
} 