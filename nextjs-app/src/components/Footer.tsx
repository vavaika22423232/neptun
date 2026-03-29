import Link from 'next/link';

const POPULAR_REGIONS = [
  { slug: 'kyiv', name: 'Київ' },
  { slug: 'kharkivska', name: 'Харківська' },
  { slug: 'odeska', name: 'Одеська' },
  { slug: 'dnipropetrovska', name: 'Дніпропетровська' },
  { slug: 'zaporizka', name: 'Запорізька' },
  { slug: 'lvivska', name: 'Львівська' },
  { slug: 'mykolaivska', name: 'Миколаївська' },
  { slug: 'khersonska', name: 'Херсонська' },
];

export default function Footer() {
  return (
    <footer className="border-t border-[#ff2a5f]/10 mt-12 pt-8 pb-6 text-[12px] text-white/40 bg-[#0a0a0b]/80 backdrop-blur-3xl relative z-10 w-full overflow-hidden">
      {/* Decorative scanline */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#ff2a5f]/50 to-transparent opacity-50"></div>
      
      <div className="max-w-4xl mx-auto px-6 font-mono">
        <div className="grid sm:grid-cols-3 gap-8 mb-8">
          {/* Navigation */}
          <div>
            <h3 className="text-[#ff2a5f] font-bold text-[13px] tracking-[2px] uppercase mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse"></span>
              Навігація
            </h3>
            <ul className="space-y-2">
              {[
                { name: 'Карта тривог', href: '/' },
                { name: 'Карта шахедів', href: '/karta-shahediv' },
                { name: 'Мапа тривог', href: '/karta-tryvoh' },
                { name: 'Радар шахедів', href: '/radar-shahediv' },
                { name: 'Про проєкт', href: '/about' },
                { name: 'FAQ', href: '/faq' },
              ].map(link => (
                <li key={link.name}>
                  <Link href={link.href} className="flex items-center gap-2 text-white/50 hover:text-[#ff2a5f] transition-all hover:translate-x-1">
                    <span className="opacity-0 -ml-3 transition-all text-[10px] group-hover:opacity-100 group-hover:ml-0 text-[#ff2a5f]">{'>'}</span>
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Popular regions */}
          <div>
            <h3 className="text-[#ff2a5f] font-bold text-[13px] tracking-[2px] uppercase mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse"></span>
              Тривога по областях
            </h3>
            <ul className="space-y-2">
              {POPULAR_REGIONS.map(({ slug, name }) => (
                <li key={slug}>
                  <Link href={`/region/${slug}`} className="flex items-center gap-2 text-white/50 hover:text-[#ff2a5f] transition-all hover:translate-x-1 tracking-wider">
                    <span className="opacity-0 -ml-3 transition-all text-[10px] group-hover:opacity-100 group-hover:ml-0 text-[#ff2a5f]">{'>'}</span>
                    {name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Apps & contacts */}
          <div>
            <h3 className="text-[#ff2a5f] font-bold text-[13px] tracking-[2px] uppercase mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse"></span>
              Додатки системи
            </h3>
            <ul className="space-y-2 mb-6">
              <li>
                <a href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-white/50 hover:text-[#36e4ff] transition-all hover:translate-x-1">
                  [ ANDROID TERMINAL ]
                </a>
              </li>
              <li>
                <a href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-white/50 hover:text-[#fff] transition-all hover:translate-x-1">
                  [ IOS COMMAND ]
                </a>
              </li>
            </ul>

            <h3 className="text-[#ff2a5f] font-bold text-[13px] tracking-[2px] uppercase mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse"></span>
              Системні Дані
            </h3>
            <ul className="space-y-2">
              <li><Link href="/contact" className="text-white/50 hover:text-[#ff2a5f] transition-colors">Контакти</Link></li>
              <li><Link href="/privacy" className="text-white/50 hover:text-[#ff2a5f] transition-colors">Конфіденційність</Link></li>
              <li><Link href="/terms" className="text-white/50 hover:text-[#ff2a5f] transition-colors">Умови використання</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#ff2a5f]/10 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-[10px] text-white/30 uppercase tracking-[2px]">
          <span>© {new Date().getFullYear()} NEPTUN MILITARY HUD</span>
          <span className="flex items-center gap-2">
            <span className="w-1 h-1 bg-white/20 rounded-full"></span>
            Не є офіційною системою оповіщення
            <span className="w-1 h-1 bg-white/20 rounded-full"></span>
          </span>
        </div>
      </div>
    </footer>
  );
}
