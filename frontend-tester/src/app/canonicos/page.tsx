// frontend-tester/src/app/canonicos/page.tsx
"use client";

import withAdminAuth from "../../components/withAdminAuth";

function CanonicosPage() {
  // O conteúdo da página permanece o mesmo, a lógica de auth foi abstraída pelo HOC
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

// Envolver a página com o HOC de autenticação de admin
export default withAdminAuth(CanonicosPage);
