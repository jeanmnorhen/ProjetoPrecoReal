// frontend-tester/src/components/UsageChart.tsx
"use client";

"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface UsageChartProps {
  data: { date: string; count: number }[];
}

export default function UsageChart({ data }: UsageChartProps) {
    if (!data || data.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center">
        <p className="text-gray-500">Sem dados de uso para exibir.</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={384}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="count" fill="#82ca9d" name="Nº de Pesquisas" />
      </BarChart>
    </ResponsiveContainer>
  );
}
