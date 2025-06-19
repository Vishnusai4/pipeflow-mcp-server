'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

export function AuthProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, checkAuth, user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const isAuth = await checkAuth();
        if (!isAuth && !window.location.pathname.startsWith('/login')) {
          router.push('/login');
        } else if (isAuth && window.location.pathname === '/login') {
          router.push('/dashboard');
        }
      } catch (error) {
        console.error('Auth verification failed:', error);
        if (!window.location.pathname.startsWith('/login')) {
          router.push('/login');
        }
      } finally {
        setIsLoading(false);
      }
    };

    verifyAuth();
  }, [checkAuth, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }


  return <>{children}</>;
}
