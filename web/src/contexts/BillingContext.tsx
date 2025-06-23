"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
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
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

  // Initialize Stripe
  useEffect(() => {
    const initStripe = async () => {
      const stripeInstance = await getStripe();
      setStripe(stripeInstance);
    };
    initStripe();
  }, []);

  // Load credit packages on mount
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

  // Load user's credit balance when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      refreshBalance();
    } else {
      setCredits(0);
      setLoading(false);
    }
  }, [isAuthenticated]);

  const refreshBalance = async () => {
    if (!isAuthenticated) return;
    
    try {
      setLoading(true);
      const response = await authenticatedFetch(`${API_BASE_URL}/billing/balance`);
      
      if (response.ok) {
        const data = await response.json();
        setCredits(data.credits || 0);
      } else {
        console.error('Failed to fetch credit balance');
      }
    } catch (error) {
      console.error('Error fetching credit balance:', error);
    } finally {
      setLoading(false);
    }
  };

  const purchaseCredits = async (credits: number) => {
    if (!isAuthenticated || !stripe) {
      throw new Error('Authentication or Stripe not available');
    }

    try {
      // Create checkout session
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
      
      // Redirect to Stripe Checkout
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
