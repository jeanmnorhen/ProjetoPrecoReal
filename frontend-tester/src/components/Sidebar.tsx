// frontend-tester/src/components/Sidebar.tsx
"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navLinks = [
  { name: 'Dashboard', href: '/admin/dashboard' },
  { name: 'Críticas', href: '/admin/criticas' },
  { name: 'Catálogo', href: '/admin/canonicos' },
  { name: 'Vitrine da Loja', href: '/admin/vitrine' },
  { name: 'Lojas', href: '/lojas' },
  { name: 'Usuários', href: '/usuarios' },
  { name: 'Monitoramento', href: '/monitoring' },
  { name: 'Health Check', href: '/healthcheck' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      <div className="p-4 font-bold text-lg border-b border-gray-700">
        Preço Real
      </div>
      <nav className="flex-grow">
        <ul>
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <li key={link.name}>
                <Link
                  href={link.href}
                  className={`block px-4 py-3 hover:bg-gray-700 ${
                    isActive ? 'bg-gray-700' : ''
                  }`}
                >
                  {link.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
