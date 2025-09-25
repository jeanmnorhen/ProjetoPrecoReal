// frontend-tester/src/components/CriticismResolutionModal.tsx
"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

interface CriticismResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  criticism: Critica; // Use the Critica interface
}

interface Critica {
  id: string;
  produto_id: string;
  tipo_critica: string;
  comentario: string;
  status: string;
  criado_em: string;
}

interface Product {
  id: string;
  name: string;
  description: string;
  store_id: string;
  // Adicione outros campos do produto canônico conforme necessário
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function CriticismResolutionModal({ isOpen, onClose, criticism }: CriticismResolutionModalProps) {
  const { idToken } = useAuth();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!isOpen || !criticism?.produto_id || !idToken || !PRODUCTS_API_URL) {
      setLoading(false);
      return;
    }

    const fetchProduct = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${PRODUCTS_API_URL}/api/products/${criticism.produto_id}`, {
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data: Product = await response.json();
        setProduct(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [isOpen, criticism?.produto_id, idToken]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setProduct((prev) => (prev ? { ...prev, [name]: value } : null));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!product || !idToken || !PRODUCTS_API_URL) return;

    try {
      setIsSaving(true);
      setError(null);
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${product.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(product),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      alert("Produto atualizado com sucesso!");
      onClose(); // Fecha o modal e recarrega a lista de críticas
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-2xl w-full">
        <h2 className="text-2xl font-bold mb-4">Resolver Crítica</h2>
        {loading ? (
          <p>Carregando detalhes do produto...</p>
        ) : error ? (
          <p className="text-red-500">Erro: {error}</p>
        ) : product ? (
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">ID da Crítica:</label>
              <p className="text-gray-900">{criticism.id}</p>
            </div>
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">Tipo de Crítica:</label>
              <p className="text-gray-900">{criticism.tipo_critica}</p>
            </div>
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">Comentário:</label>
              <p className="text-gray-900">{criticism.comentario}</p>
            </div>

            <h3 className="text-xl font-semibold mt-6 mb-4">Editar Produto Canônico</h3>
            <div className="mb-4">
              <label htmlFor="productName" className="block text-gray-700 text-sm font-bold mb-2">Nome do Produto:</label>
              <input
                type="text"
                id="productName"
                name="name"
                value={product.name}
                onChange={handleInputChange}
                className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                required
              />
            </div>
            <div className="mb-4">
              <label htmlFor="productDescription" className="block text-gray-700 text-sm font-bold mb-2">Descrição:</label>
              <textarea
                id="productDescription"
                name="description"
                value={product.description}
                onChange={handleInputChange}
                className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                rows={4}
              ></textarea>
            </div>
            {/* Adicione outros campos do produto aqui */}

            <div className="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={isSaving}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={isSaving}
              >
                {isSaving ? "Salvando..." : "Salvar Alterações do Produto"}
              </button>
              <button
                type="button"
                onClick={onClose} // Por enquanto, apenas fecha e recarrega a lista
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                disabled={isSaving}
              >
                Resolver Crítica (Apenas Fechar)
              </button>
            </div>
          </form>
        ) : (
          <p>Nenhuma crítica selecionada ou produto não encontrado.</p>
        )}
      </div>
    </div>
  );
}
