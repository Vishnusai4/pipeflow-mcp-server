import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import { normalizeAppSlug } from '@/utils/appUtils';

const API_BASE_URL = 'http://localhost:8000';

// App types
export type App = {
  app_slug: string;
  name: string;
  logo_url: string;
  app_category: string[];
  description: string;
  is_connected?: boolean; // This is added client-side based on sessions
};

export type AppsResponse = {
  apps: App[];
};

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type User = {
  username: string;
  email?: string;
  full_name?: string;
  disabled?: boolean;
};

class ApiClient {
  private client: AxiosInstance;
  private static instance: ApiClient;

  private constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      xsrfCookieName: 'csrftoken',
      xsrfHeaderName: 'X-CSRFToken',
    });

    this.setupInterceptors();
  }

  public static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized errors
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth methods
  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      console.log('Sending login request with:', { username, password: password ? '[HIDDEN]' : 'empty' });
      const response = await this.client.post<LoginResponse>('/login', 
        { 
          username: username.trim(),
          password: password 
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          withCredentials: true,
          validateStatus: (status) => status < 500 // Don't throw for 4xx errors
        }
      );
      
      console.log('Login response:', response.data);
      
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      
      return response.data;
      
    } catch (error: any) {
      console.error('Login error:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Response data:', error.response.data);
        console.error('Response status:', error.response.status);
        console.error('Response headers:', error.response.headers);
      } else if (error.request) {
        // The request was made but no response was received
        console.error('No response received:', error.request);
      } else if (error instanceof Error) {
        // Something happened in setting up the request that triggered an Error
        console.error('Error message:', error.message);
      } else {
        console.error('Unknown error:', error);
      }
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/logout');
    } finally {
      localStorage.removeItem('token');
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/me');
    return response.data;
  }

  // App methods
  async getApps(): Promise<App[]> {
    const response = await this.client.get<App[]>('/apps');
    return response.data;
  }

  async connectApp(appSlug: string): Promise<{ connect_link: string; redirect_url: string }> {
    const normalizedSlug = normalizeAppSlug(appSlug);
    const response = await this.client.post('/connect_app', 
      { app_slug: normalizedSlug },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        withCredentials: true,
      }
    );
    const { connect_link, redirect_url } = response.data;
    
    // If we have a connect_link, open it in a new window
    if (connect_link) {
      const width = 600;
      const height = 700;
      const left = (window.screen.width - width) / 2;
      const top = (window.screen.height - height) / 2;
      
      const authWindow = window.open(
        connect_link,
        `oauth_${appSlug}`,
        `width=${width},height=${height},top=${top},left=${left},scrollbars=yes,resizable=yes`
      );
      
      if (!authWindow) {
        throw new Error('popup_blocked');
      }
      
      // Return a promise that resolves when the window is closed
      return new Promise((resolve, reject) => {
        const checkPopup = setInterval(() => {
          if (authWindow.closed) {
            clearInterval(checkPopup);
            resolve({ connect_link, redirect_url });
          }
        }, 1000);
      });
    }
    
    return { connect_link: '', redirect_url: redirect_url || '/dashboard/apps' };
  }

  async disconnectApp(appSlug: string): Promise<any> {
    const normalizedSlug = normalizeAppSlug(appSlug);
    const response = await this.client.post('/disconnect_app', { app_slug: normalizedSlug });
    return response.data;
  }

  async getUserSessions(): Promise<any> {
    const response = await this.client.get('/user/sessions');
    return response.data;
  }

  async executeTool(toolName: string, params: Record<string, any>): Promise<any> {
    const response = await this.client.post('/execute_tool', {
      tool_name: toolName,
      params
    });
    return response.data;
  }

  // Auth API
  async getSignInLink(appSlug: string, scopes: string[] = ["basic"]): Promise<{ url: string; expiresAt: string }> {
    const normalizedSlug = normalizeAppSlug(appSlug);
    const response = await this.client.post<{ url: string; expiresAt: string }>(`/auth/signin-link`, 
      { 
        app_slug: normalizedSlug,
        scopes,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        withCredentials: true,
      }
    );
    return response.data;
  }

  async handleOAuthCallback(code: string, state: string): Promise<{
    status: string;
    app_slug: string;
    user_id: string;
    access_token: string;
    token_type: string;
    expires_in: number;
  }> {
    const response = await this.client.get<{
      status: string;
      app_slug: string;
      user_id: string;
      access_token: string;
      token_type: string;
      expires_in: number;
    }>(`/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);
    return response.data;
  }

  async getUserConnections(): Promise<Array<{
    app_slug: string;
    status: string;
    scopes: string[];
    connected_at?: string;
    last_used?: string;
    error?: string;
  }>> {
    const response = await this.client.get<{
      sessions: Array<{
        app_slug: string;
        is_active: boolean;
        created_at: string;
        tools_count: number;
      }>
    }>('/user/sessions', {
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });
    
    // Transform the response to match the expected format
    return response.data.sessions.map(session => ({
      app_slug: session.app_slug,
      status: session.is_active ? 'connected' : 'disconnected',
      scopes: [], // This might need to be updated based on your actual data
      connected_at: session.created_at,
      last_used: session.created_at, // Using created_at as last_used if not available
    }));
  }

  // Disconnect an app
  async disconnectAppAuth(appSlug: string): Promise<{ status: string; message: string }> {
    const normalizedSlug = normalizeAppSlug(appSlug);
    console.log(`Disconnecting app: ${normalizedSlug}`);
    const response = await this.client.delete<{ status: string; message: string }>(
      `/disconnect_app/${encodeURIComponent(normalizedSlug)}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        withCredentials: true,
      }
    );
    console.log('Disconnect response:', response.data);
    return response.data;
  }
}

export const apiClient = ApiClient.getInstance();
