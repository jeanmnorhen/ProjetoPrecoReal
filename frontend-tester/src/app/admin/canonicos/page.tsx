// frontend-tester/src/app/admin/canonicos/page.tsx
"use client";

import { useState } from "react";
import AdminLayout from "../../../components/AdminLayout";
import { useAuth } from "../../../context/AuthContext";

// Tipos específicos para payload e resultado
interface Product {
  id?: string;
  name: string;
  description?: string;
  category: string;
  barcode?: string;
  image_url?: string;
}

interface CatalogIntakePayload {
  text_query?: string;
  category_query?: string;
  image_base64?: string;
}

interface CreationResponseDetails {
  message: string;
  productId: string;
}

interface CatalogIntakeResult {
  message: string;
  product?: Product;
  productIds?: string[];
  imageUrl?: string;
  details?: CreationResponseDetails;
}

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AI_API_URL;

export default function CatalogFeederPage() {
  const { idToken } = useAuth();
  const [textQuery, setTextQuery] = useState("");
  const [categoryQuery, setCategoryQuery] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<CatalogIntakeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImageFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProcessing(true);
    setResult(null);
    setError(null);

    if (!idToken) {
      setError("Token de autenticação não disponível.");
      setProcessing(false);
      return;
    }
    if (!AGENTS_API_URL) {
      setError("URL da API de Agentes de IA não configurada.");
      setProcessing(false);
      return;
    }

    const payload: CatalogIntakePayload = {};
    if (textQuery) {
      payload.text_query = textQuery;
    } else if (categoryQuery) {
      payload.category_query = categoryQuery;
    } else if (imageFile) {
      const reader = new FileReader();
      reader.readAsDataURL(imageFile);
      reader.onloadend = async () => {
        const base64Image = reader.result?.toString().split(',')[1];
        if (base64Image) {
          payload.image_base64 = base64Image;
          await sendRequest(payload);
        } else {
          setError("Falha ao ler a imagem.");
          setProcessing(false);
        }
      };
      return; 
    } else {
      setError("Por favor, forneça um texto, categoria ou imagem.");
      setProcessing(false);
      return;
    }

    await sendRequest(payload);
  };

  const sendRequest = async (payload: CatalogIntakePayload) => {
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/agents/catalog-intake`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      setResult(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Ocorreu um erro desconhecido.");
      }
    } finally {
      setProcessing(false);
    }
  };

  return (
    <AdminLayout>
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-6">Alimentador de Catálogo com IA</h1>

        <div className="bg-white p-6 rounded shadow-md mb-6">
          <h2 className="text-xl font-semibold mb-4">Adicionar/Atualizar Produto</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="textQuery" className="block text-sm font-medium text-gray-700">Nome do Produto (Texto)</label>
              <input
                type="text"
                id="textQuery"
                value={textQuery}
                onChange={(e) => { setTextQuery(e.target.value); setCategoryQuery(""); setImageFile(null); }}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
                placeholder="Ex: Coca-Cola 2L"
                disabled={processing}
              />
            </div>
            <div>
              <label htmlFor="categoryQuery" className="block text-sm font-medium text-gray-700">Categoria (para expandir)</label>
              <input
                type="text"
                id="categoryQuery"
                value={categoryQuery}
                onChange={(e) => { setCategoryQuery(e.target.value); setTextQuery(""); setImageFile(null); }}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm"
                placeholder="Ex: Refrigerantes"
                disabled={processing}
              />
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-gray-500">OU</span>
            </div>
            <div>
              <label htmlFor="imageUpload" className="block text-sm font-medium text-gray-700">Imagem do Produto</label>
              <input
                type="file"
                id="imageUpload"
                accept="image/*"
                onChange={(e) => { handleImageChange(e); setTextQuery(""); setCategoryQuery(""); }}
                className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                disabled={processing}
              />
              {imageFile && <p className="mt-2 text-sm text-gray-500">Arquivo selecionado: {imageFile.name}</p>}
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400"
              disabled={processing || (!textQuery && !imageFile && !categoryQuery)}
            >
              {processing ? "Processando..." : "Enviar para Análise"}
            </button>
          </form>
        </div>

        {processing && (
          <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6" role="alert">
            <p className="font-bold">Processando...</p>
            <p>Aguarde enquanto a IA analisa e processa sua solicitação.</p>
          </div>
        )}

        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6" role="alert">
            <p className="font-bold">Erro!</p>
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-6" role="alert">
            <p className="font-bold">Sucesso!</p>
            <pre className="mt-2 text-sm text-green-800 overflow-auto">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
