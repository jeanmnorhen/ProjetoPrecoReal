// frontend-tester/src/components/AdminLayout.tsx
"use client";

import Sidebar from './Sidebar';
import Navbar from './Navbar';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { currentUser, isAdmin, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!currentUser) {
        router.push('/'); // Not logged in, redirect to login
      } else if (!isAdmin) {
        console.log("Acesso negado: usuário não é admin.");
        router.push('/'); // Logged in but not admin, redirect to login/home
      }
    }
  }, [currentUser, isAdmin, loading, router]);

  if (loading || !currentUser || !isAdmin) {
    return (
        <div className="flex h-screen items-center justify-center">
            <p>Verificando permissões...</p>
        </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
