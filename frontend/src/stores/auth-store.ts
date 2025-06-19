import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiClient } from '@/app/api-client';

export type User = {
  id: string;
  username: string;
  email: string;
  created_at: string;
  updated_at: string;
};

type AuthState = {
  isAuthenticated: boolean | null; // null means we don't know yet
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  initialized: boolean;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: null, // Start with null to indicate we don't know yet
      user: null,
      initialized: false,
      login: async (username: string, password: string) => {
        try {
          const loginResponse = await apiClient.login(username, password);
          // The token is already stored in localStorage by the interceptor
          const userData = await apiClient.getCurrentUser();
          set({ isAuthenticated: true, user: userData, initialized: true });
          return userData;
        } catch (error) {
          console.error('Login failed:', error);
          localStorage.removeItem('token');
          set({ isAuthenticated: false, user: null, initialized: true });
          throw error;
        }
      },
      logout: async () => {
        try {
          await apiClient.logout();
        } finally {
          set({ isAuthenticated: false, user: null });
        }
      },
      checkAuth: async () => {
        const token = localStorage.getItem('token');
        if (!token) {
          set({ isAuthenticated: false, user: null, initialized: true });
          return false;
        }
        
        try {
          const userData = await apiClient.getCurrentUser();
          set({ isAuthenticated: true, user: userData, initialized: true });
          return true;
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('token');
          set({ isAuthenticated: false, user: null, initialized: true });
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
