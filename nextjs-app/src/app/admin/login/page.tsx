'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        router.push('/admin');
      } else {
        setError('Невірний пароль');
      }
    } catch {
      setError('Помилка підключення');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="bg-[#1a2030] rounded-3xl p-8 shadow-[0_8px_32px_rgba(0,0,0,0.5)] border border-white/5">
          <div className="text-center mb-8">
            <div className="text-2xl font-semibold tracking-[6px] text-white/90 mb-2">NEPTUN</div>
            <div className="text-sm text-[#80d8ff]/60">Адмін-панель</div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs text-white/40 mb-2 uppercase tracking-wider">Пароль</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Введіть пароль"
                autoFocus
                className="w-full bg-[#0e1420] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/40 focus:ring-1 focus:ring-[#80d8ff]/20 transition-all"
              />
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-400/10 rounded-xl px-4 py-2.5 border border-red-400/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !password}
              className="w-full bg-[#80d8ff]/15 hover:bg-[#80d8ff]/25 active:bg-[#80d8ff]/30 text-[#80d8ff] font-medium py-3 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed border border-[#80d8ff]/10"
            >
              {loading ? 'Вхід...' : 'Увійти'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
