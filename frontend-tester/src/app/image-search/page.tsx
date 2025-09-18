// frontend-tester/src/app/image-search/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import AuthForm from "../../components/AuthForm";

const AI_API_URL = process.env.NEXT_PUBLIC_AI_API_URL; // URL for servico-agentes-ia

export default function ImageSearchPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [identifiedProduct, setIdentifiedProduct] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
      setIdentifiedProduct(null); // Clear previous result
      setError(null); // Clear previous error
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setIdentifiedProduct(null);

    if (!image) {
      setError("Please select an image to upload.");
      setLoading(false);
      return;
    }

    if (!AI_API_URL) {
      setError("AI API URL is not configured.");
      setLoading(false);
      return;
    }

    // Convert image to Base64
    const reader = new FileReader();
    reader.readAsDataURL(image);
    reader.onloadend = async () => {
      const base64Image = reader.result?.toString().split(',')[1]; // Get base64 string without data:image/jpeg;base64,

      if (!base64Image) {
        setError("Failed to convert image to Base64.");
        setLoading(false);
        return;
      }

      try {
        // For simplicity, we're calling the consume endpoint directly.
        // In a real app, this would be an API Gateway endpoint that triggers the Kafka event.
        const response = await fetch(`${AI_API_URL}/api/agents/consume`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // Authorization header is needed if the consume endpoint is protected
            // "Authorization": `Bearer ${idToken}`,
            // For now, assuming the consume endpoint is called by cron and doesn't need user token
          },
          body: JSON.stringify({
            task_type: "image_analysis",
            task_id: `image-task-${Date.now()}`,
            image_b64: base64Image,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        if (data.results && data.results.length > 0 && data.results[0].identified_product) {
          setIdentifiedProduct(data.results[0].identified_product);
        } else if (data.status === "No new messages to process") {
            setError("No new messages were processed. Ensure the Kafka producer is sending messages.");
        } else {
          setError("Product identification failed or no product found.");
        }

      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };
  };

  if (authLoading) return <div className="text-center p-10">Carregando autenticação...</div>;

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4 text-center">Autenticação</h1>
        <p className="text-center mb-4">Você precisa se autenticar para usar a busca por imagem.</p>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Image Search for Products</h1>

      <div className="bg-white p-4 rounded shadow-md mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="image-upload" className="block text-sm font-medium text-gray-700">Upload Image</label>
            <input
              type="file"
              id="image-upload"
              accept="image/*"
              onChange={handleImageChange}
              className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          {imagePreview && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold">Image Preview:</h3>
              <img src={imagePreview} alt="Image Preview" className="mt-2 max-w-xs max-h-xs object-contain" />
            </div>
          )}
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Analyze Image"}
          </button>
        </form>
        {error && <p className="text-red-500 mt-2">Error: {error}</p>}
      </div>

      {identifiedProduct && (
        <div className="bg-white p-4 rounded shadow-md">
          <h2 className="text-xl font-semibold mb-4">Identified Product:</h2>
          <p className="text-lg font-bold text-green-700">{identifiedProduct}</p>
        </div>
      )}
    </div>
  );
}
