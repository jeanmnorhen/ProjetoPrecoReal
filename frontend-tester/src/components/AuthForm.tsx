// frontend-tester/src/components/AuthForm.tsx
"use client";

import { useState, useEffect } from "react";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from "firebase/auth";
import { auth } from "../../lib/firebase"; // Adjust path as needed
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";

export default function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { currentUser, isAdmin, loading: authLoading } = useAuth(); // Get isAdmin and authLoading

  useEffect(() => {
    if (!authLoading && currentUser) { // Check after authLoading is complete
      if (isAdmin) {
        router.push("/admin/dashboard"); // Redirect admins to dashboard
      } else {
        // If a non-admin is already logged in and lands here,
        // they will just see the login form. No redirect needed.
        // The AdminLayout will handle redirecting them if they try to access admin pages.
      }
    }
  }, [currentUser, isAdmin, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let userCredential;
      if (isLogin) {
        if (!auth) {
          setError("Firebase authentication is not available.");
          setLoading(false);
          return;
        }
        userCredential = await signInWithEmailAndPassword(auth, email, password);
      } else {
        if (!auth) {
          setError("Firebase authentication is not available.");
          setLoading(false);
          return;
        }
        userCredential = await createUserWithEmailAndPassword(auth, email, password);
      }

      // After successful login/registration, check admin claim
      const tokenResult = await userCredential.user.getIdTokenResult();
      if (tokenResult.claims.admin === true) {
        router.push("/admin/dashboard"); // Redirect admin to dashboard
      } else {
        setError("Você não tem permissão para acessar este painel.");
        // Sign out non-admin users to prevent them from being stuck in a logged-in state
        if (auth) {
          await auth.signOut();
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === 'string') {
        setError(err);
      } else {
        setError("An unknown error occurred.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded shadow-md w-96">
        <h2 className="text-2xl font-bold mb-6 text-center">
          {isLogin ? "Login" : "Register"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              id="email"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              type="password"
              id="password"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            disabled={loading}
          >
            {loading ? "Processing..." : isLogin ? "Login" : "Register"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="font-medium text-indigo-600 hover:text-indigo-500"
          >
            {isLogin ? "Register" : "Login"}
          </button>
        </p>
        {/* Removed the "Go to Health Check" button as it's now handled by redirects */}
      </div>
    </div>
  );
}
