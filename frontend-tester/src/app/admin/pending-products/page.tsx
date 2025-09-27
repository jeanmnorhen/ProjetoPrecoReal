// frontend-tester/src/app/admin/pending-products/page.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import AdminLayout from "../../../components/AdminLayout";
import { useAuth } from "../../../context/AuthContext";
import ProductReviewModal from "../../../components/ProductReviewModal"; // Importar o modal

interface Product {
  id: string;
  name: string;
  description?: string;
  category: string;
  image_url?: string;
  status: string;
  created_at: string; // ISO string
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function PendingProductsPage() {
  const { idToken } = useAuth();
  const [pendingProducts, setPendingProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false); // Estado para controlar o modal
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null); // Produto selecionado para revisão

  const fetchPendingProducts = useCallback(async () => {
    if (!idToken) {
      setError("Token de autenticação não disponível.");
      setLoading(false);
      return;
    }
    if (!PRODUCTS_API_URL) {
      setError("URL da API de Produtos não configurada.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/pending`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setPendingProducts(data.products || []);
    } catch (err: any) {
      setError(err.message || "Ocorreu um erro desconhecido ao buscar produtos pendentes.");
    } finally {
      setLoading(false);
    }
  }, [idToken]);

  useEffect(() => {
    fetchPendingProducts();
  }, [fetchPendingProducts]);

  const handleOpenReviewModal = (product: Product) => {
    setSelectedProduct(product);
    setIsModalOpen(true);
  };

  const handleCloseReviewModal = () => {
    setIsModalOpen(false);
    setSelectedProduct(null);
    fetchPendingProducts(); // Recarrega a lista após fechar o modal
  };

  const handleApprove = async (productId: string) => {
    if (!idToken || !PRODUCTS_API_URL) return;
    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${productId}/approve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      alert("Produto aprovado com sucesso!");
      handleCloseReviewModal(); // Fecha o modal e recarrega
    } catch (err: any) {
      alert(`Erro ao aprovar produto: ${err.message}`);
    }
  };

  const handleReject = async (productId: string) => {
    if (!idToken || !PRODUCTS_API_URL) return;
    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${productId}/reject`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      alert("Produto rejeitado com sucesso!");
      handleCloseReviewModal(); // Fecha o modal e recarrega
    } catch (err: any) {
      alert(`Erro ao rejeitar produto: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="container mx-auto p-4">
          <h1 className="text-2xl font-bold mb-6">Produtos Pendentes de Aprovação</h1>
          <p>Carregando produtos...</p>
        </div>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <div className="container mx-auto p-4">
          <h1 className="text-2xl font-bold mb-6">Produtos Pendentes de Aprovação</h1>
          <p className="text-red-500">Erro: {error}</p>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-6">Produtos Pendentes de Aprovação</h1>

        {pendingProducts.length === 0 ? (
          <p>Nenhum produto pendente de aprovação no momento.</p>
        ) : (
          <div className="overflow-x-auto bg-white rounded shadow-md">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nome</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoria</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Imagem</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Criado Em</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pendingProducts.map((product) => (
                  <tr key={product.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{product.id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{product.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{product.category}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {product.image_url && (
                        <img src={product.image_url} alt={product.name} className="h-10 w-10 object-cover rounded-full" />
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{product.status}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{new Date(product.created_at).toLocaleString()}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleOpenReviewModal(product)}
                        className="text-blue-600 hover:text-blue-900 mr-2"
                      >
                        Revisar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de Revisão */}
      <ProductReviewModal
        isOpen={isModalOpen}
        onClose={handleCloseReviewModal}
        product={selectedProduct}
        onProductApproved={() => handleApprove(selectedProduct!.id)} // Passa a função de aprovação
        onProductRejected={() => handleReject(selectedProduct!.id)} // Passa a função de rejeição
      />
    </AdminLayout>
  );
}
