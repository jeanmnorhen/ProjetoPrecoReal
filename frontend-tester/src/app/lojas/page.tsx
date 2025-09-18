// frontend-tester/src/app/lojas/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface Store {
  id: string;
  name: string;
  address: string;
  store_category: string;
  description: string;
  location?: { latitude?: number; longitude?: number }; // Allow undefined for lat/lon
}

const STORES_API_URL = process.env.NEXT_PUBLIC_STORES_API_URL;

export default function LojasPage() {
  const { idToken, currentUser, loading: authLoading } = useAuth();

  const [store, setStore] = useState<Partial<Store>>({ name: "", address: "", store_category: "", description: "", location: { latitude: 0, longitude: 0 } });
  const [storeIdToFetch, setStoreIdToFetch] = useState("");
  const [allStores, setAllStores] = useState<Store[]>([]); // New state for listing all stores

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    if (name === "latitude" || name === "longitude") {
      setStore(prev => ({
        ...prev,
        location: {
          ...(prev.location || {}),
          [name]: value === "" ? undefined : parseFloat(value)
        }
      }));
    } else {
      setStore(prev => ({ ...prev, [name]: value }));
    }
  };

  const clearMessages = () => {
    setError(null);
    setMessage(null);
  };

  const handleCreateStore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken) return setError("Login necessário.");
    clearMessages();
    setLoading(true);

    const storeToCreate: { name: string; address: string; store_category: string; description: string; location?: { latitude?: number; longitude?: number } } = {
      name: store.name || "",
      address: store.address || "",
      store_category: store.store_category || "",
      description: store.description || "",
    };
    if (store.location && (store.location.latitude !== undefined && store.location.longitude !== undefined)) {
      storeToCreate.location = { latitude: store.location.latitude, longitude: store.location.longitude };
    }

    try {
      const response = await fetch(`${STORES_API_URL}/api/stores`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(storeToCreate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage(`Loja criada com sucesso! ID: ${data.storeId}`);
      setStore({ name: "", address: "", store_category: "", description: "", location: { latitude: 0, longitude: 0 } }); // Reset form
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchStore = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${STORES_API_URL}/api/stores/${storeIdToFetch}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setStore(data);
      setMessage("Loja encontrada.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setStore({ name: "", address: "", store_category: "", description: "", location: { latitude: 0, longitude: 0 } }); // Reset form on error
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken || !store.id) return setError("Login e loja carregada necessários.");
    clearMessages();
    setLoading(true);

    const storeToUpdate: { name?: string; address?: string; store_category?: string; description?: string; location?: { latitude?: number; longitude?: number } } = {
      name: store.name,
      address: store.address,
      store_category: store.store_category,
      description: store.description,
    };
    if (store.location && (store.location.latitude !== undefined && store.location.longitude !== undefined)) {
      storeToUpdate.location = { latitude: store.location.latitude, longitude: store.location.longitude };
    }

    try {
      const response = await fetch(`${STORES_API_URL}/api/stores/${store.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(storeToUpdate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage("Loja atualizada com sucesso.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStore = async () => {
    if (!idToken || !store.id) return setError("Login e loja carregada necessários.");
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${STORES_API_URL}/api/stores/${store.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${idToken}` },
      });
      if (response.status !== 204) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage("Loja deletada com sucesso.");
      setStore({ name: "", address: "", store_category: "", description: "", location: { latitude: 0, longitude: 0 } }); // Reset form
      setStoreIdToFetch("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchAllStores = async () => {
    if (!idToken) return setError("Login necessário.");
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${STORES_API_URL}/api/stores`, {
        headers: { Authorization: `Bearer ${idToken}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setAllStores(data.stores || []); // Assuming the API returns { stores: [...] }
      setMessage(`Total de ${data.stores?.length || 0} lojas encontradas.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setAllStores([]);
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) return <div className="text-center p-10">Carregando autenticação...</div>;

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Autenticação</h1>
        <p className="text-center mb-4">Você precisa se autenticar para gerenciar lojas.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Loja</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Buscar Loja por ID</h2>
        <form onSubmit={handleFetchStore} className="flex items-center gap-4">
          <input
            type="text"
            placeholder="ID da Loja"
            className="flex-grow mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={storeIdToFetch}
            onChange={(e) => setStoreIdToFetch(e.target.value)}
          />
          <button type="submit" className="py-2 px-4 bg-gray-600 text-white rounded-md hover:bg-gray-700" disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </form>
      </div>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Listar Todas as Lojas</h2>
        <button onClick={handleFetchAllStores} className="py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700" disabled={loading}>
          {loading ? "Carregando..." : "Listar Todas"}
        </button>
        {allStores.length > 0 && (
          <div className="mt-4 max-h-60 overflow-y-auto">
            <table className="min-w-full bg-white">
              <thead>
                <tr>
                  <th className="py-2 px-4 border-b">ID</th>
                  <th className="py-2 px-4 border-b">Nome</th>
                  <th className="py-2 px-4 border-b">Ações</th>
                </tr>
              </thead>
              <tbody>
                {allStores.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-100">
                    <td className="py-2 px-4 border-b text-sm">{s.id}</td>
                    <td className="py-2 px-4 border-b text-sm">{s.name}</td>
                    <td className="py-2 px-4 border-b">
                      <button
                        onClick={() => {
                          setStore(s);
                          setStoreIdToFetch(s.id);
                          setMessage("Loja carregada para edição.");
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
        <h2 className="text-xl font-semibold mb-4">{store.id ? "Editar Loja" : "Criar Nova Loja"}</h2>
        {store.id && <p className="text-sm text-gray-600 mb-4">ID: {store.id}</p>}
        <form onSubmit={store.id ? handleUpdateStore : handleCreateStore} className="space-y-4">
          <input name="name" type="text" placeholder="Nome da Loja" value={store.name || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="address" type="text" placeholder="Endereço" value={store.address || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="store_category" type="text" placeholder="Categoria da Loja" value={store.store_category || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <textarea name="description" placeholder="Descrição" value={store.description || ""} onChange={handleInputChange} rows={3} className="w-full px-3 py-2 border rounded"></textarea>
          <input name="latitude" type="number" placeholder="Latitude" value={store.location?.latitude || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          <input name="longitude" type="number" placeholder="Longitude" value={store.location?.longitude || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          
          <div className="flex items-center gap-4">
            <button type="submit" className="py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700" disabled={loading}>
              {loading ? "Salvando..." : (store.id ? "Atualizar" : "Criar")}
            </button>
            {store.id && (
              <button type="button" onClick={handleDeleteStore} className="py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700" disabled={loading}>
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