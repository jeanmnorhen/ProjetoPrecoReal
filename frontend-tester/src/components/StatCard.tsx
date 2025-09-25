// frontend-tester/src/components/StatCard.tsx
"use client";

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'increase' | 'decrease';
}

export default function StatCard({ title, value, change, changeType }: StatCardProps) {
  const isIncrease = changeType === 'increase';
  const changeColor = changeType ? (isIncrease ? 'text-green-500' : 'text-red-500') : 'text-gray-500';

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-sm font-medium text-gray-500 truncate">{title}</h3>
      <p className="mt-1 text-3xl font-semibold text-gray-900">{value}</p>
      {change && (
        <p className={`mt-2 text-sm ${changeColor}`}>
          {change} {changeType && (isIncrease ? '↑' : '↓')}
        </p>
      )}
    </div>
  );
}
