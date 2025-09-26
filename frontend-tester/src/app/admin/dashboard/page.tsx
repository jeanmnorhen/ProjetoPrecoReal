// frontend-tester/src/app/admin/dashboard/page.tsx
"use client";

import { useEffect, useState } from 'react';
import AdminLayout from '../../../components/AdminLayout';
import StatCard from '../../../components/StatCard';
import PriceTrendChart from '../../../components/PriceTrendChart';
import UsageChart from '../../../components/UsageChart';
import { useAuth } from '../../../context/AuthContext';

const MONITORING_API_URL = process.env.NEXT_PUBLIC_MONITORING_API_URL;

interface UsageMetrics {
  active_users_today: number;
  searches_per_day: { date: string; count: number }[];
}

interface PriceMetrics {
    average_price_trend: { date: string; avg_price: number }[];
}

interface GeneralMetrics {
  pending_critiques_count: number;
  canonical_products_count: number;
}

export default function DashboardPage() {
  const { idToken } = useAuth();
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);
  const [priceMetrics, setPriceMetrics] = useState<PriceMetrics | null>(null);
  const [generalMetrics, setGeneralMetrics] = useState<GeneralMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!idToken || !MONITORING_API_URL) {
        setLoading(false);
        setError("Pré-condições para busca de dados não atendidas (token ou URL da API).");
        return;
      }

      try {
        setLoading(true);
        const [usageRes, priceRes, generalRes] = await Promise.all([
          fetch(`${MONITORING_API_URL}/api/metricas/uso`, { headers: { Authorization: `Bearer ${idToken}` } }),
          fetch(`${MONITORING_API_URL}/api/metricas/precos`, { headers: { Authorization: `Bearer ${idToken}` } }),
          fetch(`${MONITORING_API_URL}/api/metricas/gerais`, { headers: { Authorization: `Bearer ${idToken}` } })
        ]);

        if (!usageRes.ok || !priceRes.ok || !generalRes.ok) {
          throw new Error('Falha ao buscar uma ou mais métricas.');
        }

        const usageData = await usageRes.json();
        const priceData = await priceRes.json();
        const generalData = await generalRes.json();

        setUsageMetrics(usageData);
        setPriceMetrics(priceData);
        setGeneralMetrics(generalData);

      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Ocorreu um erro desconhecido.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [idToken]);

  if (loading) {
    return <AdminLayout><div className="text-center">Carregando métricas...</div></AdminLayout>;
  }

  if (error) {
    return <AdminLayout><div className="text-center text-red-500">Erro: {error}</div></AdminLayout>;
  }

  return (
    <AdminLayout>
      <div>
        {/* Stat Cards Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard 
            title="Usuários Ativos Hoje" 
            value={usageMetrics?.active_users_today.toLocaleString() || 'N/A'} 
          />
          <StatCard 
            title="Pesquisas no Último Dia" 
            value={usageMetrics?.searches_per_day[usageMetrics.searches_per_day.length - 1]?.count.toLocaleString() || 'N/A'} 
          />
          <StatCard 
            title="Críticas Pendentes" 
            value={generalMetrics?.pending_critiques_count.toLocaleString() || 'N/A'}
          />
          <StatCard 
            title="Produtos no Catálogo" 
            value={generalMetrics?.canonical_products_count.toLocaleString() || 'N/A'}
          />
        </div>

        {/* Charts Section */}
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Tendência de Preços (Mock)</h2>
            <PriceTrendChart data={priceMetrics?.average_price_trend || []} />
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Pesquisas por Dia (Mock)</h2>
            <UsageChart data={usageMetrics?.searches_per_day || []} />
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
