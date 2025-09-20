// frontend-tester/src/app/canonicos/page.tsx
"use client";

import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

export default function CanonicosPage() {
  const { currentUser, loading } = useAuth();

  if (loading) {
    return <div className="text-center p-10">Carregando...</div>;
  }

  // Idealmente, teríamos uma verificação de `isAdmin` aqui.
  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Acesso Negado</h1>
        <p className="text-center mb-4">Você precisa ser um administrador para acessar esta página.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Produtos Canônicos</h1>
      
      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Sugestões Pendentes</h2>
        <p className="text-gray-600">[Tabela de sugestões de produtos para revisão aparecerá aqui]</p>
      </div>

      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">Catálogo Canônico</h2>
        <p className="text-gray-600">[Tabela com produtos canônicos existentes para CRUD aparecerá aqui]</p>
      </div>
    </div>
  );
}
