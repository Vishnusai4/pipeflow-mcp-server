'use client';

import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { apiClient, type App } from '@/app/api-client';
import { useAppAuth } from '@/hooks/useAppAuth';

// Extend the App type to include is_connected
interface ConnectedApp extends Omit<App, 'is_connected'> {
  is_connected: boolean;
}

// Define the backend response type for the /apps endpoint
type BackendAppsResponse = Array<{
  app_slug: string;
  name: string;
  logo_url: string;
  app_category: string[];
  description: string;
}>;

// Define session type
type Session = {
  id: string;
  app_slug: string;
  created_at: string;
  expires_at: string;
};

type Category = {
  name: string;
  apps: ConnectedApp[];
};

export default function AppsPage() {
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = React.useState<string | null>(null);
  const { disconnectApp } = useAppAuth();

  const { 
    data: appsResponse, 
    isLoading: isLoadingApps, 
    error: appsError 
  } = useQuery<BackendAppsResponse>({
    queryKey: ['apps'],
    queryFn: async (): Promise<BackendAppsResponse> => {
      try {
        const response = await apiClient.getApps();
        // The backend returns the array of apps directly
        return Array.isArray(response) ? response : [];
      } catch (error) {
        console.error('Error fetching apps:', error);
        return [];
      }
    },
    retry: 2,
    refetchOnWindowFocus: false
  });

  const { 
    data: sessionsResponse, 
    isLoading: isLoadingSessions, 
    error: sessionsError 
  } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => apiClient.getUserSessions(),
  });
  
  // Ensure sessions is always an array
  const sessionsData = Array.isArray(sessionsResponse) ? sessionsResponse : [];

  const handleConnect = async (appSlug: string) => {
    if (isProcessing) return;
    
    try {
      setIsProcessing(appSlug);
      const { redirect_url } = await apiClient.connectApp(appSlug);
      
      // Invalidate queries to refresh the app list
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['apps'] }),
        queryClient.invalidateQueries({ queryKey: ['sessions'] }),
      ]);
      
      // Show success message
      toast.success('App connected successfully');
      
      // Redirect if needed
      if (redirect_url && redirect_url !== window.location.pathname) {
        window.location.href = redirect_url;
      }
    } catch (error: any) {
      if (error.message === 'popup_blocked') {
        toast.error('Popup was blocked. Please allow popups for this site.');
      } else {
        console.error('Connection error:', error);
        toast.error(error.response?.data?.detail || 'Failed to connect app');
      }
    } finally {
      setIsProcessing(null);
    }
  };

  const handleDisconnect = async (appSlug: string) => {
    if (isProcessing) return;
    
    try {
      setIsProcessing(appSlug);
      await disconnectApp(appSlug);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['apps'] }),
        queryClient.invalidateQueries({ queryKey: ['sessions'] }),
      ]);
    } catch (error) {
      console.error('Disconnection error:', error);
    } finally {
      setIsProcessing(null);
    }
  };

  // Show loading state
  if (isLoadingApps || isLoadingSessions) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Show error state
  if (appsError || sessionsError) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 text-lg font-medium mb-2">
          Failed to load apps. Please try again.
        </div>
        <div className="mt-2 text-sm text-red-700">
          <p>{
            appsError instanceof Error 
              ? appsError.message 
              : sessionsError instanceof Error 
                ? sessionsError.message 
                : 'An unknown error occurred'
          }</p>
        </div>
        <div className="mt-4">
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['apps'] });
              queryClient.invalidateQueries({ queryKey: ['sessions'] });
            }}
            className="rounded-md bg-red-50 px-2 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

    // Transform the backend response into the frontend App[] format with connection status
  const apps = React.useMemo<ConnectedApp[]>(() => {
    if (!appsResponse || !Array.isArray(appsResponse)) return [];
    
    const sessionData = Array.isArray(sessionsData) ? sessionsData : [];
    const connectedAppSlugs = new Set(sessionData.map((session: Session) => session.app_slug));
    
    try {
      return appsResponse.map(app => ({
        ...app,
        // Ensure app_category is always an array and has at least one category
        app_category: Array.isArray(app.app_category) && app.app_category.length > 0 
          ? app.app_category 
          : ['Other'],
        is_connected: connectedAppSlugs.has(app.app_slug)
      }));
    } catch (error) {
      console.error('Error processing apps:', error);
      return [];
    }
  }, [appsResponse, sessionsData]);

  // Group apps by category and sort them
  const categories = React.useMemo<Category[]>(() => {
    const categoriesMap = new Map<string, ConnectedApp[]>();
    
    // First pass: collect all unique categories
    const allCategories = new Set<string>();
    apps.forEach((app: ConnectedApp) => {
      if (app.app_category?.length) {
        app.app_category.forEach(cat => allCategories.add(cat));
      } else {
        allCategories.add('Other');
      }
    });
    
    // Initialize all categories with empty arrays
    Array.from(allCategories).sort().forEach(cat => {
      categoriesMap.set(cat, []);
    });
    
    // Second pass: assign apps to their categories
    apps.forEach((app: ConnectedApp) => {
      const appCategories = app.app_category?.length ? app.app_category : ['Other'];
      
      // Add app to each of its categories
      appCategories.forEach(category => {
        if (!categoriesMap.has(category)) {
          categoriesMap.set(category, []);
        }
        categoriesMap.get(category)?.push(app);
      });
    });

    // Convert to array and sort categories alphabetically
    return Array.from(categoriesMap.entries())
      .map(([name, categoryApps]) => ({
        name,
        // Remove duplicates and sort apps by name within each category
        apps: Array.from(new Map(categoryApps.map(app => [app.app_slug, app])).values())
          .sort((a, b) => a.name.localeCompare(b.name))
      }))
      .sort((a, b) => a.name.localeCompare(b.name)); // Sort categories alphabetically
  }, [apps]);

  const renderAppCard = (app: ConnectedApp) => (
    <div
      key={app.app_slug}
      className="bg-white overflow-hidden shadow rounded-lg divide-y divide-gray-200 flex flex-col"
    >
      <div className="px-4 py-5 sm:p-6 flex-1">
        <div className="flex items-start">
          <div className="flex-shrink-0 bg-white rounded-md p-1 mr-4 border border-gray-200">
            <img 
              src={app.logo_url} 
              alt={`${app.name} logo`} 
              className="h-12 w-12 object-contain"
              onError={(e) => {
                // Fallback to first letter of app name if logo fails to load
                const fallback = document.createElement('div');
                fallback.className = 'h-12 w-12 rounded-md bg-gray-100 flex items-center justify-center';
                fallback.innerHTML = `<span class="text-sm font-medium text-gray-500">${app.name.charAt(0)}</span>`;
                e.currentTarget.parentNode?.replaceChild(fallback, e.currentTarget);
              }}
            />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-medium text-gray-900">
              {app.name}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {app.description}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {app.app_category?.map((cat) => (
                <span 
                  key={`${app.app_slug}-${cat}`}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="px-4 py-4 sm:px-6">
        {app.is_connected ? (
          <button
            onClick={() => handleDisconnect(app.app_slug)}
            disabled={isProcessing === app.app_slug}
            className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing === app.app_slug ? 'Disconnecting...' : 'Disconnect'}
          </button>
        ) : (
          <button
            onClick={() => handleConnect(app.app_slug)}
            disabled={isProcessing === app.app_slug}
            className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing === app.app_slug ? 'Connecting...' : 'Connect'}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Available Apps</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connect to your favorite apps to get started.
        </p>
      </div>

      <div className="space-y-12">
        {categories.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                vectorEffect="non-scaling-stroke"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No apps found</h3>
            <p className="mt-1 text-sm text-gray-500">
              There are no apps available to connect at the moment.
            </p>
          </div>
        ) : (
          categories.map((category) => (
            <div key={category.name} className="space-y-4">
              <h2 className="text-lg font-medium text-gray-900">{category.name}</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {category.apps.map((app) => renderAppCard(app))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
