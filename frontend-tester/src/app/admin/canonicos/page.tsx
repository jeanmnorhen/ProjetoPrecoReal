// frontend-tester/src/app/admin/canonicos/page.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import AdminLayout from "../../../components/AdminLayout";
import { useAuth } from "../../../context/AuthContext";
import CanonicalProductsTable from "../../../components/CanonicalProductsTable";
import ProductFormModal from "../../../components/ProductFormModal";

interface Suggestion {
  id: string;
  term: string;
  source: string;
  status: string;
  created_at: string; // ISO string
  task_id?: string;
}

interface Product {
  id?: string;
  name: string;
  description?: string;
  category: string;
  barcode?: string;
  image_url?: string;
}

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL;

function CanonicosPage() {
  const { idToken } = useAuth();
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [errorSuggestions, setErrorSuggestions] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | undefined>(undefined);

  const fetchSuggestions = useCallback(async () => {
    if (!idToken) {
      setErrorSuggestions("Token de autenticação não disponível.");
      setLoadingSuggestions(false);
      return;
    }
    if (!AGENTS_API_URL) {
      setErrorSuggestions("URL da API de Agentes não configurada.");
      setLoadingSuggestions(false);
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
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorSuggestions(err.message);
      } else {
        setErrorSuggestions("An unknown error occurred");
      }
    } finally {
      setLoadingSuggestions(false);
    }
  }, [idToken]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleCreateProductClick = () => {
    setSelectedProduct(undefined); // Clear any previously selected product
    setIsModalOpen(true);
  };

  const handleEditProduct = (product: Product) => {
    setSelectedProduct(product);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedProduct(undefined);
    // No need to refetch products here, CanonicalProductsTable will manage its own state
  };

  const handleProductSaved = () => {
    // This callback will be passed to ProductFormModal and called after a product is saved.
    // It will trigger a refresh of the CanonicalProductsTable.
    // The CanonicalProductsTable component will handle its own data fetching.
  };

  return (
    <AdminLayout>
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-6">Gerenciamento de Produtos Canônicos</h1>
        
        <div class="bg-white p-4 rounded shadow-md mb-6">
          <h2 class="text-xl font-semibold mb-4">Sugestões Pendentes</h2>
          {loadingSuggestions ? (
             <div class="text-center p-10">Carregando sugestões...</div>
          ) : errorSuggestions ? (
            <div class="text-center p-10 text-red-500">Erro ao carregar sugestões: {errorSuggestions}</div>
          ) : suggestions.length === 0 ? (
            <p class="text-gray-600">Nenhuma sugestão pendente no momento.</p>
          ) : (
            <div class="overflow-x-auto">
              <table class="min-w-full bg-white">
                <thead>
                  <tr>
                    <th class="py-2 px-4 border-b text-left">ID</th>
                    <th class="py-2 px-4 border-b text-left">Termo</th>
                    <th class="py-2 px-4 border-b text-left">Origem</th>
                    <th class="py-2 px-4 border-b text-left">Status</th>
                    <th class="py-2 px-4 border-b text-left">Criado Em</th>
                    <th class="py-2 px-4 border-b text-left">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {suggestions.map((s) => (
                    <tr key={s.id} class="hover:bg-gray-100">
                      <td class="py-2 px-4 border-b text-sm">{s.id}</td>
                      <td class="py-2 px-4 border-b text-sm">{s.term}</td>
                      <td class="py-2 px-4 border-b text-sm">{s.source}</td>
                      <td class="py-2 px-4 border-b text-sm">{s.status}</td>
                      <td class="py-2 px-4 border-b text-sm">{new Date(s.created_at).toLocaleString()}</td>
                      <td class="py-2 px-4 border-b text-sm">
                        <button class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-2 rounded text-xs mr-2">
                          Buscar Produtos
                        </button>
                        <button class="bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-xs">
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

        <div class="bg-white p-4 rounded shadow-md">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-semibold">Catálogo Canônico</h2>
            <button
              onClick={handleCreateProductClick}
              class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Adicionar Novo Produto
            </button>
          </div>
          <CanonicalProductsTable onEditProduct={handleEditProduct} />
        </div>
      </div>

      <ProductFormModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSave={handleProductSaved}
        initialProduct={selectedProduct}
      />
    </AdminLayout>
  );
}

export default CanonicosPage;
