"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { loadStripe, Stripe } from '@stripe/stripe-js';

interface CreditPackage {
  credits: number;
  price_cents: number;
  price_dollars: number;
  savings_percent: number;
  popular: boolean;
}

interface BillingContextType {
  credits: number;
  loading: boolean;
  creditPackages: CreditPackage[];
  purchaseCredits: (credits: number) => Promise<void>;
  refreshBalance: () => Promise<void>;
  stripe: Stripe | null;
}

const BillingContext = createContext<BillingContextType | undefined>(undefined);

let stripePromise: Promise<Stripe | null> | null = null;

const getStripe = () => {
  if (!stripePromise) {
    const publishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
    if (!publishableKey) {
      console.error('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set');
      return null;
    }
    stripePromise = loadStripe(publishableKey);
  }
  return stripePromise;
};

export function BillingProvider({ children }: { children: ReactNode }) {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(true);
  const [creditPackages, setCreditPackages] = useState<CreditPackage[]>([]);
  const [stripe, setStripe] = useState<Stripe | null>(null);
  
  const { authenticatedFetch, isAuthenticated } = useAuth();
  const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost';
  const API_BASE_URL = RAW_BASE.endsWith('/api') ? RAW_BASE : `${RAW_BASE}/api`;

  useEffect(() => {
    const initStripe = async () => {
      const stripeInstance = await getStripe();
      setStripe(stripeInstance);
    };
    initStripe();
  }, []);

  useEffect(() => {
    const loadCreditPackages = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/billing/prices`);
        if (response.ok) {
          const data = await response.json();
          setCreditPackages(data.packages || []);
        }
      } catch (error) {
        console.error('Error loading credit packages:', error);
      }
    };
    
    loadCreditPackages();
  }, [API_BASE_URL]);

  const refreshBalance = useCallback(async () => {
    console.log('refreshBalance called - isAuthenticated:', isAuthenticated);
    if (!isAuthenticated) {
      console.log('User not authenticated, skipping balance fetch');
      return;
    }
    
    try {
      setLoading(true);
      console.log('Fetching balance from:', `${API_BASE_URL}/billing/balance`);
      const response = await authenticatedFetch(`${API_BASE_URL}/billing/balance`);
      
      console.log('Balance response status:', response.status);
      if (response.ok) {
        const data = await response.json();
        console.log('Balance data received:', data);
        setCredits(data.credits || 0);
      } else {
        console.error('Failed to fetch credit balance, status:', response.status);
        const errorText = await response.text();
        console.error('Error response:', errorText);
      }
    } catch (error) {
      console.error('Error fetching credit balance:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, authenticatedFetch, API_BASE_URL]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshBalance();
    } else {
      setCredits(0);
      setLoading(false);
    }
  }, [isAuthenticated, refreshBalance]);

  const purchaseCredits = async (credits: number) => {
    if (!isAuthenticated || !stripe) {
      throw new Error('Authentication or Stripe not available');
    }

    try {
      const response = await authenticatedFetch(`${API_BASE_URL}/billing/checkout-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ credits }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create checkout session');
      }

      const { url } = await response.json();
      
      window.location.href = url;
    } catch (error) {
      console.error('Error purchasing credits:', error);
      throw error;
    }
  };

  const value: BillingContextType = {
    credits,
    loading,
    creditPackages,
    purchaseCredits,
    refreshBalance,
    stripe,
  };

  return (
    <BillingContext.Provider value={value}>
      {children}
    </BillingContext.Provider>
  );
}

export function useBilling() {
  const context = useContext(BillingContext);
  if (context === undefined) {
    throw new Error('useBilling must be used within a BillingProvider');
  }
  return context;
}
