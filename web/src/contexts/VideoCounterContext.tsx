"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface VideoCounterContextType {
  videoCount: number;
  refreshVideoCount: () => void;
}

const VideoCounterContext = createContext<VideoCounterContextType | undefined>(undefined);

export function VideoCounterProvider({ children }: { children: ReactNode }) {
  const [videoCount, setVideoCount] = useState(0);
  
  // Load video count from API on mount
  useEffect(() => {
    const fetchVideoCount = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/video-count`);
        if (response.ok) {
          const data = await response.json();
          setVideoCount(data.count);
        }
      } catch (error) {
        console.error('Failed to fetch video count:', error);
        // Fallback to localStorage if API is not available
        const savedCount = localStorage.getItem('videoCount');
        if (savedCount) {
          setVideoCount(parseInt(savedCount, 10));
        }
      }
    };
    
    fetchVideoCount();
  }, []);

  // Save to localStorage as backup
  useEffect(() => {
    localStorage.setItem('videoCount', videoCount.toString());
  }, [videoCount]);

  const refreshVideoCount = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/video-count`);
      if (response.ok) {
        const data = await response.json();
        setVideoCount(data.count);
      }
    } catch (error) {
      console.error('Failed to refresh video count:', error);
      // Keep current count if refresh fails
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
