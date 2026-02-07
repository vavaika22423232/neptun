'use client';

import { useState, useEffect } from 'react';

interface DonateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DonateModal({ isOpen, onClose }: DonateModalProps) {
  const [toast, setToast] = useState(false);

  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

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
        className="fixed inset-0 z-[10000] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-md"
        onClick={onClose}
      >
        <div
          className="bg-[#1a2030] rounded-t-[28px] sm:rounded-[28px] p-5 sm:p-6 w-full sm:max-w-md sm:w-[90%] max-h-[90vh] sm:max-h-[85vh] overflow-y-auto relative shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="w-10 h-1 bg-[#42474e] rounded-full mx-auto mb-4 sm:hidden" />

          <button
            onClick={onClose}
            className="absolute top-3 right-4 text-[#8c9099] hover:text-[#e2e2e6] active:bg-[#42474e]/40 text-2xl cursor-pointer bg-transparent border-none min-w-[44px] min-h-[44px] flex items-center justify-center rounded-xl"
          >
            &times;
          </button>

          <h3 className="text-lg font-medium text-[#e2e2e6] flex items-center gap-2 mb-1">
            <span className="material-icons text-[#ff7eb3]">favorite</span>
            Підтримати NEPTUN
          </h3>
          <p className="text-[#8c9099] text-sm mb-5">
            Допоможіть розвивати карту для всіх українців
          </p>

          <div className="space-y-3">
            <div className="bg-[#222a3a] rounded-2xl p-4">
              <div className="text-[#80d8ff] text-[10px] uppercase tracking-widest font-medium mb-1.5">Моно (UAH)</div>
              <div className="text-[#e2e2e6] font-mono text-sm mb-2.5 tracking-wider">4441 1111 2110 7290</div>
              <button
                onClick={() => copyDonate('4441111121107290')}
                className="text-[11px] text-[#c2c6d0] hover:text-[#e2e2e6] bg-[#80d8ff]/8 hover:bg-[#80d8ff]/14 rounded-xl px-3.5 py-2 flex items-center gap-1.5 transition-all cursor-pointer border-none min-h-[40px]"
              >
                <span className="material-icons text-[14px]">content_copy</span>
                Копіювати
              </button>
            </div>

            <div className="bg-[#222a3a] rounded-2xl p-4">
              <div className="text-[#80d8ff] text-[10px] uppercase tracking-widest font-medium mb-1.5">Приват (UAH)</div>
              <div className="text-[#e2e2e6] font-mono text-sm mb-2.5 tracking-wider">5168 7451 5313 3886</div>
              <button
                onClick={() => copyDonate('5168745153133886')}
                className="text-[11px] text-[#c2c6d0] hover:text-[#e2e2e6] bg-[#80d8ff]/8 hover:bg-[#80d8ff]/14 rounded-xl px-3.5 py-2 flex items-center gap-1.5 transition-all cursor-pointer border-none min-h-[40px]"
              >
                <span className="material-icons text-[14px]">content_copy</span>
                Копіювати
              </button>
            </div>

            <div className="bg-[#222a3a] rounded-2xl p-4">
              <div className="text-[#80d8ff] text-[10px] uppercase tracking-widest font-medium mb-1.5">Monobank Банка</div>
              <div className="text-[#e2e2e6] text-xs mb-2.5 break-all">send.monobank.ua/jar/6Vi9TVzJZQ</div>
              <div className="flex gap-2">
                <button
                  onClick={openJar}
                  className="text-[11px] text-[#c2c6d0] hover:text-[#e2e2e6] bg-[#80d8ff]/8 hover:bg-[#80d8ff]/14 rounded-xl px-3.5 py-2 flex items-center gap-1.5 transition-all cursor-pointer border-none min-h-[40px]"
                >
                  <span className="material-icons text-[14px]">open_in_new</span>
                  Відкрити
                </button>
                <button
                  onClick={() => copyDonate('https://send.monobank.ua/jar/6Vi9TVzJZQ')}
                  className="text-[11px] text-[#c2c6d0] hover:text-[#e2e2e6] bg-[#80d8ff]/8 hover:bg-[#80d8ff]/14 rounded-xl px-3.5 py-2 flex items-center gap-1.5 transition-all cursor-pointer border-none min-h-[40px]"
                >
                  <span className="material-icons text-[14px]">content_copy</span>
                </button>
              </div>
            </div>
          </div>

          <button
            onClick={openJar}
            className="w-full mt-5 py-3.5 bg-gradient-to-r from-[#80d8ff] to-[#b0e0ff] text-[#003549] rounded-2xl font-semibold text-sm flex items-center justify-center gap-2 hover:shadow-[0_4px_16px_rgba(128,216,255,0.3)] active:opacity-90 transition-all cursor-pointer border-none min-h-[48px]"
          >
            <span className="material-icons text-[20px]">rocket_launch</span>
            Задонатити зараз
          </button>

          <div className="text-center text-[#8c9099] text-xs mt-3 pb-1">
            Дякуємо за підтримку! 💙💛
          </div>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[10001] bg-[#69f0ae] text-[#003322] text-sm font-medium px-5 py-2.5 rounded-2xl shadow-[0_4px_16px_rgba(105,240,174,0.3)]">
          ✓ Скопійовано
        </div>
      )}
    </>
  );
}
