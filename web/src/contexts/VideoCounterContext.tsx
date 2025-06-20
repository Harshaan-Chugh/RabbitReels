"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface VideoCounterContextType {
  videoCount: number;
  incrementVideoCount: () => void;
}

const VideoCounterContext = createContext<VideoCounterContextType | undefined>(undefined);

export function VideoCounterProvider({ children }: { children: ReactNode }) {
  const [videoCount, setVideoCount] = useState(0);
  // Load video count from localStorage on mount
  useEffect(() => {
    // For testing purposes, start with 0. Remove this line later if you want persistence
    localStorage.removeItem('videoCount');
    setVideoCount(0);
    
    // Uncomment these lines to restore localStorage functionality:
    // const savedCount = localStorage.getItem('videoCount');
    // if (savedCount) {
    //   setVideoCount(parseInt(savedCount, 10));
    // } else {
    //   setVideoCount(0);
    // }
  }, []);

  // Save video count to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('videoCount', videoCount.toString());
  }, [videoCount]);

  const incrementVideoCount = () => {
    setVideoCount(prev => prev + 1);
  };

  return (
    <VideoCounterContext.Provider value={{ videoCount, incrementVideoCount }}>
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
