import React, { useState } from 'react';
import { normalizeAppSlug } from '@/utils/appUtils';

const ConnectButton = ({ appSlug, appName }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [connectLink, setConnectLink] = useState(null);

  const handleConnect = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/connect_app', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ app_slug: normalizeAppSlug(appSlug) })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to connect');
      }

      const data = await response.json();
      
      if (!data.connect_link) {
        throw new Error('No connection link received');
      }

      // Store the connect link in case popup is blocked
      setConnectLink(data.connect_link);
      
      // Open the OAuth URL in a new window
      const width = 600;
      const height = 700;
      const left = (window.screen.width - width) / 2;
      const top = (window.screen.height - height) / 2;
      
      const authWindow = window.open(
        data.connect_link,
        `oauth_${appSlug}`,
        `width=${width},height=${height},top=${top},left=${left},scrollbars=yes,resizable=yes`
      );

      if (!authWindow) {
        throw new Error('popup_blocked');
      }

      // Check if the window was closed
      const checkPopup = setInterval(() => {
        if (authWindow.closed) {
          clearInterval(checkPopup);
          // Refresh the page to show the new connection
          window.location.href = data.redirect_url || '/dashboard/apps';
        }
      }, 1000);

    } catch (error) {
      console.error('Error connecting app:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleConnect}
        disabled={isLoading}
        className={`px-4 py-2 rounded-md text-white font-medium ${
          isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Connecting...
          </>
        ) : (
          'Connect'
        )}
      </button>
      
      {error && (
        <div className="text-red-500 text-sm">
          {error === 'popup_blocked' ? (
            <>
              <p>Popup was blocked. Please allow popups for this site or click the link below:</p>
              <a 
                href={connectLink} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-500 underline"
              >
                Open {appName} Authentication
              </a>
            </>
          ) : (
            <p>{error}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ConnectButton;
