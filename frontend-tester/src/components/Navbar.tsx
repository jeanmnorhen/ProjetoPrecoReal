// frontend-tester/src/components/Navbar.tsx
"use client";

import Link from "next/link";
import { useAuth } from "../context/AuthContext";
import { auth } from "../../lib/firebase";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const { currentUser } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await auth.signOut();
      router.push("/"); // Redirect to home/login page after logout
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  return (
    <nav className="bg-gray-800 p-4">
      <div className="container mx-auto flex justify-between items-center">
        <Link href="/" className="text-white text-lg font-bold">
          Admin Preço Real
        </Link>
        {currentUser && (
          <div className="space-x-4 flex items-center">
            <Link href="/canonicos" className="text-gray-300 hover:text-white">
              Catálogo
            </Link>
            <Link href="/monitoring" className="text-gray-300 hover:text-white">
              Monitoramento
            </Link>
            <Link href="/healthcheck" className="text-gray-300 hover:text-white">
              Health Check
            </Link>
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
