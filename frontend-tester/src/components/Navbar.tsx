// frontend-tester/src/components/Navbar.tsx
"use client";

import { useAuth } from "../context/AuthContext";
import { auth } from "../../lib/firebase";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const { currentUser } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      if (!auth) {
        console.error("Firebase authentication is not available.");
        return;
      }
      await auth.signOut();
      router.push("/"); // Redirect to home/login page after logout
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  return (
    <header className="bg-white shadow-sm">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
        <h1 className="text-lg font-semibold leading-6 text-gray-900">Dashboard</h1>
        {currentUser && (
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md"
            >
              Logout
            </button>
        )}
      </div>
    </header>
  );
}
