'use client';

import { useState } from 'react';
import { TELEGRAM_CHANNEL_URL, GOOGLE_PLAY_URL, APP_STORE_URL } from '@/lib/constants';

interface BottomBarProps {
  onDonate: () => void;
  onFaq: () => void;
}

export default function BottomBar({ onDonate, onFaq }: BottomBarProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`bottom-safe fixed bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 z-[1200] bg-[#1a2030]/95 backdrop-blur-2xl border border-[#80d8ff]/8 rounded-[20px] transition-all duration-300 shadow-[0_4px_24px_rgba(0,0,0,0.4)] ${
        expanded
          ? 'w-[calc(100%-24px)] max-w-2xl px-3 py-2'
          : 'w-auto px-2 sm:px-3 py-1.5 sm:py-2'
      }`}
    >
      <div className="flex items-center gap-0 sm:gap-0.5 justify-center">
        {/* Telegram */}
        <a
          href={TELEGRAM_CHANNEL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-3 sm:px-4 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 hover:text-[#2AABEE] transition-all no-underline min-h-[48px] justify-center"
        >
          <span className="material-icons text-[20px]">telegram</span>
          <span className="text-[9px] sm:text-[10px]">Telegram</span>
        </a>

        {/* Android */}
        <a
          href={GOOGLE_PLAY_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-2.5 sm:px-3 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#69f0ae]/8 active:bg-[#69f0ae]/12 hover:text-[#69f0ae] transition-all no-underline min-h-[48px] justify-center"
          aria-label="Завантажити з Google Play"
        >
          <span className="material-icons text-[20px]">android</span>
          <span className="text-[9px] sm:text-[10px]">Android</span>
        </a>

        {/* iOS */}
        <a
          href={APP_STORE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-2.5 sm:px-3 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 hover:text-white transition-all no-underline min-h-[48px] justify-center"
          aria-label="Завантажити з App Store"
        >
          <span className="material-icons text-[20px]">phone_iphone</span>
          <span className="text-[9px] sm:text-[10px]">iOS</span>
        </a>

        {/* FAQ */}
        <button
          onClick={onFaq}
          className="flex flex-col items-center gap-0.5 px-3 sm:px-4 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 hover:text-[#80d8ff] transition-all bg-transparent border-none cursor-pointer min-h-[48px] justify-center"
        >
          <span className="material-icons text-[20px]">help_outline</span>
          <span className="text-[9px] sm:text-[10px]">FAQ</span>
        </button>

        {/* Donate */}
        <button
          onClick={onDonate}
          className="flex flex-col items-center gap-0.5 px-3 sm:px-4 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#ff7eb3]/8 active:bg-[#ff7eb3]/12 hover:text-[#ff7eb3] transition-all bg-transparent border-none cursor-pointer min-h-[48px] justify-center"
        >
          <span className="material-icons text-[20px]">favorite</span>
          <span className="text-[9px] sm:text-[10px]">Донат</span>
        </button>

        {/* Info */}
        <button
          onClick={() => setExpanded(!expanded)}
          className={`flex flex-col items-center gap-0.5 px-3 sm:px-4 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 transition-all bg-transparent border-none cursor-pointer min-h-[48px] justify-center ${
            expanded ? 'bg-[#80d8ff]/10 text-[#80d8ff]' : ''
          }`}
        >
          <span className="material-icons text-[20px]">info</span>
          <span className="text-[9px] sm:text-[10px]">Інфо</span>
        </button>
      </div>

      {expanded && (
        <div className="mt-2 pt-2.5 border-t border-[#80d8ff]/8 max-h-[40vh] overflow-y-auto text-[#c2c6d0] text-[12px] sm:text-[13px] leading-relaxed px-2 sm:px-3 pb-3 scrollbar-none">
          <article itemScope itemType="https://schema.org/Article">
            <meta itemProp="headline" content="Карта шахедів і тривог України онлайн — повітряна тривога в реальному часі" />
            <meta itemProp="author" content="NEPTUN" />
            <meta itemProp="datePublished" content="2024-01-01" />
            <meta itemProp="dateModified" content="2025-01-12" />

            <h2 className="text-[#e2e2e6] text-sm sm:text-base font-medium mb-2">
              Карта шахедів і тривог України — найточніший моніторинг загроз в реальному часі
            </h2>

            <p className="mb-3">
              <strong className="text-[#80d8ff]">NEPTUN</strong> — це сучасна інтерактивна <strong>карта шахедів і тривог України</strong>, яка відображає актуальну інформацію про <strong>повітряні тривоги</strong>, <strong>шахеди</strong>, ракети та інші загрози в режимі реального часу. Наш сервіс допомагає мільйонам українців слідкувати за небезпекою та вчасно реагувати на загрози.
            </p>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Що показує карта повітряних тривог?</h3>
            <p className="mb-2 text-[#8c9099]">Карта тривог NEPTUN надає комплексну інформацію про всі типи загроз:</p>
            <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
              <li><strong className="text-[#c2c6d0]">Повітряна тривога</strong> — активні сирени по всіх 25 областях України з точним часом оголошення та відбою</li>
              <li><strong className="text-[#c2c6d0]">Шахеди онлайн</strong> — відстеження дронів-камікадзе Shahed-136/131 з траєкторією польоту, напрямком руху та швидкістю</li>
              <li><strong className="text-[#c2c6d0]">Крилаті ракети</strong> — моніторинг Х-101, Х-555, Калібр з прогнозом траєкторії</li>
              <li><strong className="text-[#c2c6d0]">Балістичні ракети</strong> — Іскандер, Кинжал та інші балістичні загрози</li>
              <li><strong className="text-[#c2c6d0]">БпЛА розвідники</strong> — розвідувальні дрони типу Орлан, Supercam тощо</li>
            </ul>

            <p className="mb-3 text-[#8c9099]"><strong className="text-[#c2c6d0]">Карта шахедів</strong> інтегрована в <strong>мапу тривог</strong> та <strong>карту повітряних тривог</strong>, щоб користувачі отримували повну картину загроз в одному інтерфейсі.</p>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Чому NEPTUN — найкраща карта тривог і шахедів?</h3>
            <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
              <li><strong className="text-[#c2c6d0]">Швидкість оновлення</strong> — дані оновлюються кожні 5-10 секунд</li>
              <li><strong className="text-[#c2c6d0]">Офіційні джерела</strong> — інформація з Telegram-каналів ОВА</li>
              <li><strong className="text-[#c2c6d0]">Траєкторії шахедів</strong> — унікальна функція відображення напрямку польоту дронів</li>
              <li><strong className="text-[#c2c6d0]">Мобільний додаток</strong> — безкоштовний Android-додаток з push-сповіщеннями</li>
              <li><strong className="text-[#c2c6d0]">Працює 24/7</strong> — цілодобовий моніторинг без перерв</li>
            </ul>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Карта шахедів та дронів онлайн (радар шахедів)</h3>
            <p className="mb-2 text-[#8c9099]">Окрема увага в NEPTUN приділяється <strong className="text-[#c2c6d0]">відстеженню шахедів</strong>. Наш <strong className="text-[#c2c6d0]">радар шахедів</strong> показує:</p>
            <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
              <li>Поточне місцезнаходження <strong className="text-[#c2c6d0]">дронів Shahed</strong> на карті України</li>
              <li>Напрямок польоту та ймовірну ціль</li>
              <li>Кількість дронів у групі</li>
              <li>Область перебування та час входу</li>
            </ul>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Регіони України на карті тривог</h3>
            <p className="mb-2 text-[#8c9099]">Карта охоплює всі адміністративні одиниці України:</p>
            <p className="mb-1 text-[#8c9099]"><strong className="text-[#c2c6d0]">Північ:</strong> Київська, Чернігівська, Сумська, Житомирська</p>
            <p className="mb-1 text-[#8c9099]"><strong className="text-[#c2c6d0]">Схід:</strong> Харківська, Донецька, Луганська, Запорізька</p>
            <p className="mb-1 text-[#8c9099]"><strong className="text-[#c2c6d0]">Південь:</strong> Одеська, Миколаївська, Херсонська</p>
            <p className="mb-1 text-[#8c9099]"><strong className="text-[#c2c6d0]">Центр:</strong> Дніпропетровська, Полтавська, Черкаська, Кіровоградська, Вінницька</p>
            <p className="mb-1 text-[#8c9099]"><strong className="text-[#c2c6d0]">Захід:</strong> Львівська, Волинська, Рівненська, Тернопільська, Хмельницька, Івано-Франківська, Закарпатська, Чернівецька</p>
            <p className="mb-3 text-[#8c9099]"><strong className="text-[#c2c6d0]">Столиця:</strong> місто Київ</p>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Як користуватися картою тривог?</h3>
            <ol className="list-decimal pl-5 space-y-1 mb-3 text-[#8c9099]">
              <li>Відкрийте <a href="https://neptun.in.ua" className="text-[#80d8ff] hover:underline">neptun.in.ua</a> у браузері</li>
              <li>Карта автоматично завантажиться з актуальними даними</li>
              <li>Червоні області — активна <strong className="text-[#c2c6d0]">повітряна тривога</strong></li>
              <li>Іконки на карті — <strong className="text-[#c2c6d0]">шахеди</strong>, ракети та інші загрози</li>
              <li>Натисніть на іконку для детальної інформації</li>
            </ol>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Мобільні додатки карти тривог</h3>
            <p className="mb-2 text-[#8c9099]">Завантажте безкоштовний додаток NEPTUN:</p>
            <div className="flex flex-wrap gap-2 mb-2">
              <a href={GOOGLE_PLAY_URL} className="inline-flex items-center gap-1.5 bg-[#69f0ae]/10 text-[#69f0ae] text-[12px] px-3 py-1.5 rounded-full hover:bg-[#69f0ae]/20 transition-colors no-underline" rel="noopener" target="_blank">
                <span className="material-icons text-[14px]">android</span>
                Google Play
              </a>
              <a href={APP_STORE_URL} className="inline-flex items-center gap-1.5 bg-[#80d8ff]/10 text-[#80d8ff] text-[12px] px-3 py-1.5 rounded-full hover:bg-[#80d8ff]/20 transition-colors no-underline" rel="noopener" target="_blank">
                <span className="material-icons text-[14px]">phone_iphone</span>
                App Store
              </a>
            </div>
            <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
              <li>Push-сповіщення про тривоги у вашому регіоні</li>
              <li>Голосове оповіщення про загрози</li>
              <li>Віджет на головний екран</li>
              <li>Працює у фоновому режимі</li>
            </ul>

            <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Часті питання про карту тривог</h3>
            <h4 className="text-[#c2c6d0] text-[12px] sm:text-[13px] font-medium mt-2 mb-1">Чи є карта тривог офіційною?</h4>
            <p className="mb-2 text-[#8c9099]">NEPTUN агрегує дані з офіційних джерел (Telegram ОВА), але не є державною системою оповіщення.</p>
            <h4 className="text-[#c2c6d0] text-[12px] sm:text-[13px] font-medium mt-2 mb-1">Яка затримка даних?</h4>
            <p className="mb-2 text-[#8c9099]">Дані оновлюються кожні 5-10 секунд. Затримка залежить від швидкості публікації в джерелах.</p>
            <h4 className="text-[#c2c6d0] text-[12px] sm:text-[13px] font-medium mt-2 mb-1">Чи працює карта без інтернету?</h4>
            <p className="mb-2 text-[#8c9099]">Для роботи карти потрібне підключення до інтернету. Мобільний додаток надсилає push-сповіщення навіть при слабкому зв&apos;язку.</p>

            <p className="text-[#8c9099]/60 text-[11px] mt-3">Останнє оновлення: <time dateTime="2025-01-12">12 січня 2025</time></p>
          </article>
        </div>
      )}
    </div>
  );
}
