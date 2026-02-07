'use client';

interface ZoomControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

export default function ZoomControls({ onZoomIn, onZoomOut, onReset }: ZoomControlsProps) {
  return (
    <div>
      <button
        onClick={onZoomIn}
        className="w-11 h-11 bg-[#2c2c2e] border border-white/10 rounded-xl text-white/80 text-lg flex items-center justify-center hover:bg-[#3a3a3c] active:bg-[#4a4a4c] hover:text-white transition-all cursor-pointer"
        aria-label="Збільшити масштаб"
      >
        +
      </button>
      <button
        onClick={onZoomOut}
        className="w-11 h-11 bg-[#2c2c2e] border border-white/10 rounded-xl text-white/80 text-lg flex items-center justify-center hover:bg-[#3a3a3c] active:bg-[#4a4a4c] hover:text-white transition-all cursor-pointer"
        aria-label="Зменшити масштаб"
      >
        &minus;
      </button>
      <button
        onClick={onReset}
        className="w-11 h-11 bg-[#2c2c2e] border border-white/10 rounded-xl text-white/80 text-sm flex items-center justify-center hover:bg-[#3a3a3c] active:bg-[#4a4a4c] hover:text-white transition-all cursor-pointer"
        aria-label="Скинути масштаб"
        title="Показати всю Україну"
      >
        <span className="material-icons text-[18px]">fullscreen</span>
      </button>
    </div>
  );
}
