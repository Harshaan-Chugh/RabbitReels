"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface VideoCounterContextType {
  videoCount: number;
  refreshVideoCount: () => void;
}

const VideoCounterContext = createContext<VideoCounterContextType | undefined>(undefined);

export function VideoCounterProvider({ children }: { children: ReactNode }) {
  const [videoCount, setVideoCount] = useState(0);
  
  useEffect(() => {
    const fetchVideoCount = async () => {
      try {
        const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://rabbitreels.us';
        const API_BASE_URL = RAW_BASE.endsWith('/api') ? RAW_BASE : `${RAW_BASE}/api`;
        const response = await fetch(`${API_BASE_URL}/video-count`);
        if (response.ok) {
          const data = await response.json();
          setVideoCount(data.count);
        }
      } catch (error) {
        console.error('Failed to fetch video count:', error);
        const savedCount = localStorage.getItem('videoCount');
        if (savedCount) {
          setVideoCount(parseInt(savedCount, 10));
        }
      }
    };
    
    fetchVideoCount();
  }, []);

  useEffect(() => {
    localStorage.setItem('videoCount', videoCount.toString());
  }, [videoCount]);

  const refreshVideoCount = async () => {
    try {
      const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://rabbitreels.us';
      const API_BASE_URL = RAW_BASE.endsWith('/api') ? RAW_BASE : `${RAW_BASE}/api`;
      const response = await fetch(`${API_BASE_URL}/video-count`);
      if (response.ok) {
        const data = await response.json();
        setVideoCount(data.count);
      }
    } catch (error) {
      console.error('Failed to refresh video count:', error);
    }
  };

  return (
    <VideoCounterContext.Provider value={{ videoCount, refreshVideoCount }}>
      {children}
    </VideoCounterContext.Provider>
  );
}

export function useVideoCounter() {
  const context = useContext(VideoCounterContext);
  if (context === undefined) {
    throw new Error('useVideoCounter must be used within a VideoCounterProvider');
  }
  return context;
}
