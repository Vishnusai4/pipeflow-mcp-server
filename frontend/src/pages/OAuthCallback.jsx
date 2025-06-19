import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

function OAuthCallback() {
  const location = useLocation();

  useEffect(() => {
    // Check for error in URL
    const params = new URLSearchParams(location.search);
    const error = params.get('error');
    
    if (error) {
      const errorDescription = params.get('error_description');
      window.opener?.postMessage({
        type: 'oauth_error',
        error,
        error_description: errorDescription
      }, window.location.origin);
    } else {
      // Success - notify the opener
      window.opener?.postMessage({
        type: 'oauth_complete',
        success: true
      }, window.location.origin);
    }
    
    // Close the window
    window.close();
  }, [location]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center p-6 max-w-sm mx-auto">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold mb-2">Completing Connection</h2>
        <p className="text-gray-600">Please wait while we connect your account...</p>
      </div>
    </div>
  );
}

export default OAuthCallback;
