// frontend-tester/src/components/CriticismQueueTable.tsx
"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import CriticismResolutionModal from "./CriticismResolutionModal";

interface Critica {
  id: string;
  produto_id: string;
  tipo_critica: string;
  comentario: string;
  status: string;
  criado_em: string;
}

const USERS_API_URL = process.env.NEXT_PUBLIC_USERS_API_URL;

export default function CriticismQueueTable() {
  const { idToken } = useAuth();
  const [criticas, setCriticas] = useState<Critica[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCriticism, setSelectedCriticism] = useState<Critica | null>(null);

  const fetchCriticas = async () => {
    if (!idToken || !USERS_API_URL) {
      setError("Token de autenticação ou URL da API de Usuários não disponível.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${USERS_API_URL}/api/criticas`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data: Critica[] = await response.json();
      setCriticas(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCriticas();
  }, [idToken]);

  const handleResolveClick = (critica: Critica) => {
    setSelectedCriticism(critica);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCriticism(null);
    fetchCriticas(); // Refresh the list after closing modal
  };

  if (loading) {
    return <div className="text-center p-10">Carregando críticas...</div>;
  }

  if (error) {
    return <div className="text-center p-10 text-red-500">Erro ao carregar críticas: {error}</div>;
  }

  return (
    <div className="overflow-x-auto">
      {criticas.length === 0 ? (
        <p className="text-gray-600">Nenhuma crítica pendente no momento.</p>
      ) : (
        <table className="min-w-full bg-white">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produto ID</th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo de Crítica</th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Comentário</th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {criticas.map((critica) => (
              <tr key={critica.id} className="hover:bg-gray-50">
                <td className="py-4 px-4 whitespace-nowrap text-sm font-medium text-gray-900">{critica.produto_id}</td>
                <td className="py-4 px-4 whitespace-nowrap text-sm text-gray-700">{critica.tipo_critica}</td>
                <td className="py-4 px-4 max-w-sm">
                  <p className="text-sm text-gray-700 truncate">{critica.comentario}</p>
                </td>
                <td className="py-4 px-4 whitespace-nowrap text-sm text-gray-500">{new Date(critica.criado_em).toLocaleDateString()}</td>
                <td className="py-4 px-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => handleResolveClick(critica)}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    Resolver
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {isModalOpen && selectedCriticism && (
        <CriticismResolutionModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          criticism={selectedCriticism}
        />
      )}
    </div>
  );
}
