// frontend-tester/src/components/CanonicalProductsTable.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import Image from "next/image";

interface Product {
  id: string;
  name: string;
  description?: string;
  category: string;
  barcode?: string;
  image_url?: string;
}

interface CanonicalProductsTableProps {
  onEditProduct: (product: Product) => void;
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function CanonicalProductsTable({ onEditProduct }: CanonicalProductsTableProps) {
  const { idToken } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("");

  const fetchProducts = useCallback(async () => {
    if (!idToken || !PRODUCTS_API_URL) {
      setError("Token de autenticação ou URL da API de Produtos não disponível.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${PRODUCTS_API_URL}/api/products`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setProducts(data.products || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [idToken]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleDeleteProduct = async (productId: string) => {
    if (!idToken || !PRODUCTS_API_URL) {
      alert("Token de autenticação ou URL da API de Produtos não disponível.");
      return;
    }
    if (!confirm("Tem certeza que deseja excluir este produto?")) {
      return;
    }

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${productId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      alert("Produto excluído com sucesso!");
      fetchProducts(); // Refresh list
    } catch (err: unknown) {
      alert(`Erro ao excluir produto: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const filteredProducts = products.filter(product => {
    const matchesSearch = searchTerm === "" || 
                          product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          product.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          product.barcode?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterCategory === "" || product.category.toLowerCase() === filterCategory.toLowerCase();
    return matchesSearch && matchesCategory;
  });

  if (loading) {
    return <div className="text-center p-10">Carregando catálogo de produtos...</div>;
  }

  if (error) {
    return <div className="text-center p-10 text-red-500">Erro ao carregar produtos: {error}</div>;
  }

  return (
    <div>
      <div className="mb-4 flex space-x-4">
        <input
          type="text"
          placeholder="Buscar por nome, descrição, código de barras..."
          className="flex-grow px-3 py-2 border rounded-md shadow-sm"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <select
          className="px-3 py-2 border rounded-md shadow-sm"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
        >
          <option value="">Todas as Categorias</option>
          {/* TODO: Fetch categories dynamically from an API */}
          <option value="eletronicos">Eletrônicos</option>
          <option value="alimentos">Alimentos</option>
          <option value="bebidas">Bebidas</option>
          <option value="limpeza">Limpeza</option>
        </select>
      </div>

      {filteredProducts.length === 0 ? (
        <p className="text-gray-600">Nenhum produto canônico encontrado.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white">
            <thead className="bg-gray-50">
              <tr>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Imagem</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nome</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoria</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Código de Barras</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredProducts.map((product) => (
                <tr key={product.id} className="hover:bg-gray-50">
                  <td className="py-4 px-4 whitespace-nowrap text-sm font-medium text-gray-900">{product.id}</td>
                  <td className="py-4 px-4 whitespace-nowrap text-sm text-gray-700">
                    {product.image_url ? (
                      <Image src={product.image_url} alt={product.name} width={40} height={40} className="h-10 w-10 object-cover rounded-full" />
                    ) : (
                      <span className="text-gray-400">Sem Imagem</span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-sm text-gray-700">{product.name}</td>
                  <td className="py-4 px-4 whitespace-nowrap text-sm text-gray-700">{product.category}</td>
                  <td className="py-4 px-4 whitespace-nowrap text-sm text-gray-700">{product.barcode || 'N/A'}</td>
                  <td className="py-4 px-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => onEditProduct(product)}
                      className="text-indigo-600 hover:text-indigo-900 mr-3"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDeleteProduct(product.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}