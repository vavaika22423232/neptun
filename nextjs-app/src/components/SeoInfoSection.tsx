'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const REGION_LINKS = [
  { slug: 'kyiv', name: 'Київ' },
  { slug: 'kyivska', name: 'Київська' },
  { slug: 'kharkivska', name: 'Харківська' },
  { slug: 'odeska', name: 'Одеська' },
  { slug: 'dnipropetrovska', name: 'Дніпропетровська' },
  { slug: 'zaporizka', name: 'Запорізька' },
  { slug: 'lvivska', name: 'Львівська' },
  { slug: 'mykolaivska', name: 'Миколаївська' },
  { slug: 'khersonska', name: 'Херсонська' },
  { slug: 'poltavska', name: 'Полтавська' },
  { slug: 'vinnytska', name: 'Вінницька' },
  { slug: 'sumska', name: 'Сумська' },
  { slug: 'chernihivska', name: 'Чернігівська' },
  { slug: 'zhytomyrska', name: 'Житомирська' },
  { slug: 'cherkaska', name: 'Черкаська' },
  { slug: 'rivnenska', name: 'Рівненська' },
  { slug: 'volynska', name: 'Волинська' },
  { slug: 'ternopilska', name: 'Тернопільська' },
  { slug: 'ivano-frankivska', name: 'Івано-Франківська' },
  { slug: 'zakarpatska', name: 'Закарпатська' },
  { slug: 'chernivetska', name: 'Чернівецька' },
  { slug: 'khmelnytska', name: 'Хмельницька' },
  { slug: 'kirovohradska', name: 'Кіровоградська' },
  { slug: 'donetska', name: 'Донецька' },
  { slug: 'luhanska', name: 'Луганська' },
];

export default function SeoInfoSection() {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const handleToggle = () => setExpanded(prev => !prev);
    window.addEventListener('toggle-system-log', handleToggle);
    return () => window.removeEventListener('toggle-system-log', handleToggle);
  }, []);

  return (
    <>
      <div className={`fixed left-0 right-0 z-[1100] transition-all duration-300 bottom-[80px] sm:bottom-[90px] font-mono pointer-events-none`}>
        {/* Expandable content */}
        <article
          className={`pointer-events-auto mx-auto max-w-4xl rounded-t-3xl scrollbar-none overflow-y-auto border-t border-l border-r border-[#ff2a5f]/20 bg-[#0a0a0b]/95 backdrop-blur-3xl transition-all duration-500 ease-[cubic-bezier(0.2,0,0,1)] ${
            expanded ? 'max-h-[60vh] opacity-100' : 'max-h-0 opacity-0 overflow-hidden'
          }`}
        >
          <div className="mx-auto max-w-4xl px-6 py-8 text-[12px] leading-relaxed text-white/50">
            {/* Header */}
            <h2 className="mb-6 text-[14px] font-bold text-white uppercase tracking-[4px] border-b border-[#ff2a5f]/20 pb-4 inline-block">
              <span className="text-[#ff2a5f] mr-2">/RADAR/</span> Карта тривог та шахедів України онлайн
            </h2>
            
            <p className="mb-6 tracking-wide">
              <strong className="text-[#ff2a5f] uppercase tracking-[2px]">NEPTUN COMMAND</strong> — найшвидша <strong className="text-white">карта тривог України</strong> онлайн.
              Відстежуйте <strong className="text-white">повітряні тривоги</strong>, шахеди, дрони та ракети в реальному часі
              на інтерактивній <strong className="text-white">мапі тривог</strong>. Оновлення кожні 5 секунд, push-сповіщення,
              траєкторія польоту шахедів 24/7.
            </p>

            <div className="grid sm:grid-cols-2 gap-8 mb-8">
              <div className="bg-[#050505]/50 p-6 rounded-2xl border border-white/5 relative overflow-hidden group hover:border-[#ff2a5f]/30 transition-colors">
                <div className="absolute top-0 right-0 p-2 opacity-10 text-[10px] uppercase font-bold text-[#ff2a5f] group-hover:opacity-40 transition-opacity">SYS.CAPABILITIES</div>
                <h3 className="mb-4 text-[13px] font-bold text-white uppercase tracking-[2px]">Можливості Радару</h3>
                <ul className="space-y-3 font-mono text-[11px]">
                  <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 bg-[#5ef5c4] shadow-[0_0_8px_#5ef5c4] rounded-full" /> Всі області та райони України </li>
                  <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 bg-[#ff2a5f] shadow-[0_0_8px_#ff2a5f] rounded-full" /> Радар шахедів в реальному часі</li>
                  <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 bg-[#ff2a5f] shadow-[0_0_8px_#ff2a5f] rounded-full" /> Крилаті та балістичні ракети</li>
                  <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 bg-[#5ef5c4] shadow-[0_0_8px_#5ef5c4] rounded-full" /> Push-сповіщення про загрозу</li>
                  <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 bg-[#36e4ff] shadow-[0_0_8px_#36e4ff] rounded-full" /> Мобільний HUD (iOS/Android)</li>
                </ul>
              </div>

              <div className="bg-[#050505]/50 p-6 rounded-2xl border border-white/5 relative overflow-hidden group hover:border-[#ff2a5f]/30 transition-colors">
                <div className="absolute top-0 right-0 p-2 opacity-10 text-[10px] uppercase font-bold text-[#ff2a5f] group-hover:opacity-40 transition-opacity">SYS.ALGORITHM</div>
                <h3 className="mb-4 text-[13px] font-bold text-white uppercase tracking-[2px]">Як працює NEPTUN</h3>
                <p className="mb-3 text-white/50 tracking-wide">
                  Карта тривог автоматично сканує інформацію з Телеграм-каналів та інших відкритих військових джерел. Нейромережа відфільтровує фейки та будує вектори руху цілей.
                </p>
                <p className="text-white/50 tracking-wide border-l-2 border-[#ff2a5f]/50 pl-3">
                  Ви бачите активні загрози: шахеди, КАБ, ракети та розвід-БПЛА в ту ж секунду, як їх фіксує система ППО у відкритому доступі.
                </p>
              </div>
            </div>

            <h3 className="mb-4 text-[13px] font-bold text-white uppercase tracking-[2px]">Регіональна сітка моніторингу</h3>
            <nav aria-label="Регіональні карти тривог" className="mb-8 flex flex-wrap gap-2">
              {REGION_LINKS.map(({ slug, name }) => (
                <Link
                  key={slug}
                  href={`/region/${slug}`}
                  className="rounded border border-white/10 bg-[#050505] px-3 py-1.5 text-[10px] uppercase tracking-wider text-white/40 transition-all hover:border-[#ff2a5f]/40 hover:bg-[#ff2a5f]/10 hover:text-[#ff2a5f]"
                >
                  {name}
                </Link>
              ))}
            </nav>

            <div className="flex flex-wrap items-center gap-3 border-t border-[#ff2a5f]/20 pt-6 text-[10px] uppercase tracking-[1px] text-[#ff2a5f]/60 font-bold">
              <Link href="/about" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">Проєкт</Link>
              <span className="text-[#ff2a5f]/20">/</span>
              <Link href="/faq" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">FAQ</Link>
              <span className="text-[#ff2a5f]/20">/</span>
              <Link href="/tryvoga-zaraz" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">Тривога зараз</Link>
              <span className="text-[#ff2a5f]/20">/</span>
              <Link href="/karta-tryvoh" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">Карта тривог</Link>
              <span className="text-[#ff2a5f]/20">/</span>
              <Link href="/karta-shahediv" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">Карта шахедів</Link>
              <span className="text-[#ff2a5f]/20">/</span>
              <Link href="/radar-shahediv" className="hover:text-[#ff2a5f] hover:underline underline-offset-4">Радар шахедів</Link>
              <span className="flex-1" />
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse" />
                <span>NEPTUN MILITARY HUD © {new Date().getFullYear()}</span>
              </div>
            </div>
          </div>
        </article>
      </div>
    </>
  );
}
