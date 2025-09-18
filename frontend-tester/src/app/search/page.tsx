// frontend-tester/src/app/search/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

interface SearchResult {
  id: string;
  type: string; // e.g., 'users', 'products', 'stores', 'offers'
  name?: string;
  email?: string;
  address?: string;
  // Add other relevant fields based on your data structure
}

const SEARCH_API_URL = process.env.NEXT_PUBLIC_SEARCH_API_URL;

export default function SearchPage() {
  const { idToken, currentUser, loading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults([]);

    if (!query) {
      setError("Please enter a search query.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${SEARCH_API_URL}/api/search?q=${encodeURIComponent(query)}`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResults(data.results);
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
        <p className="text-center mb-4">Você precisa se autenticar para usar a busca.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Search</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <form onSubmit={handleSearch} className="flex space-x-4">
          <input
            type="text"
            placeholder="Search for products, stores, users..."
            className="flex-grow px-3 py-2 border border-gray-300 rounded-md shadow-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700"
            disabled={loading}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>

      <div className="bg-white p-4 rounded shadow-md">
        <h2 className="text-xl font-semibold mb-4">Search Results</h2>
        {results.length === 0 && !loading && !error && query && (
          <p>No results found for &quot;{query}&quot;.</p>
        )}
        {results.length === 0 && !loading && !error && !query && (
          <p>Enter a query to search.</p>
        )}
        {results.length > 0 && (
          <ul className="divide-y divide-gray-200">
            {results.map((result) => (
              <li key={result.id} className="py-4">
                <p className="text-lg font-semibold">{result.name || result.email || result.id}</p>
                <p className="text-sm text-gray-600">Type: {result.type}</p>
                {result.address && <p className="text-sm text-gray-600">Address: {result.address}</p>}
                {/* Add more fields as needed */}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}