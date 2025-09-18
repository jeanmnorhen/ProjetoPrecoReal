// frontend-tester/src/app/usuarios/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface User {
  id: string;
  email: string;
  name: string;
  location?: { latitude?: number; longitude?: number }; // Allow undefined for lat/lon
}

// URL da API de produção
const USERS_API_URL = process.env.NEXT_PUBLIC_USERS_API_URL;

export default function UsuariosPage() {
  const { idToken, currentUser, loading: authLoading } = useAuth();

  // State for the user being managed (created, fetched, or edited)
  const [user, setUser] = useState<Partial<User>>({ email: "", name: "", location: { latitude: 0, longitude: 0 } });
  const [userIdToFetch, setUserIdToFetch] = useState("");

  // State for feedback and loading
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (name === "latitude" || name === "longitude") {
      setUser(prev => ({
        ...prev,
        location: {
          ...(prev.location || {}),
          [name]: value === "" ? undefined : parseFloat(value)
        }
      }));
    } else {
      setUser(prev => ({ ...prev, [name]: value }));
    }
  };

  const clearMessages = () => {
    setError(null);
    setMessage(null);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken) {
      setError("Você precisa estar logado para criar um usuário.");
      return;
    }
    setLoading(true);
    clearMessages();

    const userToCreate: { email: string; name: string; location?: { latitude?: number; longitude?: number } } = {
      email: user.email || "",
      name: user.name || "",
    };
    if (user.location && (user.location.latitude !== undefined && user.location.longitude !== undefined)) {
      userToCreate.location = { latitude: user.location.latitude, longitude: user.location.longitude };
    }

    try {
      const response = await fetch(`${USERS_API_URL}/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(userToCreate),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage(`Usuário criado com sucesso! ID: ${data.id}`);
      setUser({ email: "", name: "", location: { latitude: 0, longitude: 0 } }); // Reset form
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchUser = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${USERS_API_URL}/users/${userIdToFetch}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setUser(data);
      setMessage("Usuário encontrado.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setUser({ email: "", name: "", location: { latitude: 0, longitude: 0 } }); // Reset form on error
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken || !user.id) {
      setError("Você precisa estar logado e ter um usuário carregado para atualizar.");
      return;
    }
    setLoading(true);
    clearMessages();

    const userToUpdate: { email?: string; name?: string; location?: { latitude?: number; longitude?: number } } = {
      name: user.name,
      email: user.email,
    };
    if (user.location && (user.location.latitude !== undefined && user.location.longitude !== undefined)) {
      userToUpdate.location = { latitude: user.location.latitude, longitude: user.location.longitude };
    }

    try {
      const response = await fetch(`${USERS_API_URL}/users/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(userToUpdate),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage("Usuário atualizado com sucesso.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!idToken || !user.id) {
      setError("Você precisa estar logado e ter um usuário carregado para deletar.");
      return;
    }
    setLoading(true);
    clearMessages();

    try {
      const response = await fetch(`${USERS_API_URL}/users/${user.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });
      if (response.status !== 204) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage("Usuário deletado com sucesso.");
      setUser({ email: "", name: "", location: { latitude: 0, longitude: 0 } }); // Reset form
      setUserIdToFetch("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return <div className="text-center p-10">Carregando autenticação...</div>;
  }

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Autenticação</h1>
        <p className="text-center mb-4">Você precisa se autenticar para gerenciar usuários.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Usuário</h1>

      {/* SEARCH FORM */}
      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Buscar Usuário por ID</h2>
        <form onSubmit={handleFetchUser} className="flex items-center gap-4">
          <input
            type="text"
            placeholder="ID do Usuário"
            className="flex-grow mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={userIdToFetch}
            onChange={(e) => setUserIdToFetch(e.target.value)}
          />
          <button type="submit" className="py-2 px-4 bg-gray-600 text-white rounded-md hover:bg-gray-700" disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </form>
      </div>

      {/* USER FORM (CREATE/EDIT) */}
      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">{user.id ? "Editar Usuário" : "Criar Novo Usuário"}</h2>
        {user.id && <p className="text-sm text-gray-600 mb-4">ID: {user.id}</p>}
        <form onSubmit={user.id ? handleUpdateUser : handleCreateUser} className="space-y-4">
          <input name="email" type="email" placeholder="Email" value={user.email || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="name" type="text" placeholder="Nome" value={user.name || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="latitude" type="number" placeholder="Latitude" value={user.location?.latitude || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          <input name="longitude" type="number" placeholder="Longitude" value={user.location?.longitude || ""} onChange={handleInputChange} className="w-full px-3 py-2 border rounded"/>
          
          <div className="flex items-center gap-4">
            <button type="submit" className="py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700" disabled={loading}>
              {loading ? "Salvando..." : (user.id ? "Atualizar" : "Criar")}
            </button>
            {user.id && (
              <button type="button" onClick={handleDeleteUser} className="py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700" disabled={loading}>
                {loading ? "Deletando..." : "Deletar"}
              </button>
            )}
          </div>
        </form>
      </div>

      {/* FEEDBACK AREA */}
      <div className="mt-6 text-center">
        {loading && <p>Processando...</p>}
        {error && <p className="text-red-500 font-bold">Erro: {error}</p>}
        {message && <p className="text-green-500 font-bold">{message}</p>}
      </div>
    </div>
  );
}
