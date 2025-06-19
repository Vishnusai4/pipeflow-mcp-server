'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAppAuth } from '@/hooks/useAppAuth';
import { Spinner } from '@/components/ui/spinner';

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { handleOAuthCallback } = useAppAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');

    const processCallback = async () => {
      if (errorParam) {
        setError(errorParam);
        return;
      }

      if (!code || !state) {
        setError('Missing required parameters');
        return;
      }

      try {
        const result = await handleOAuthCallback(code, state);
        
        // Close the popup if this is in a popup
        if (window.opener) {
          window.opener.postMessage(
            { type: 'OAUTH_COMPLETE', success: true, appSlug: result.app_slug },
            window.location.origin
          );
          window.close();
        } else {
          // If not in a popup, redirect to dashboard
          router.push('/dashboard');
        }
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('Failed to complete authentication');
        
        if (window.opener) {
          window.opener.postMessage(
            { type: 'OAUTH_COMPLETE', success: false, error: 'Authentication failed' },
            window.location.origin
          );
        }
      }
    };

    processCallback();
  }, [searchParams, handleOAuthCallback, router]);

  // Listen for messages from popup (in case this is the parent window)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data?.type === 'OAUTH_COMPLETE') {
        if (event.data.success) {
          router.push('/dashboard');
        } else {
          setError(event.data.error || 'Authentication failed');
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [router]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg max-w-md w-full text-center">
          <h2 className="text-xl font-bold mb-2">Authentication Error</h2>
          <p className="mb-4">{error}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div className="text-center">
        <Spinner className="w-12 h-12 mx-auto mb-4" />
        <h1 className="text-2xl font-bold mb-2">Completing Authentication</h1>
        <p className="text-gray-600">Please wait while we connect your account...</p>
      </div>
    </div>
  );
}
