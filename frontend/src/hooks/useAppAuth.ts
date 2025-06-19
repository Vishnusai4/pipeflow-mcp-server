import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/app/api-client';
import { toast } from 'react-hot-toast';

export function useAppAuth() {
  const queryClient = useQueryClient();
  const [isConnecting, setIsConnecting] = useState<Record<string, boolean>>({});

  // Get user's app connections
  const { data: connections = [], isLoading, error } = useQuery({
    queryKey: ['appConnections'],
    queryFn: () => apiClient.getUserConnections(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation for disconnecting an app
  const disconnectAppMutation = useMutation({
    mutationFn: (appSlug: string) => apiClient.disconnectAppAuth(appSlug),
    onSuccess: (_, appSlug) => {
      toast.success(`Successfully disconnected from ${appSlug}`);
      queryClient.invalidateQueries({ queryKey: ['appConnections'] });
    },
    onError: (error: any, appSlug) => {
      console.error('Failed to disconnect app:', error);
      toast.error(`Failed to disconnect from ${appSlug}`);
    },
  });

  // Function to initiate app connection
  const connectApp = async (appSlug: string, scopes: string[] = ["basic"]) => {
    try {
      console.log(`Initiating connection to ${appSlug}...`);
      setIsConnecting(prev => ({ ...prev, [appSlug]: true }));
      
      // Get the sign-in link from the server
      console.log('Requesting sign-in link from server...');
      const { url } = await apiClient.getSignInLink(appSlug, scopes);
      console.log('Received sign-in URL:', url);
      
      if (!url) {
        throw new Error('No URL returned from server');
      }
      
      // Open the OAuth flow in a popup or redirect
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      
      console.log('Opening OAuth popup...');
      const popup = window.open(
        url,
        'oauth',
        `width=${width},height=${height},left=${left},top=${top},popup=1`
      );
      
      if (!popup) {
        throw new Error('Popup was blocked. Please allow popups for this site.');
      }
      
    } catch (error) {
      console.error('Error in connectApp:', error);
      toast.error(`Failed to start authentication: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsConnecting(prev => ({ ...prev, [appSlug]: false }));
    }
  };

  // Function to handle OAuth callback (call this in your OAuth callback page)
  const handleOAuthCallback = async (code: string, state: string) => {
    try {
      const result = await apiClient.handleOAuthCallback(code, state);
      toast.success(`Successfully connected to ${result.app_slug}`);
      queryClient.invalidateQueries({ queryKey: ['appConnections'] });
      return result;
    } catch (error) {
      console.error('OAuth callback error:', error);
      toast.error('Failed to complete OAuth flow');
      throw error;
    }
  };

  // Function to disconnect an app
  const disconnectApp = async (appSlug: string) => {
    try {
      await disconnectAppMutation.mutateAsync(appSlug);
      // Success toast is handled in the mutation's onSuccess callback
    } catch (error) {
      console.error('Error disconnecting app:', error);
      // Error toast is handled in the mutation's onError callback
      throw error; // Re-throw to allow components to handle the error if needed
    }
  };

  // Check if an app is connected
  const isAppConnected = (appSlug: string) => {
    return connections.some(conn => 
      conn.app_slug === appSlug && conn.status === 'connected'
    );
  };

  // Get connection status for an app
  const getAppConnection = (appSlug: string) => {
    return connections.find(conn => conn.app_slug === appSlug);
  };

  return {
    connections,
    isLoading,
    error,
    connectApp,
    disconnectApp,
    isConnecting: (appSlug: string) => isConnecting[appSlug] || false,
    isAppConnected,
    getAppConnection,
    handleOAuthCallback,
  };
}

export default useAppAuth;
