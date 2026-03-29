/** Ultra-Premium Spatial Glassmorphism (Apple Vision Pro / Sci-Fi HUD) */
export const glass = {
  // Central floating pill at the top
  island:
    'rounded-full border border-white/[0.12] bg-[#0a0a0b]/10 shadow-[0_32px_64px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[100px] backdrop-saturate-200 supports-[backdrop-filter]:bg-white/[0.02]',
  // Large expansive glass panels
  panel:
    'rounded-[40px] border border-white/[0.08] bg-[#0a0a0b]/10 shadow-[0_48px_100px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-[100px] backdrop-saturate-[1.8] supports-[backdrop-filter]:bg-white/[0.01]',
  // Bottom dock
  dock:
    'rounded-[32px] border border-white/[0.1] bg-white/[0.02] shadow-[0_24px_48px_rgba(0,0,0,0.5),inset_0_1px_2px_rgba(255,255,255,0.12)] backdrop-blur-[100px] backdrop-saturate-[1.5]',
  // Circular or pill floating buttons
  button:
    'rounded-full relative overflow-hidden border border-white/[0.05] bg-white/[0.04] text-white shadow-[0_8px_32px_rgba(0,0,0,0.3),inset_0_1px_3px_rgba(255,255,255,0.15)] backdrop-blur-[64px] transition-all duration-300 hover:border-white/[0.2] hover:bg-white/[0.12] hover:shadow-[0_0_32px_rgba(255,255,255,0.15)] active:bg-white/[0.06] active:scale-95',
  // Standard card component
  card:
    'rounded-[28px] border border-white/[0.05] bg-[#000000]/30 backdrop-blur-[80px] backdrop-saturate-150 shadow-[0_16px_48px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.04)]',
  // Inner list items
  tile:
    'rounded-[20px] border border-white/[0.03] bg-white/[0.02] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] backdrop-blur-2xl transition-all duration-300 hover:bg-white/[0.05] hover:border-white/[0.08]',
} as const;
