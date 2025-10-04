// frontend-tester/src/app/admin/canonicos/page.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import AdminLayout from "../../../components/AdminLayout";
import { useAuth } from "../../../context/AuthContext";

// --- Tipos de Dados (espelhando api/schemas.py) ---
interface ProductData {
    product_name: string;
    category_standard: string;
    description_long: string;
    features_list: string[];
}

interface TaskStatus {
    task_id: string;
    status: string;
    result?: ProductData;
    error?: string;
}

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AI_API_URL;

// --- Custom Hook para Polling --- 
const useTaskPolling = (taskId: string | null, onComplete: (data: ProductData) => void, onError: (error: string) => void) => {
    useEffect(() => {
        if (!taskId) return;

        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`${AGENTS_API_URL}/api/agents/task-status/${taskId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data: TaskStatus = await response.json();

                if (data.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    if (data.result) {
                        onComplete(data.result);
                    } else {
                        onError("A tarefa foi concluída com sucesso, mas não retornou resultados.");
                    }
                } else if (data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    onError(data.error || "Ocorreu uma falha desconhecida na tarefa.");
                }
                // Se o status for PENDING, o polling continua

            } catch (err: unknown) {
                clearInterval(intervalId);
                onError(err instanceof Error ? err.message : "Erro ao verificar o status da tarefa.");
            }
        }, 3000); // Poll a cada 3 segundos

        // Cleanup no unmount do componente
        return () => clearInterval(intervalId);

    }, [taskId, onComplete, onError]);
};


export default function CatalogFeederPage() {
    const { idToken } = useAuth();
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [processing, setProcessing] = useState(false);
    const [finalResult, setFinalResult] = useState<ProductData | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleCompletion = useCallback((data: ProductData) => {
        setFinalResult(data);
        setProcessing(false);
        setTaskId(null);
    }, []);

    const handleError = useCallback((errorMessage: string) => {
        setError(errorMessage);
        setProcessing(false);
        setTaskId(null);
    }, []);

    useTaskPolling(taskId, handleCompletion, handleError);

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setImageFile(e.target.files[0]);
            setFinalResult(null);
            setError(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!imageFile) {
            setError("Por favor, selecione um arquivo de imagem.");
            return;
        }
        if (!idToken || !AGENTS_API_URL) {
            setError("Aplicação não configurada corretamente (API URL ou Token).");
            return;
        }

        setProcessing(true);
        setFinalResult(null);
        setError(null);
        setTaskId(null);

        const formData = new FormData();
        formData.append("file", imageFile);

        try {
            const response = await fetch(`${AGENTS_API_URL}/api/agents/catalog-intake`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${idToken}`,
                },
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            // Inicia o polling ao receber o task_id
            setTaskId(data.task_id);

        } catch (err: unknown) {
            handleError(err instanceof Error ? err.message : "Ocorreu um erro desconhecido ao submeter a tarefa.");
        }
    };

    return (
        <AdminLayout>
            <div className="container mx-auto p-4">
                <h1 className="text-2xl font-bold mb-6">Alimentador de Catálogo com IA (Local)</h1>

                <div className="bg-white p-6 rounded shadow-md mb-6">
                    <h2 className="text-xl font-semibold mb-4">Análise de Produto por Imagem</h2>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="imageUpload" className="block text-sm font-medium text-gray-700">Imagem do Produto</label>
                            <input
                                type="file"
                                id="imageUpload"
                                accept="image/*"
                                onChange={handleImageChange}
                                className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                                disabled={processing}
                            />
                            {imageFile && <p className="mt-2 text-sm text-gray-500">Arquivo selecionado: {imageFile.name}</p>}
                        </div>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400"
                            disabled={processing || !imageFile}
                        >
                            {processing ? "Processando..." : "Enviar para Análise"}
                        </button>
                    </form>
                </div>

                {processing && (
                    <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6" role="alert">
                        <p className="font-bold">Processando Imagem...</p>
                        <p>A tarefa foi enviada para o worker de IA (Task ID: {taskId}).</p>
                        <p>O resultado aparecerá aqui automaticamente quando estiver pronto.</p>
                    </div>
                )}

                {error && (
                    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6" role="alert">
                        <p className="font-bold">Erro!</p>
                        <p>{error}</p>
                    </div>
                )}

                {finalResult && (
                    <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-6">
                        <p className="font-bold">Sucesso! Produto Analisado:</p>
                        <pre className="mt-2 text-sm text-green-800 bg-white p-3 rounded overflow-auto">{JSON.stringify(finalResult, null, 2)}</pre>
                    </div>
                )}
            </div>
        </AdminLayout>
    );
}