// frontend-tester/src/components/ProductFormModal.tsx
"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

interface Product {
  id?: string;
  name: string;
  description?: string;
  category: string;
  barcode?: string;
  image_url?: string;
}

interface ProductFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void; // Callback to refresh product list
  initialProduct?: Product; // For editing existing products
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function ProductFormModal({ isOpen, onClose, onSave, initialProduct }: ProductFormModalProps) {
  const { idToken } = useAuth();
  const [productData, setProductData] = useState<Product>(initialProduct || { name: "", category: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProductData(initialProduct || { name: "", category: "" });
  }, [initialProduct]);

  if (!isOpen) return null;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setProductData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken || !PRODUCTS_API_URL) {
      setError("Token de autenticação ou URL da API de Produtos não disponível.");
      return;
    }

    setLoading(true);
    setError(null);

    const method = productData.id ? "PUT" : "POST";
    const url = productData.id ? `${PRODUCTS_API_URL}/api/products/${productData.id}` : `${PRODUCTS_API_URL}/api/products`;

    try {
      const response = await fetch(url, {
        method: method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(productData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      alert(`Produto ${productData.id ? "atualizado" : "criado"} com sucesso!`);
      onSave(); // Refresh the list in the parent component
      onClose(); // Close the modal
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">{productData.id ? "Editar Produto Canônico" : "Criar Novo Produto Canônico"}</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">Nome do Produto</label>
            <input
              type="text"
              id="name"
              name="name"
              value={productData.name}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
              required
            />
          </div>
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700">Descrição Detalhada</label>
            <textarea
              id="description"
              name="description"
              value={productData.description || ""}
              onChange={handleInputChange}
              rows={3}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            ></textarea>
          </div>
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700">Categoria</label>
            <select
              id="category"
              name="category"
              value={productData.category}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
              required
            >
              <option value="">Selecione uma Categoria</option>
              {/* TODO: Fetch categories dynamically */}
              <option value="eletronicos">Eletrônicos</option>
              <option value="alimentos">Alimentos</option>
              <option value="bebidas">Bebidas</option>
              <option value="limpeza">Limpeza</option>
            </select>
          </div>
          <div>
            <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">Código de Barras (EAN/UPC)</label>
            <input
              type="text"
              id="barcode"
              name="barcode"
              value={productData.barcode || ""}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            />
          </div>
          <div>
            <label htmlFor="image_url" className="block text-sm font-medium text-gray-700">URL da Imagem de Alta Qualidade</label>
            <input
              type="text"
              id="image_url"
              name="image_url"
              value={productData.image_url || ""}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            />
          </div>
          
          {error && <p className="text-red-500 text-sm mt-2">Erro: {error}</p>}

          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              disabled={loading}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              disabled={loading}
            >
              {loading ? "Salvando..." : (productData.id ? "Salvar Alterações" : "Criar Produto")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
