import { useState, useEffect } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppAuth } from '@/hooks/useAppAuth';

interface AppCardProps {
  app: {
    app_slug: string;
    name: string;
    logo_url?: string;
    description?: string;
    app_category?: string[];
  };
  onConnect?: (appSlug: string) => void;
  onDisconnect?: (appSlug: string) => void;
  className?: string;
}

export function AppCard({ app, className = '' }: AppCardProps) {
  const { 
    isAppConnected, 
    isConnecting, 
    connectApp, 
    disconnectApp,
    getAppConnection 
  } = useAppAuth();
  
  const [isMounted, setIsMounted] = useState(false);
  const connection = getAppConnection(app.app_slug);
  const isConnected = isAppConnected(app.app_slug);
  const isLoading = isConnecting(app.app_slug);

  // Handle popup completion
  useEffect(() => {
    setIsMounted(true);
    
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data?.type === 'OAUTH_COMPLETE') {
        if (event.data.success) {
          // Connection successful
          console.log(`Successfully connected to ${app.app_slug}`);
        } else {
          console.error('Connection failed:', event.data.error);
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [app.app_slug]);

  const handleConnect = async () => {
    try {
      await connectApp(app.app_slug, ['basic']); // Default scopes
    } catch (error) {
      console.error('Error connecting app:', error);
    }
  };

  const handleDisconnect = async () => {
    if (window.confirm(`Are you sure you want to disconnect from ${app.name}?`)) {
      try {
        await disconnectApp(app.app_slug);
      } catch (error) {
        console.error('Error disconnecting app:', error);
      }
    }
  };

  // Don't render on server to avoid hydration mismatch
  if (!isMounted) return null;

  return (
    <div className={`border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow ${className}`}>
      <div className="p-4">
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            {app.logo_url ? (
              <div className="w-12 h-12 relative rounded-md overflow-hidden">
                <Image
                  src={app.logo_url}
                  alt={`${app.name} logo`}
                  width={48}
                  height={48}
                  className="object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.onerror = null;
                    target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(app.name)}&background=random`;
                  }}
                />
              </div>
            ) : (
              <div className="w-12 h-12 rounded-md bg-gray-100 flex items-center justify-center text-gray-500 font-medium">
                {app.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-900 truncate">{app.name}</h3>
              {isConnected && (
                <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
                  Connected
                </Badge>
              )}
            </div>
            
            {app.description && (
              <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                {app.description}
              </p>
            )}
            
            <div className="mt-2 flex flex-wrap gap-1">
              {app.app_category?.map((category) => (
                <Badge key={category} variant="secondary">
                  {category}
                </Badge>
              ))}
            </div>
            
            <div className="mt-4">
              {isConnected ? (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleDisconnect}
                  disabled={isLoading}
                >
                  {isLoading ? 'Disconnecting...' : 'Disconnect'}
                </Button>
              ) : (
                <Button 
                  size="sm" 
                  onClick={handleConnect}
                  disabled={isLoading}
                >
                  {isLoading ? 'Connecting...' : 'Connect'}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
