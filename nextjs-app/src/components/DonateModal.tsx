'use client';

import { useState } from 'react';

interface DonateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DonateModal({ isOpen, onClose }: DonateModalProps) {
  const [toast, setToast] = useState(false);

  if (!isOpen) return null;

  const copyDonate = (text: string) => {
    navigator.clipboard.writeText(text);
    setToast(true);
    setTimeout(() => setToast(false), 2000);
  };

  const openJar = () => {
    window.open('https://send.monobank.ua/jar/6Vi9TVzJZQ', '_blank');
  };

  return (
    <>
      <div
        className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      >
        <div
          className="bg-[#1c1c1e] rounded-2xl p-6 max-w-md w-[90%] max-h-[85vh] overflow-y-auto relative"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute top-3 right-4 text-white/50 hover:text-white text-2xl cursor-pointer bg-transparent border-none"
          >
            &times;
          </button>

          <h3 className="text-lg font-medium text-white flex items-center gap-2 mb-2">
            <span className="material-icons text-red-400">favorite</span>
            Підтримати NEPTUN
          </h3>
          <p className="text-white/50 text-sm mb-4">
            Ваша допомога дозволяє нам розвивати карту та робити її ще кращою для всіх українців.
          </p>

          <div className="space-y-3">
            {/* Mono */}
            <div className="bg-white/5 rounded-xl p-3.5">
              <div className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Моно (UAH)</div>
              <div className="text-white font-mono text-sm mb-2">4441 1111 2110 7290</div>
              <button
                onClick={() => copyDonate('4441111121107290')}
                className="text-[11px] text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg px-3 py-1.5 flex items-center gap-1 transition-colors cursor-pointer border-none"
              >
                <span className="material-icons text-[14px]">content_copy</span>
                Копіювати
              </button>
            </div>

            {/* Privat */}
            <div className="bg-white/5 rounded-xl p-3.5">
              <div className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Приват (UAH)</div>
              <div className="text-white font-mono text-sm mb-2">5168 7451 5313 3886</div>
              <button
                onClick={() => copyDonate('5168745153133886')}
                className="text-[11px] text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg px-3 py-1.5 flex items-center gap-1 transition-colors cursor-pointer border-none"
              >
                <span className="material-icons text-[14px]">content_copy</span>
                Копіювати
              </button>
            </div>

            {/* Monobank jar */}
            <div className="bg-white/5 rounded-xl p-3.5">
              <div className="text-white/40 text-[10px] uppercase tracking-wider mb-1">Monobank Банка</div>
              <div className="text-white text-xs mb-2 break-all">send.monobank.ua/jar/6Vi9TVzJZQ</div>
              <div className="flex gap-2">
                <button
                  onClick={openJar}
                  className="text-[11px] text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg px-3 py-1.5 flex items-center gap-1 transition-colors cursor-pointer border-none"
                >
                  <span className="material-icons text-[14px]">open_in_new</span>
                  Відкрити
                </button>
                <button
                  onClick={() => copyDonate('https://send.monobank.ua/jar/6Vi9TVzJZQ')}
                  className="text-[11px] text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg px-3 py-1.5 flex items-center gap-1 transition-colors cursor-pointer border-none"
                >
                  <span className="material-icons text-[14px]">content_copy</span>
                </button>
              </div>
            </div>
          </div>

          <button
            onClick={openJar}
            className="w-full mt-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity cursor-pointer border-none"
          >
            <span className="material-icons">rocket_launch</span>
            Задонатити зараз
          </button>

          <div className="text-center text-white/40 text-xs mt-3">
            Дякуємо за підтримку! 💙💛
          </div>
        </div>
      </div>

      {/* Copy toast */}
      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[10001] bg-green-600 text-white text-sm px-4 py-2 rounded-lg">
          ✓ Скопійовано
        </div>
      )}
    </>
  );
}
