'use client';

import { useAuthStore } from '@/stores/auth-store';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api-client';
import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { 
  FiActivity, 
  FiClock, 
  FiPlus, 
  FiServer, 
  FiAlertCircle,
  FiZap,
  FiCheck,
  FiLink,
  FiX
} from 'react-icons/fi';
import Link from 'next/link';

// Define activity types
type ActivityType = 'connected' | 'disconnected' | 'error' | 'info';

interface ActivityItem {
  id: string;
  type: ActivityType;
  app: string;
  timestamp: string;
  message: string;
}

import { App } from '../api-client';

// Define the app type for the frontend
interface DashboardApp {
  app_slug: string;
  name: string;
  logo_url: string;
  app_category: string[];
  description: string;
  is_connected: boolean;
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: string;
    type: 'up' | 'down' | 'neutral';
  };
}

function StatCard({ title, value, icon, trend }: StatCardProps) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0 bg-indigo-500 rounded-md p-3">
            {icon}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {value}
                </div>
                {trend && (
                  <div
                    className={`ml-2 flex items-baseline text-sm font-semibold ${
                      trend.type === 'up'
                        ? 'text-green-600'
                        : trend.type === 'down'
                        ? 'text-red-600'
                        : 'text-gray-500'
                    }`}
                  >
                    {trend.value}
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

// ActivityItem type is already defined above

function ActivityFeedItem({ item }: { item: ActivityItem }) {
  const getIcon = () => {
    switch (item.type) {
      case 'connected':
        return (
          <div className="bg-green-100 p-2 rounded-full">
            <FiZap className="h-4 w-4 text-green-600" />
          </div>
        );
      case 'disconnected':
        return (
          <div className="bg-red-100 p-2 rounded-full">
            <FiZap className="h-4 w-4 text-red-600" />
          </div>
        );
      case 'error':
        return (
          <div className="bg-yellow-100 p-2 rounded-full">
            <FiActivity className="h-4 w-4 text-yellow-600" />
          </div>
        );
      default:
        return (
          <div className="bg-blue-100 p-2 rounded-full">
            <FiServer className="h-4 w-4 text-blue-600" />
          </div>
        );
    }
  };

  return (
    <div className="relative pb-8">
      <span
        className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
        aria-hidden="true"
      />
      <div className="relative flex space-x-3">
        <div>{getIcon()}</div>
        <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
          <div>
            <p className="text-sm text-gray-500">
              {item.message}{' '}
              <span className="font-medium text-gray-900">{item.app}</span>
            </p>
          </div>
          <div className="text-right text-sm whitespace-nowrap text-gray-500">
            <time dateTime={item.timestamp}>
              {new Date(item.timestamp).toLocaleTimeString()}
            </time>
          </div>
        </div>
      </div>
    </div>
  );
}

// Mock data for the dashboard
const mockActivity: ActivityItem[] = [
  {
    id: '1',
    type: 'connected',
    app: 'Slack',
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    message: 'Connected to',
  },
  {
    id: '2',
    type: 'disconnected',
    app: 'GitHub',
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    message: 'Disconnected from',
  },
  {
    id: '3',
    type: 'error',
    app: 'Slack',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    message: 'Error syncing data from',
  },
  {
    id: '4',
    type: 'info',
    app: 'System',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    message: 'System update completed for',
  },
];

export default function DashboardPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  // Handle app disconnection
  const handleDisconnectApp = async (appSlug: string) => {
    if (!appSlug) {
      console.error('Cannot disconnect: No app slug provided');
      return;
    }
    
    try {
      setIsProcessing(appSlug);
      await apiClient.disconnectApp(appSlug);
      toast.success('App disconnected successfully');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['apps'] }),
        queryClient.invalidateQueries({ queryKey: ['sessions'] }),
      ]);
    } catch (error) {
      console.error('Disconnection error:', error);
      toast.error('Failed to disconnect app');
    } finally {
      setIsProcessing(null);
    }
  };
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  // Fetch apps data
  const { 
    data: apps = [], 
    isLoading: isLoadingApps,
    refetch: refetchApps 
  } = useQuery<App[]>({
    queryKey: ['apps'],
    queryFn: () => apiClient.getApps(),
  });

  console.log('Apps data from backend:', apps);

  const { 
    data: sessionsResponse, 
    isLoading: isLoadingSessions,
    refetch: refetchSessions 
  } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => apiClient.getUserSessions(),
  });
  
  // Ensure sessions is always an array
  const sessions = Array.isArray(sessionsResponse) ? sessionsResponse : [];

  // Activity data - in a real app, this would come from an API
  const activityData: ActivityItem[] = [
    {
      id: '1',
      type: 'connected',
      app: 'Slack',
      timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
      message: 'Successfully connected to Slack',
    },
    {
      id: '2',
      type: 'error',
      app: 'GitHub',
      timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      message: 'Failed to sync repositories',
    },
  ];

  // Get connected app slugs from sessions
  const connectedAppSlugs = new Set(sessions.map((session) => session.app_slug));
  
  // Transform apps to include connection status
  const availableApps: DashboardApp[] = apps.map((app) => ({
    ...app,
    is_connected: connectedAppSlugs.has(app.app_slug)
  }));
  
  // Filter connected apps
  const connectedApps = availableApps.filter(app => app.is_connected);
  
  console.log('Available apps:', availableApps);
  console.log('Connected apps:', connectedApps);
  
  const totalToolsCount = connectedApps.length; // This will be 0 until we implement connected apps
  
  const recentActivityItems = [...activityData, ...mockActivity]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 5);

  const handleConnectApp = async (appSlug: string) => {
    try {
      setIsProcessing(appSlug);
      await apiClient.connectApp(appSlug);
      toast.success('App connected successfully');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['apps'] }),
        queryClient.invalidateQueries({ queryKey: ['sessions'] }),
      ]);
    } catch (error) {
      console.error('Connection error:', error);
      toast.error('Failed to connect app');
    } finally {
      setIsProcessing(null);
    }
  };

  // Wrapper function with additional logging
  const handleDisconnectAppWithLogging = async (appSlug: string) => {
    console.log('Disconnecting app with slug:', appSlug);
    if (!appSlug) {
      console.error('Error: appSlug is undefined or empty');
      toast.error('Failed to disconnect: Invalid app identifier');
      return;
    }
    
    try {
      setIsProcessing(appSlug);
      console.log('Calling disconnectApp with slug:', appSlug);
      await handleDisconnectApp(appSlug);
      console.log('Successfully disconnected app:', appSlug);
      
      toast.success(`Successfully disconnected from ${appSlug}`);
    } catch (error) {
      console.error('Disconnection error:', error);
      toast.error(`Failed to disconnect from ${appSlug}`);
    } finally {
      setIsProcessing(null);
    }
  };

  if (isLoadingApps || isLoadingSessions) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900">
            Welcome back, {user?.email || 'User'}!
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Here's what's happening with your MCP server connections.
          </p>
        </div>
      </div>

      {/* Connected Apps */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Connected Apps</h2>
        </div>
        {connectedApps.length === 0 ? (
          <div className="text-center py-12 bg-white shadow rounded-lg">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              No connected apps
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by connecting an app.
            </p>
            <div className="mt-6">
              <button
                type="button"
                onClick={() => router.push('/dashboard/apps')}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Connect App
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connectedApps.map((app: App) => (
              <div key={app.app_slug} className="relative bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 bg-white rounded-md p-1 relative">
                      <img 
                        src={app.logo_url} 
                        alt={`${app.name} logo`} 
                        className="h-10 w-10 object-contain"
                        onError={(e) => {
                          // Fallback to first letter of app name if logo fails to load
                          const fallback = document.createElement('div');
                          fallback.className = 'h-10 w-10 rounded-md bg-gray-100 flex items-center justify-center';
                          fallback.innerHTML = `<span class="text-xs font-medium text-gray-500">${app.name.charAt(0)}</span>`;
                          e.currentTarget.parentNode?.replaceChild(fallback, e.currentTarget);
                        }}
                      />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-900 truncate">
                          {app.name}
                        </dt>
                        <dd>
                          <div className="text-sm text-gray-500">
                            {app.description}
                          </div>
                          <div className="mt-1">
                            {app.app_category?.map((category) => (
                              <span 
                                key={`${app.app_slug}-${category}`}
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-1"
                              >
                                {category}
                              </span>
                            ))}
                          </div>
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-5 py-3">
                  <div className="text-sm">
                    <button
                      onClick={() => {
                        console.log('Disconnect button clicked for app:', app);
                        if (!app || !app.app_slug) {
                          console.error('App or app_slug is undefined:', app);
                          toast.error('Cannot disconnect: Invalid app data');
                          return;
                        }
                        handleDisconnectApp(app.app_slug);
                      }}
                      disabled={isProcessing === app.app_slug}
                      className="font-medium text-red-600 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing === app.app_slug ? 'Disconnecting...' : 'Disconnect'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available Apps */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Available Apps</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {availableApps
            .filter((app: any) => !connectedApps.some((a: any) => a.app_slug === app.app_slug))
            .slice(0, 3)
            .map((app: any) => (
              <div key={`available-${app.app_slug}`} className="relative bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 bg-white rounded-md p-1">
                      <img 
                        src={app.logo_url} 
                        alt={`${app.name} logo`} 
                        className="h-10 w-10 object-contain opacity-75"
                        onError={(e) => {
                          // Fallback to first letter of app name if logo fails to load
                          const fallback = document.createElement('div');
                          fallback.className = 'h-10 w-10 rounded-md bg-gray-100 flex items-center justify-center';
                          fallback.innerHTML = `<span class="text-xs font-medium text-gray-400">${app.name.charAt(0)}</span>`;
                          e.currentTarget.parentNode?.replaceChild(fallback, e.currentTarget);
                        }}
                      />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-900 truncate">
                          {app.name}
                        </dt>
                        <dd>
                          <div className="text-sm text-gray-500">
                            {app.description}
                          </div>
                          <div className="mt-1">
                            {app.app_category?.map((category) => (
                              <span 
                                key={`${app.app_slug}-${category}`}
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 mr-1"
                              >
                                {category}
                              </span>
                            ))}
                          </div>
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-5 py-3">
                  <div className="text-sm">
                    <button
                      onClick={() => handleConnectApp(app.app_slug)}
                      disabled={isProcessing === app.app_slug}
                      className="font-medium text-blue-600 hover:text-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing === app.app_slug ? 'Connecting...' : 'Connect'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
        </div>
        {availableApps.filter((app: any) => !connectedApps.some((a: any) => a.app_slug === app.slug)).length > 3 && (
          <div className="mt-4 text-right">
            <button
              onClick={() => router.push('/dashboard/apps')}
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              View all apps <span aria-hidden="true">&rarr;</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
