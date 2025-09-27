// frontend-tester/src/components/ProductReviewModal.tsx
"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

interface Product {
  id: string;
  name: string;
  description?: string;
  category: string;
  image_url?: string;
  status: string;
  created_at: string; // ISO string
}

interface ProductReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: Product | null;
  onProductApproved: () => void;
  onProductRejected: () => void;
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function ProductReviewModal({
  isOpen,
  onClose,
  product,
  onProductApproved,
  onProductRejected,
}: ProductReviewModalProps) {
  const { idToken } = useAuth();
  const [editedProduct, setEditedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setEditedProduct({ ...product });
    }
  }, [product]);

  if (!isOpen || !editedProduct) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setEditedProduct((prev) => (prev ? { ...prev, [name]: value } : null));
  };

  const handleSave = async () => {
    if (!idToken || !PRODUCTS_API_URL || !editedProduct?.id) return;
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${editedProduct.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          name: editedProduct.name,
          description: editedProduct.description,
          category: editedProduct.category,
          image_url: editedProduct.image_url, // Assuming image_url can be edited directly for now
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      alert("Produto atualizado com sucesso!");
      onClose();
      // onProductApproved(); // Optionally refresh parent list if needed after edit
    } catch (err: any) {
      setError(err.message || "Erro ao salvar alterações.");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!editedProduct?.id) return;
    await handleSave(); // Save changes before approving
    onProductApproved();
  };

  const handleReject = async () => {
    if (!editedProduct?.id) return;
    onProductRejected();
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-2xl w-full">
        <h2 className="text-2xl font-bold mb-4">Revisar Produto: {editedProduct.name}</h2>
        {error && <div className="text-red-500 mb-4">Erro: {error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">Nome</label>
            <input type="text" name="name" value={editedProduct.name} onChange={handleChange} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Categoria</label>
            <input type="text" name="category" value={editedProduct.category} onChange={handleChange} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm" />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Descrição</label>
            <textarea name="description" value={editedProduct.description || ''} onChange={handleChange} rows={4} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"></textarea>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">URL da Imagem Principal</label>
            <input type="text" name="image_url" value={editedProduct.image_url || ''} onChange={handleChange} className="mt-1 block w-full border-gray-300 rounded-md shadow-sm" />
            {editedProduct.image_url && (
              <img src={editedProduct.image_url} alt="Product Image" className="mt-2 max-h-48 object-contain" />
            )}
          </div>
          {/* TODO: Adicionar lógica para múltiplas imagens e seleção da principal */}
        </div>

        <div className="flex justify-end space-x-3">
          <button onClick={onClose} className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-50" disabled={loading}>
            Cancelar
          </button>
          <button onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700" disabled={loading}>
            Salvar Edições
          </button>
          <button onClick={handleApprove} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700" disabled={loading}>
            Aprovar Produto
          </button>
          <button onClick={handleReject} className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700" disabled={loading}>
            Rejeitar Produto
          </button>
        </div>
      </div>
    </div>
  );
}
