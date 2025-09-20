// frontend-tester/src/app/canonicos/page.tsx
"use client";

import { useState, useEffect } from "react";
import withAdminAuth from "../../components/withAdminAuth";
import { useAuth } from "../../context/AuthContext"; // Import useAuth

interface Suggestion {
  id: string;
  term: string;
  source: string;
  status: string;
  created_at: string; // ISO string
  task_id?: string;
}

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL; // Define this in .env.local

function CanonicosPage() {
  const { idToken } = useAuth(); // Get idToken from context
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (!idToken) {
        setError("Token de autenticação não disponível.");
        setLoading(false);
        return;
      }
      if (!AGENTS_API_URL) {
        setError("URL da API de Agentes não configurada.");
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${AGENTS_API_URL}/api/agents/suggestions`, {
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data: Suggestion[] = await response.json();
        setSuggestions(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSuggestions();
  }, [idToken]); // Re-fetch if idToken changes

  if (loading) {
    return <div className="text-center p-10">Carregando sugestões...</div>;
  }

  if (error) {
    return <div className="text-center p-10 text-red-500">Erro ao carregar sugestões: {error}</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Produtos Canônicos</h1>
      
      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Sugestões Pendentes</h2>
        {suggestions.length === 0 ? (
          <p className="text-gray-600">Nenhuma sugestão pendente no momento.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white">
              <thead>
                <tr>
                  <th className="py-2 px-4 border-b text-left">ID</th>
                  <th className="py-2 px-4 border-b text-left">Termo</th>
                  <th className="py-2 px-4 border-b text-left">Origem</th>
                  <th className="py-2 px-4 border-b text-left">Status</th>
                  <th className="py-2 px-4 border-b text-left">Criado Em</th>
                  <th className="py-2 px-4 border-b text-left">Ações</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-100">
                    <td className="py-2 px-4 border-b text-sm">{s.id}</td>
                    <td className="py-2 px-4 border-b text-sm">{s.term}</td>
                    <td className="py-2 px-4 border-b text-sm">{s.source}</td>
                    <td className="py-2 px-4 border-b text-sm">{s.status}</td>
                    <td className="py-2 px-4 border-b text-sm">{new Date(s.created_at).toLocaleString()}</td>
                    <td className="py-2 px-4 border-b text-sm">
                      <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-2 rounded text-xs mr-2">
                        Buscar Produtos
                      </button>
                      <button className="bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-xs">
                        Rejeitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">Catálogo Canônico</h2>
        <p className="text-gray-600">[Tabela com produtos canônicos existentes para CRUD aparecerá aqui]</p>
      </div>
    </div>
  );
}

export default withAdminAuth(CanonicosPage);
