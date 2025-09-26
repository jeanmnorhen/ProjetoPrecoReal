// frontend-tester/src/app/admin/vitrine/page.tsx
"use client";

import { useState, useEffect, useMemo } from "react";
import AdminLayout from "../../../components/AdminLayout";
import { useAuth } from "../../../context/AuthContext";

// Interfaces
interface Store {
  id: string;
  name: string;
}

interface Product {
  id: string;
  name: string;
  category: string;
  barcode?: string;
  store_id?: string; // Canonical products won't have this
}

interface AddToStoreState {
  product: Product | null;
  price: string;
}

// API URLs from environment variables
const STORES_API_URL = process.env.NEXT_PUBLIC_STORES_API_URL;
const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

// Modal Component
function AddToStoreModal({ 
  isOpen, 
  onClose, 
  onSave, 
  productName 
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onSave: (price: number) => void; 
  productName: string; 
}) {
  const [price, setPrice] = useState("");

  if (!isOpen) return null;

  const handleSave = () => {
    const numericPrice = parseFloat(price);
    if (!isNaN(numericPrice) && numericPrice > 0) {
      onSave(numericPrice);
      setPrice("");
    } else {
      alert("Por favor, insira um preço válido.");
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">Adicionar à Vitrine</h2>
        <p className="mb-4">Defina o preço para o produto: <span className="font-semibold">{productName}</span></p>
        <div>
          <label htmlFor="price" className="block text-sm font-medium text-gray-700">Preço (R$)</label>
          <input
            type="number"
            id="price"
            name="price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            required
            min="0.01"
            step="0.01"
          />
        </div>
        <div className="mt-6 flex justify-end space-x-3">
          <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-50">
            Cancelar
          </button>
          <button type="button" onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Salvar na Loja
          </button>
        </div>
      </div>
    </div>
  );
}

// Main Page Component
export default function VitrinePage() {
  const { idToken, currentUser } = useAuth();
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>("");
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalState, setModalState] = useState<AddToStoreState>({ product: null, price: "" });

  // Fetch user's stores
  useEffect(() => {
    if (!idToken || !STORES_API_URL) return;
    const fetchStores = async () => {
      try {
        const response = await fetch(`${STORES_API_URL}/api/stores`, { 
          headers: { Authorization: `Bearer ${idToken}` }
        });
        if (!response.ok) throw new Error("Falha ao buscar lojas.");
        const data = await response.json();
        // Assuming the API returns { stores: [...] } and we only want stores owned by the current user
        // This logic needs to be adjusted if the API doesn't provide owner info.
        // For now, we'll assume the API correctly returns only the user's stores.
        setStores(data.stores || []);
        if (data.stores && data.stores.length > 0) {
          setSelectedStoreId(data.stores[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro desconhecido");
      }
    };
    fetchStores();
  }, [idToken]);

  // Fetch all products (canonical and store-specific)
  useEffect(() => {
    if (!idToken || !PRODUCTS_API_URL) return;
    setLoading(true);
    const fetchProducts = async () => {
      try {
        const response = await fetch(`${PRODUCTS_API_URL}/api/products`, { 
          headers: { Authorization: `Bearer ${idToken}` }
        });
        if (!response.ok) throw new Error("Falha ao buscar produtos.");
        const data = await response.json();
        setAllProducts(data.products || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro desconhecido");
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, [idToken]);

  // Memoize filtered lists
  const canonicalProducts = useMemo(() => 
    allProducts.filter(p => !p.store_id)
  , [allProducts]);

  const currentStoreProducts = useMemo(() => 
    allProducts.filter(p => p.store_id === selectedStoreId)
  , [allProducts, selectedStoreId]);

  const handleOpenModal = (product: Product) => {
    setModalState({ product, price: "" });
  };

  const handleCloseModal = () => {
    setModalState({ product: null, price: "" });
  };

  const handleSaveProductToStore = async (price: number) => {
    if (!modalState.product || !selectedStoreId || !idToken || !PRODUCTS_API_URL) {
      alert("Erro: Informações faltando para salvar.");
      return;
    }

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/from_canonical`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          canonical_product_id: modalState.product.id,
          store_id: selectedStoreId,
          price: price,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Falha ao adicionar produto à loja.");
      }

      alert(data.message);
      handleCloseModal();
      // Refetch all products to update the UI
      const refetchResponse = await fetch(`${PRODUCTS_API_URL}/api/products`, { headers: { Authorization: `Bearer ${idToken}` }});
      const refetchData = await refetchResponse.json();
      setAllProducts(refetchData.products || []);

    } catch (err) {
      alert(err instanceof Error ? err.message : "Ocorreu um erro.");
    }
  };

  return (
    <AdminLayout>
      <h1 className="text-2xl font-bold mb-6">Vitrine da Loja</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <label htmlFor="store-select" className="block text-sm font-medium text-gray-700 mb-2">Selecione a Loja para Gerenciar:</label>
        <select 
          id="store-select"
          value={selectedStoreId}
          onChange={(e) => setSelectedStoreId(e.target.value)}
          className="w-full p-2 border rounded-md"
          disabled={stores.length === 0}
        >
          {stores.length > 0 ? (
            stores.map(store => <option key={store.id} value={store.id}>{store.name}</option>)
          ) : (
            <option>Nenhuma loja encontrada...</option>
          )}
        </select>
      </div>

      {error && <p className="text-red-500 mb-4">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Canonical Products Catalog */}
        <div className="bg-white p-4 rounded shadow-md">
          <h2 className="text-xl font-semibold mb-4">Catálogo de Produtos Canônicos</h2>
          {loading ? <p>Carregando catálogo...</p> : (
            <div className="max-h-96 overflow-y-auto">
              <table className="min-w-full">
                <thead><tr><th className="text-left p-2">Produto</th><th className="text-left p-2">Ação</th></tr></thead>
                <tbody>
                  {canonicalProducts.map(p => (
                    <tr key={p.id} className="border-b hover:bg-gray-50">
                      <td className="p-2">{p.name} <span className="text-xs text-gray-500">({p.category})</span></td>
                      <td className="p-2">
                        <button 
                          onClick={() => handleOpenModal(p)}
                          className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                          disabled={!selectedStoreId}
                        >
                          Adicionar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Current Store's Products */}
        <div className="bg-white p-4 rounded shadow-md">
          <h2 className="text-xl font-semibold mb-4">Produtos na sua Vitrine</h2>
          {loading ? <p>Carregando produtos da loja...</p> : (
             <div className="max-h-96 overflow-y-auto">
              <table className="min-w-full">
                <thead><tr><th className="text-left p-2">Produto</th><th className="text-left p-2">Preço</th></tr></thead>
                <tbody>
                  {currentStoreProducts.map(p => (
                    <tr key={p.id} className="border-b">
                      <td className="p-2">{p.name}</td>
                      <td className="p-2">R$ {p.price?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <AddToStoreModal 
        isOpen={!!modalState.product}
        onClose={handleCloseModal}
        onSave={handleSaveProductToStore}
        productName={modalState.product?.name || ''}
      />
    </AdminLayout>
  );
}
