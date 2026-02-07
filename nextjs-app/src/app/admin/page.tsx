'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function AdminPage() {
  const [secret, setSecret] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);

  const authenticate = () => {
    if (secret) {
      setAuthenticated(true);
      fetchStats();
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`/api/health`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-[#0a0e17] text-white flex items-center justify-center">
        <div className="bg-white/5 rounded-2xl p-8 max-w-sm w-full mx-4">
          <h1 className="text-xl font-bold mb-4">Admin Panel</h1>
          <input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && authenticate()}
            placeholder="Enter admin secret"
            className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white placeholder:text-white/30 mb-4 outline-none focus:border-blue-500"
          />
          <button
            onClick={authenticate}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg font-medium transition-colors cursor-pointer"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e17] text-white p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">NEPTUN Admin</h1>
          <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
            &larr; Back to map
          </Link>
        </div>

        {/* Health */}
        <div className="bg-white/5 rounded-xl p-6 mb-4">
          <h2 className="text-lg font-semibold mb-3">Server Health</h2>
          {stats ? (
            <pre className="text-white/60 text-sm overflow-auto">
              {JSON.stringify(stats, null, 2)}
            </pre>
          ) : (
            <p className="text-white/40">Loading...</p>
          )}
        </div>

        {/* Quick links */}
        <div className="grid grid-cols-2 gap-3">
          <a
            href="/api/health"
            target="_blank"
            className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors block text-center"
          >
            <span className="text-white/60 text-sm">Health Check</span>
          </a>
          <a
            href="/api/threats"
            target="_blank"
            className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors block text-center"
          >
            <span className="text-white/60 text-sm">Active Threats</span>
          </a>
        </div>
      </div>
    </div>
  );
}
