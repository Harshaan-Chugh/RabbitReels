"use client";

import { useState, useEffect, useRef } from 'react';

interface AnimatedCounterProps {
  target: number;
  duration?: number;
  className?: string;
}

export default function AnimatedCounter({ 
  target, 
  duration = 2500, 
  className = ""
}: AnimatedCounterProps) {
  const [current, setCurrent] = useState(0);
  const [fontSize, setFontSize] = useState('2.25rem'); // text-4xl equivalent
  const [isAnimating, setIsAnimating] = useState(false);
  const animationRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    // Cancel any existing animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    if (target <= 0) {
      setCurrent(0);
      setFontSize('1.25rem'); // text-xl equivalent
      return;
    }
    
    // Reset to large size and start counting
    setFontSize('2.25rem'); // text-4xl equivalent
    setIsAnimating(true);
    setCurrent(0); // Always start from 0
    
    const startTime = Date.now();
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Smooth easing function
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const newValue = Math.floor(target * easeOutQuart);
      
      setCurrent(newValue);
      
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setCurrent(target);
        setIsAnimating(false);
        
        // After counting completes, wait then shrink
        setTimeout(() => {
          setFontSize('1.25rem'); // text-xl equivalent
        }, 500);
      }
    };
    
    animationRef.current = requestAnimationFrame(animate);

    // Cleanup function
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [target, duration]);

  return (
    <span 
      className={`
        ${className}
        font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent
        ${isAnimating ? 'animate-pulse' : ''}
        inline-block
      `}
      style={{
        fontSize: fontSize,
        transition: 'font-size 0.7s ease-in-out',
        fontVariantNumeric: 'tabular-nums',
        minWidth: '3ch'
      }}
    >
      {current.toLocaleString()}
    </span>
  );
}