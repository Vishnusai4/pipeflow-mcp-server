"use client";

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useToast } from '@/components/ui/use-toast';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

export default function ConnectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const appSlug = searchParams.get('app');

  useEffect(() => {
    const connectApp = async () => {
      if (!appSlug) {
        setError('No app specified');
        setStatus('error');
        setIsLoading(false);
        return;
      }

      try {
        setStatus('connecting');
        
        // Call the backend to get the OAuth URL
        const response = await fetch(`/api/connect_app`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ app_slug: appSlug })
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to connect to app');
        }

        const data = await response.json();
        
        // Redirect to the OAuth URL
        if (data.redirect_url) {
          window.location.href = data.redirect_url;
        } else {
          throw new Error('No redirect URL received from server');
        }
      } catch (err) {
        console.error('Connection error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Failed to connect to app');
        toast({
          title: 'Connection failed',
          description: 'Failed to initialize connection to the app',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    connectApp();
  }, [appSlug, toast]);

  const handleRetry = () => {
    setStatus('idle');
    setError(null);
    setIsLoading(true);
    // The useEffect will trigger again because of the state changes
  };

  if (status === 'connecting' || isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="text-lg font-medium">Connecting to {appSlug}...</p>
        <p className="text-muted-foreground">You will be redirected to complete the connection.</p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 max-w-md mx-auto text-center">
        <div className="rounded-full bg-red-100 p-4">
          <svg
            className="h-8 w-8 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold">Connection Failed</h1>
        <p className="text-muted-foreground">
          {error || 'An error occurred while connecting to the app.'}
        </p>
        <div className="flex gap-4 pt-4">
          <Button onClick={handleRetry}>Try Again</Button>
          <Button variant="outline" onClick={() => router.push('/dashboard')}>
            Go to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      <p className="text-lg font-medium">Preparing connection...</p>
    </div>
  );
}
