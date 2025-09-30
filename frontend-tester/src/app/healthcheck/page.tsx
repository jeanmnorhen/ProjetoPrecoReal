//  frontend-tester/src/app/healthcheck/page.tsx
"use client";

import { useState, useEffect } from "react";

import AdminLayout from "../../components/AdminLayout";

export default function HealthCheckPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

    const HEALTHCHECK_API_URL = process.env.NEXT_PUBLIC_HEALTHCHECK_API_URL;

    useEffect(() => {
      const fetchHealth = async () => {
        if (!HEALTHCHECK_API_URL) {
          setError("URL da API de Healthcheck não configurada.");
          setLoading(false);
          return;
        }
        try {
          const response = await fetch(`${HEALTHCHECK_API_URL}/api/health`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setStatus(JSON.stringify(data, null, 2));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };

        fetchHealth();
        }, [HEALTHCHECK_API_URL]);

  return (
    <AdminLayout>
      <div className="p-8 bg-white rounded shadow-md w-full max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-6 text-center">Health Check Status</h2>
        {loading ? (
          <p>Loading health check...</p>
        ) : error ? (
          <p className="text-red-500">Error: {error}</p>
        ) : (
          <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
            {status}
          </pre>
        )}
      </div>
    </AdminLayout>
  );
}
