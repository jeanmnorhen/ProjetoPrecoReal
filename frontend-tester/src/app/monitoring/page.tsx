// frontend-tester/src/app/monitoring/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface PriceHistory {
  time: string;
  price: number;
  product_id: string;
}

const MONITORING_API_URL = process.env.NEXT_PUBLIC_MONITORING_API_URL;

export default function MonitoringPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const [productId, setProductId] = useState("");
  const [history, setHistory] = useState<PriceHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetchHistory = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setHistory([]);

    if (!productId) {
      setError("Please enter a Product ID.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${MONITORING_API_URL}/api/monitoring/prices?product_id=${productId}`);

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setHistory(data.data || []);
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
        <p className="text-center mb-4">Você precisa se autenticar para ver o monitoramento.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Price Monitoring</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <form onSubmit={handleFetchHistory} className="flex space-x-4">
          <input
            type="text"
            placeholder="Enter Product ID"
            className="flex-grow px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700"
            disabled={loading}
          >
            {loading ? "Fetching..." : "Fetch History"}
          </button>
        </form>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>

      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">Price History for: {productId}</h2>
        {history.length > 0 ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {history.map((record) => (
                <tr key={record.time}>
                  <td className="px-6 py-4 whitespace-nowrap">{new Date(record.time).toLocaleString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{record.price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No history found for this product, or none fetched yet.</p>
        )}
      </div>
    </div>
  );
}
