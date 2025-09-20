// frontend-tester/src/components/withAdminAuth.tsx
"use client";

import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import { ComponentType, useEffect } from 'react';

export default function withAdminAuth<P extends object>(WrappedComponent: ComponentType<P>) {
  const WithAdminAuth = (props: P) => {
    const { currentUser, isAdmin, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && !currentUser) {
        // Se não está carregando e não há usuário, redireciona para o login
        router.push('/');
      }
      if (!loading && currentUser && !isAdmin) {
        // Se há um usuário mas ele não é admin, redireciona para uma página de acesso negado
        // ou para a home, mostrando uma mensagem.
        console.log("Acesso negado: usuário não é admin.");
        router.push('/'); // Ou para uma página '/acesso-negado'
      }
    }, [currentUser, isAdmin, loading, router]);

    // Enquanto carrega ou se o usuário não for admin, pode-se mostrar um loader ou nada
    if (loading || !isAdmin) {
      return <div className="flex justify-center items-center min-h-screen">Verificando permissões...</div>;
    }

    // Se for admin, renderiza o componente da página
    return <WrappedComponent {...props} />;
  };

  return WithAdminAuth;
}
