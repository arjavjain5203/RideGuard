"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FaHome, FaFileInvoice, FaMoneyBillWave, FaShieldAlt } from 'react-icons/fa';

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { name: 'Dashboard', href: '/dashboard', icon: FaHome },
    { name: 'Get Policy', href: '/policy', icon: FaShieldAlt },
    { name: 'My Claims', href: '/claims', icon: FaFileInvoice },
    { name: 'Payouts', href: '/payout', icon: FaMoneyBillWave },
    { name: 'Admin', href: '/admin', icon: FaShieldAlt },
  ];

  return (
    <div className="w-64 bg-white shadow-md rounded-xl h-[calc(100vh-6rem)] overflow-y-auto hidden md:block border border-gray-100 p-4">
      <div className="space-y-2">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700 font-medium border border-green-100'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className={isActive ? 'text-green-600' : 'text-gray-400'} />
              {link.name}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
