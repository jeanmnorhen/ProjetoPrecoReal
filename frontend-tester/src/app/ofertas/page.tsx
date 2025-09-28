// frontend-tester/src/app/ofertas/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface Offer {
  id: string;
  product_id: string;
  offer_price: number;
  start_date: string;
  end_date: string;
  offer_type: string;
}

const OFFERS_API_URL = process.env.NEXT_PUBLIC_OFFERS_API_URL;

export default function OfertasPage() {
  const { idToken, currentUser, loading: authLoading } = useAuth();

  const [offer, setOffer] = useState<Partial<Offer>>({ product_id: "", offer_price: 0, start_date: "", end_date: "", offer_type: "" });
  const [offerIdToFetch, setOfferIdToFetch] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setOffer(prev => ({ ...prev, [name]: value }));
  };

  const clearMessages = () => {
    setError(null);
    setMessage(null);
  };

  const handleCreateOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken) return setError("Login necessário.");
    clearMessages();
    setLoading(true);

    const offerToCreate: { product_id: string; offer_price: number; start_date: string; end_date: string; offer_type: string; } = {
      product_id: offer.product_id || "",
      offer_price: parseFloat(String(offer.offer_price)) || 0,
      start_date: offer.start_date || "",
      end_date: offer.end_date || "",
      offer_type: offer.offer_type || "",
    };

    try {
      const response = await fetch(`${OFFERS_API_URL}/api/offers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(offerToCreate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage(`Oferta criada com sucesso! ID: ${data.offerId}`);
      setOffer({ product_id: "", offer_price: 0, start_date: "", end_date: "", offer_type: "" }); // Reset form
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFetchOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${OFFERS_API_URL}/api/offers/${offerIdToFetch}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setOffer(data);
      setMessage("Oferta encontrada.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setOffer({ product_id: "", offer_price: 0, start_date: "", end_date: "", offer_type: "" }); // Reset form on error
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idToken || !offer.id) return setError("Login e oferta carregada necessários.");
    clearMessages();
    setLoading(true);

    const offerToUpdate: { product_id?: string; offer_price?: number; start_date?: string; end_date?: string; offer_type?: string; } = {
      product_id: offer.product_id,
      offer_price: parseFloat(String(offer.offer_price)) || 0,
      start_date: offer.start_date,
      end_date: offer.end_date,
      offer_type: offer.offer_type,
    };

    try {
      const response = await fetch(`${OFFERS_API_URL}/api/offers/${offer.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(offerToUpdate),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP error! status: ${response.status}`);
      setMessage("Oferta atualizada com sucesso.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteOffer = async () => {
    if (!idToken || !offer.id) return setError("Login e oferta carregada necessários.");
    clearMessages();
    setLoading(true);

    try {
      const response = await fetch(`${OFFERS_API_URL}/api/offers/${offer.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${idToken}` },
      });
      if (response.status !== 204) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setMessage("Oferta deletada com sucesso.");
      setOffer({ product_id: "", offer_price: 0, start_date: "", end_date: "", offer_type: "" }); // Reset form
      setOfferIdToFetch("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) return <div className="text-center p-10">Carregando autenticação...</div>;

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Autenticação</h1>
        <p className="text-center mb-4">Você precisa se autenticar para gerenciar ofertas.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Gerenciamento de Oferta</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Buscar Oferta por ID</h2>
        <form onSubmit={handleFetchOffer} className="flex items-center gap-4">
          <input
            type="text"
            placeholder="ID da Oferta"
            className="flex-grow mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={offerIdToFetch}
            onChange={(e) => setOfferIdToFetch(e.target.value)}
          />
          <button type="submit" className="py-2 px-4 bg-gray-600 text-white rounded-md hover:bg-gray-700" disabled={loading}>
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </form>
      </div>

      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">{offer.id ? "Editar Oferta" : "Criar Nova Oferta"}</h2>
        {offer.id && <p className="text-sm text-gray-600 mb-4">ID: {offer.id}</p>}
        <form onSubmit={offer.id ? handleUpdateOffer : handleCreateOffer} className="space-y-4">
          <input name="product_id" type="text" placeholder="ID do Produto" value={offer.product_id || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="offer_price" type="number" placeholder="Preço da Oferta" value={offer.offer_price || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="start_date" type="datetime-local" placeholder="Data de Início" value={offer.start_date || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="end_date" type="datetime-local" placeholder="Data de Término" value={offer.end_date || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          <input name="offer_type" type="text" placeholder="Tipo da Oferta" value={offer.offer_type || ""} onChange={handleInputChange} required className="w-full px-3 py-2 border rounded"/>
          
          <div className="flex items-center gap-4">
            <button type="submit" className="py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700" disabled={loading}>
              {loading ? "Salvando..." : (offer.id ? "Atualizar" : "Criar")}
            </button>
            {offer.id && (
              <button type="button" onClick={handleDeleteOffer} className="py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700" disabled={loading}>
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
