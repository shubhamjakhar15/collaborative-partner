import { Link, useLocation } from 'react-router-dom';
import { Bot, Sparkles, Zap, Users } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function Navbar() {
  const location = useLocation();

  const links = [
    { name: 'Home', path: '/' },
    { name: 'About', path: '/about' },
    { name: 'Service', path: '/service' },
    { name: 'Product', path: '/product' },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-black/10 bg-white/70 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-gray-900 font-bold text-xl tracking-tight">
          <div className="bg-blue-600 p-1.5 rounded-lg">
            <Bot size={20} className="text-white" />
          </div>
          Project Partner
        </Link>
        <div className="flex items-center gap-6">
          {links.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                "text-sm font-medium transition-colors hover:text-gray-900",
                location.pathname === link.path ? "text-gray-900" : "text-gray-500"
              )}
            >
              {link.name}
            </Link>
          ))}
          <Link
            to="/product"
            className="ml-4 bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-semibold hover:bg-blue-700 transition-colors"
          >
            Start Free Trial
          </Link>
        </div>
      </div>
    </nav>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-black/10 py-12 mt-auto bg-white/50">
      <div className="max-w-7xl mx-auto px-6 text-center text-gray-500 text-sm">
        <p>© 2026 Project Partner AI. All rights reserved.</p>
      </div>
    </footer>
  );
}
