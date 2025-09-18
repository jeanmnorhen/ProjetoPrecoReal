// frontend-tester/src/app/healthcheck/page.tsx
"use client";

import { useState, useEffect } from "react";

export default function HealthCheckPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
                const response = await fetch(`https://servico-healthcheck-17676sqek-jeanmnorhens-projects.vercel.app/health`);
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
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center min-h-screen">Loading health check...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center min-h-screen text-red-500">Error: {error}</div>;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="p-8 bg-white rounded shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center">Health Check Status</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
          {status}
        </pre>
      </div>
    </div>
  );
}
