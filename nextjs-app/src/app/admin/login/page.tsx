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
        setError('ACCESS DENIED: INVALID KEY');
      }
    } catch {
      setError('CONNECTION ERROR');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center p-4 selection:bg-[#ff2a5f]/30 font-mono relative overflow-hidden">
      
      {/* Background Matrix/Radar Effect */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-20 flex items-center justify-center">
        <div className="w-[800px] h-[800px] rounded-full border border-[#ff2a5f]/10 absolute animate-[ping_6s_cubic-bezier(0,0,0.2,1)_infinite]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:32px_32px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <div className="bg-[#0a0a0b]/80 backdrop-blur-3xl rounded-[24px] p-10 shadow-[0_32px_64px_rgba(255,42,95,0.1),inset_0_1px_0_rgba(255,255,255,0.06)] border border-[#ff2a5f]/20">
          
          <div className="text-center mb-10 flex flex-col items-center">
            <div className="w-16 h-16 rounded-full border border-[#ff2a5f]/30 flex items-center justify-center mb-6 relative">
              <div className="absolute inset-0 rounded-full border-t-2 border-[#ff2a5f] animate-spin" />
              <div className="w-2 h-2 rounded-full bg-[#ff2a5f] animate-pulse" />
            </div>
            <div className="text-3xl font-bold tracking-[8px] text-white uppercase mb-2">NEPTUN</div>
            <div className="text-xs tracking-[4px] text-[#ff2a5f] uppercase font-bold bg-[#ff2a5f]/10 px-3 py-1 rounded-full">Secure Terminal</div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[10px] text-white/40 mb-3 uppercase tracking-widest font-bold">
                Enter Decryption Key
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••••"
                autoFocus
                className="w-full bg-[#050505] border border-white/10 rounded-xl px-5 py-4 text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/60 focus:ring-1 focus:ring-[#ff2a5f]/40 transition-all font-mono tracking-widest text-center shadow-[inset_0_4px_8px_rgba(0,0,0,0.5)]"
              />
            </div>

            {error && (
              <div className="text-[#ff2a5f] text-[11px] font-bold tracking-widest uppercase bg-[#ff2a5f]/10 rounded-lg px-4 py-3 border border-[#ff2a5f]/30 text-center animate-pulse">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !password}
              className="w-full bg-[#ff2a5f]/20 hover:bg-[#ff2a5f]/30 active:bg-[#ff2a5f]/40 text-[#ff2a5f] font-bold tracking-[4px] uppercase py-4 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed border border-[#ff2a5f]/30 text-[12px] shadow-[0_0_16px_rgba(255,42,95,0.2)]"
            >
              {loading ? 'Authenticating...' : 'Initialize'}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
