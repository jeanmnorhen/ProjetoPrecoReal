// frontend-tester/src/app/produtos/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface Product {
  id: string;
  name: string;
  store_id: string;
  price: number;
  category: string;
}

const PRODUCTS_API_URL = process.env.NEXT_PUBLIC_PRODUCTS_API_URL;

export default function ProdutosPage() {
  const { idToken, currentUser, loading: authLoading } = useAuth();

  const [product, setProduct] = useState<Partial<Product>>({ name: "", store_id: "", price: 0, category: "" });
  const [productIdToFetch, setProductIdToFetch] = useState("");
  const [allProducts, setAllProducts] = useState<Product[]>([]); // New state for listing all products

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProduct(prev => ({ ...prev, [name]: name === "price" ? parseFloat(value) || 0 : value }));
  };

  const clearMessages = () => {
    setError(null);
    setMessage(null);
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken) return setError("Login necessário.");
    clearMessages();
    setLoading(true);

    const productToCreate: { name: string; store_id: string; price: number; category: string; } = {
      name: product.name || "",
      store_id: product.store_id || "",
      price: product.price || 0,
      category: product.category || "",
    };

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(productToCreate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage(`Produto criado com sucesso! ID: ${data.productId}`);
      setProduct({ name: "", store_id: "", price: 0, category: "" }); // Reset form
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${productIdToFetch}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setProduct(data);
      setMessage("Produto encontrado.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setProduct({ name: "", store_id: "", price: 0, category: "" });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken || !product.id) return setError("Login e produto carregado necessários.");
    clearMessages();
    setLoading(true);

    const productToUpdate: { name?: string; store_id?: string; price?: number; category?: string; } = {
      name: product.name,
      store_id: product.store_id,
      price: product.price,
      category: product.category,
    };

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${product.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(productToUpdate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage("Produto atualizado com sucesso.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProduct = async () => {
    if (!idToken || !product.id) return setError("Login e produto carregado necessários.");
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products/${product.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${idToken}` },
      });
      if (response.status !== 204) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage("Produto deletado com sucesso.");
      setProduct({ name: "", store_id: "", price: 0, category: "" });
      setProductIdToFetch("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchAllProducts = async () => {
    if (!idToken) return setError("Login necessário.");
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${PRODUCTS_API_URL}/api/products`, {
        headers: { Authorization: `Bearer ${idToken}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setAllProducts(data.products || []); // Assuming the API returns { products: [...] }
      setMessage(`Total de ${data.products?.length || 0} produtos encontrados.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setAllProducts([]);
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) return <div className="text-center p-10">Carregando autenticação...</div>;

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Autenticação</h1>
        <p className="text-center mb-4">Você precisa se autenticar para gerenciar produtos.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Produto</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Buscar Produto por ID</h2>
        <form onSubmit={handleFetchProduct} className="flex items-center gap-4">
          <input
            type="text"
            placeholder="ID do Produto"
            className="flex-grow mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={productIdToFetch}
            onChange={(e) => setProductIdToFetch(e.target.value)}
          />
          <button type="submit" className="py-2 px-4 bg-gray-600 text-white rounded-md hover:bg-gray-700" disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </form>
      </div>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Listar Todos os Produtos</h2>
        <button onClick={handleFetchAllProducts} className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700" disabled={loading}>
          {loading ? "Carregando..." : "Listar Todos"}
        </button>
        {allProducts.length > 0 && (
          <div className="mt-4 max-h-60 overflow-y-auto">
            <table className="min-w-full bg-white">
              <thead>
                <tr>
                  <th className="py-2 px-4 border-b">ID</th>
                  <th className="py-2 px-4 border-b">Nome</th>
                  <th className="py-2 px-4 border-b">Loja ID</th>
                  <th className="py-2 px-4 border-b">Preço</th>
                  <th className="py-2 px-4 border-b">Ações</th>
                </tr>
              </thead>
              <tbody>
                {allProducts.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-100">
                    <td className="py-2 px-4 border-b text-sm">{p.id}</td>
                    <td className="py-2 px-4 border-b text-sm">{p.name}</td>
                    <td className="py-2 px-4 border-b text-sm">{p.store_id}</td>
                    <td className="py-2 px-4 border-b text-sm">{p.price}</td>
                    <td className="py-2 px-4 border-b">
                      <button
                        onClick={() => {
                          setProduct(p);
                          setProductIdToFetch(p.id);
                          setMessage("Produto carregado para edição.");
                        }}
                        className="text-indigo-600 hover:text-indigo-900 text-sm"
                      >
                        Editar/Ver
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
        <h2 className="text-xl font-semibold mb-4">{product.id ? "Editar Produto" : "Criar Novo Produto"}</h2>
        {product.id && <p className="text-sm text-gray-600 mb-4">ID: {product.id}</p>}
        <form onSubmit={product.id ? handleUpdateProduct : handleCreateProduct} className="space-y-4">
          <input name="name" type="text" placeholder="Nome do Produto" value={product.name || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="store_id" type="text" placeholder="ID da Loja" value={product.store_id || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="price" type="number" placeholder="Preço" value={product.price || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          <input name="category" type="text" placeholder="Categoria" value={product.category || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          
          <div className="flex items-center gap-4">
            <button type="submit" className="py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700" disabled={loading}>
              {loading ? "Salvando..." : (product.id ? "Atualizar" : "Criar")}
            </button>
            {product.id && (
              <button type="button" onClick={handleDeleteProduct} className="py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700" disabled={loading}>
                {loading ? "Deletando..." : "Deletar"}
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="mt-6 text-center">
        {loading && <p>Processando...</p>}
        {error && <p className="text-red-500 font-bold">Erro: {error}</p>}
        {message && <p className="text-green-500 font-bold">{message}</p>}
      </div>
    </div>
  );
}
