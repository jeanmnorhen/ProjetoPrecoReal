// frontend-tester/src/app/admin/criticas/page.tsx
"use client";

import AdminLayout from "../../../components/AdminLayout";
import CriticismQueueTable from "../../../components/CriticismQueueTable";

export default function CriticasPage() {
  return (
    <AdminLayout>
      <h1 className="text-2xl font-bold mb-6">Fila de Críticas de Produtos</h1>
      <div className="bg-white p-6 rounded-lg shadow-md">
        <CriticismQueueTable />
      </div>
    </AdminLayout>
  );
}
