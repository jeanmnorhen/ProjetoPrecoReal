// frontend-tester/src/components/PriceTrendChart.tsx
"use client";

"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PriceTrendProps {
  data: { date: string; avg_price: number }[];
}

export default function PriceTrendChart({ data }: PriceTrendProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center">
        <p className="text-gray-500">Sem dados de tendência de preço para exibir.</p>
      </div>
    );
  }

  return (
    <>
      {/* 384px is h-96 */}
      <ResponsiveContainer width="100%" height={384}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="avg_price" stroke="#8884d8" name="Preço Médio" />
      </LineChart>
    </ResponsiveContainer>
    </>
  );
}
