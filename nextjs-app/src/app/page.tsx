'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useAlarms } from '@/hooks/useAlarms';
import { useMarkers } from '@/hooks/useMarkers';
import { useFusionTrajectories } from '@/hooks/useFusionTrajectories';
import { usePresence } from '@/hooks/usePresence';
import Navbar from '@/components/Navbar';
import BallisticBanner from '@/components/BallisticBanner';
import DonateModal from '@/components/DonateModal';
import FaqModal from '@/components/FaqModal';
import TelegramBanner from '@/components/TelegramBanner';
import BottomBar from '@/components/BottomBar';
import DeploymentScreen from '@/components/DeploymentScreen';
import ZoomControls from '@/components/Map/ZoomControls';

// Dynamically import map (no SSR - Leaflet needs window)
const MapContainer = dynamic(() => import('@/components/Map/MapContainer'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#0e1218]">
      <div className="text-[#80d8ff]/40 text-sm animate-pulse">Завантаження карти...</div>
    </div>
  ),
});

export default function HomePage() {
  const { alarms } = useAlarms();
  const { markers, ballisticThreat } = useMarkers();
  const { trajectories } = useFusionTrajectories();
  const presence = usePresence();

  const [donateOpen, setDonateOpen] = useState(false);
  const [faqOpen, setFaqOpen] = useState(false);

  // Map zoom controls - access Leaflet map at runtime (not at import time)
  const getLeafletMap = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    if (w.L && w.L.Map) {
      for (const key of Object.keys(w)) {
        if (w[key] instanceof w.L.Map) return w[key];
      }
    }
    // Fallback: find map from DOM
    const mapEl = document.getElementById('leaflet-map');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (mapEl && (mapEl as any)._leaflet_id != null) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (mapEl as any)._leaflet;
    }
    return null;
  }, []);

  const handleZoomIn = useCallback(() => {
    getLeafletMap()?.zoomIn();
  }, [getLeafletMap]);

  const handleZoomOut = useCallback(() => {
    getLeafletMap()?.zoomOut();
  }, [getLeafletMap]);

  const handleResetZoom = useCallback(() => {
    const map = getLeafletMap();
    if (map) {
      map.fitBounds([[44.2, 22.0], [52.4, 40.2]]);
    }
  }, [getLeafletMap]);

  return (
    <main className="w-full h-screen h-[100dvh] overflow-hidden relative">
      {/* Deployment health check screen */}
      <DeploymentScreen />

      {/* SEO H1 - visible to Google, minimal for users */}
      <h1 className="absolute top-1.5 left-1/2 -translate-x-1/2 z-[5] text-[#8c9099]/40 text-[10px] font-normal text-center whitespace-nowrap pointer-events-none tracking-wide max-md:text-[9px] max-md:whitespace-normal max-md:leading-snug max-md:max-w-[90%]">
        Карта шахедів і тривог України онлайн — повітряна тривога, мапа тривог
      </h1>

      {/* Navbar */}
      <Navbar
        presence={presence}
        onDonate={() => setDonateOpen(true)}
        onFaq={() => setFaqOpen(true)}
      />

      {/* Status Panel removed per request */}

      {/* Ballistic threat banner */}
      <BallisticBanner threat={ballisticThreat} />

      {/* Map */}
      <div id="map-container" className="w-full h-full">
        <MapContainer
          markers={markers}
          alarms={alarms}
          fusionTrajectories={trajectories}
        />
      </div>

      {/* Zoom controls */}
      <ZoomControls
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onReset={handleResetZoom}
      />

      {/* Telegram banner */}
      <TelegramBanner />

      {/* Bottom bar */}
      <BottomBar
        onDonate={() => setDonateOpen(true)}
        onFaq={() => setFaqOpen(true)}
      />

      {/* Modals */}
      <DonateModal isOpen={donateOpen} onClose={() => setDonateOpen(false)} />
      <FaqModal isOpen={faqOpen} onClose={() => setFaqOpen(false)} />

      {/* SEO content - hidden but crawlable (matches original index.html) */}
      <article className="sr-only">
        <h2>Карта тривог та шахедів України онлайн — повітряна тривога в реальному часі</h2>
        <h3>NEPTUN — карта тривог України з радаром шахедів, дронів та ракет</h3>
        <p>NEPTUN — найшвидша карта тривог України онлайн. Відстежуйте повітряні тривоги, шахеди, дрони та ракети в реальному часі на інтерактивній мапі. Оновлення кожні 5 секунд, push-сповіщення, траєкторія польоту шахедів 24/7.</p>

        <h3>Карта тривог України — можливості:</h3>
        <ul>
          <li>Карта тривог онлайн — всі області та райони України</li>
          <li>Карта тривог в реальному часі — миттєве оновлення даних</li>
          <li>Мапа тривог з радаром шахедів та ракет</li>
          <li>Push-сповіщення про тривоги у вашому регіоні</li>
          <li>Мобільний додаток карти тривог для Android та iOS</li>
          <li>Історія тривог та аналітика по регіонах</li>
        </ul>

        <h3>Де подивитися карту тривог?</h3>
        <p>Карта тривог NEPTUN доступна на сайті neptun.in.ua. Це безкоштовна інтерактивна карта тривог України з відстеженням шахедів, дронів та ракет в реальному часі.</p>

        <h3>Карта тривог по областях України</h3>
        <p>Карта тривог охоплює всі області України:</p>
        <nav aria-label="Регіональні карти тривог">
          <a href="/region/kyiv">Тривога Київ</a>{' | '}
          <a href="/region/kharkivska">Тривога Харків</a>{' | '}
          <a href="/region/odeska">Тривога Одеса</a>{' | '}
          <a href="/region/dnipropetrovska">Тривога Дніпро</a>{' | '}
          <a href="/region/zaporizka">Тривога Запоріжжя</a>{' | '}
          <a href="/region/lvivska">Тривога Львів</a>{' | '}
          <a href="/region/mykolaivska">Тривога Миколаїв</a>{' | '}
          <a href="/region/khersonska">Тривога Херсон</a>{' | '}
          <a href="/region/poltavska">Тривога Полтава</a>{' | '}
          <a href="/region/vinnytska">Тривога Вінниця</a>{' | '}
          <a href="/region/cherkaska">Тривога Черкаси</a>{' | '}
          <a href="/region/zhytomyrska">Тривога Житомир</a>{' | '}
          <a href="/region/sumska">Тривога Суми</a>{' | '}
          <a href="/region/chernihivska">Тривога Чернігів</a>{' | '}
          <a href="/region/rivnenska">Тривога Рівне</a>{' | '}
          <a href="/region/volynska">Тривога Луцьк</a>{' | '}
          <a href="/region/ternopilska">Тривога Тернопіль</a>{' | '}
          <a href="/region/ivano-frankivska">Тривога Івано-Франківськ</a>{' | '}
          <a href="/region/zakarpatska">Тривога Ужгород</a>{' | '}
          <a href="/region/chernivetska">Тривога Чернівці</a>{' | '}
          <a href="/region/khmelnytska">Тривога Хмельницький</a>{' | '}
          <a href="/region/kirovohradska">Тривога Кропивницький</a>{' | '}
          <a href="/region/donetska">Тривога Донецьк</a>{' | '}
          <a href="/region/luhanska">Тривога Луганськ</a>
        </nav>

        <h3>Додаток карти тривог NEPTUN</h3>
        <p>Завантажте мобільний додаток карти тривог NEPTUN з <a href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app">Google Play</a> або <a href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk">App Store</a>. Отримуйте миттєві push-сповіщення про повітряні тривоги у вашому регіоні.</p>

        <h3>Як працює карта тривог?</h3>
        <p>Карта тривог NEPTUN збирає інформацію з офіційних джерел та відображає її на інтерактивній мапі. Ви можете бачити активні повітряні тривоги, напрямок руху шахедів та ракет, а також історію попередніх атак.</p>

        <p>Карта тривог NEPTUN — ваш надійний помічник для безпеки. Слідкуйте за повітряними тривогами онлайн 24/7.</p>
      </article>

      {/* Noscript fallback for Googlebot — critical for SEO */}
      <noscript>
        <div style={{ maxWidth: 800, margin: '40px auto', padding: 20, background: '#0a0e17', color: 'rgba(255,255,255,0.8)', fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif", lineHeight: 1.7 }}>
          <h2 style={{ color: '#fff', fontSize: 28, marginBottom: 16 }}>Повітряна тривога онлайн — мапа тривог України</h2>
          <h3 style={{ color: '#fff', fontSize: 20, margin: '24px 0 12px' }}>Карта тривог в реальному часі — NEPTUN</h3>
          <p>NEPTUN — найточніша <strong style={{ color: '#fff' }}>карта тривог України</strong> в реальному часі. Відстежуйте <strong style={{ color: '#fff' }}>повітряні тривоги</strong>, <strong style={{ color: '#fff' }}>шахеди</strong>, дрони та ракети онлайн 24/7.</p>
          <p>Корисні сторінки: <a href="/about" style={{ color: '#4ade80' }}>Про проект</a> · <a href="/faq" style={{ color: '#4ade80' }}>Часті питання</a> · <a href="/privacy" style={{ color: '#4ade80' }}>Політика конфіденційності</a></p>

          <h2 style={{ color: '#fff', fontSize: 28, marginBottom: 16 }}>Що показує карта тривог NEPTUN?</h2>
          <ul style={{ margin: '12px 0', paddingLeft: 24 }}>
            <li style={{ margin: '8px 0' }}><strong style={{ color: '#fff' }}>Повітряна тривога</strong> — активні тривоги по всіх областях України</li>
            <li style={{ margin: '8px 0' }}><strong style={{ color: '#fff' }}>Шахеди онлайн</strong> — відстеження дронів-камікадзе Shahed в реальному часі</li>
            <li style={{ margin: '8px 0' }}><strong style={{ color: '#fff' }}>Ракетна загроза</strong> — крилаті та балістичні ракети</li>
            <li style={{ margin: '8px 0' }}><strong style={{ color: '#fff' }}>БпЛА</strong> — розвідувальні дрони та БПЛА</li>
          </ul>

          <h2 style={{ color: '#fff', fontSize: 28, marginBottom: 16 }}>Переваги карти тривог NEPTUN</h2>
          <ul style={{ margin: '12px 0', paddingLeft: 24 }}>
            <li style={{ margin: '8px 0' }}>Оновлення кожні 5 секунд</li>
            <li style={{ margin: '8px 0' }}>Дані з офіційних джерел (Telegram канали ОВА)</li>
            <li style={{ margin: '8px 0' }}>Безкоштовний додаток для Android та iOS з push-сповіщеннями</li>
            <li style={{ margin: '8px 0' }}>Траєкторія польоту шахедів та ракет</li>
          </ul>

          <h2 style={{ color: '#fff', fontSize: 28, marginBottom: 16 }}>Регіони України</h2>
          <p>Карта тривог охоплює всі області: Київська, Харківська, Одеська, Дніпропетровська, Львівська, Запорізька, Миколаївська, Полтавська, Вінницька, Житомирська, Черкаська, Сумська, Чернігівська, Хмельницька, Волинська, Рівненська, Тернопільська, Івано-Франківська, Закарпатська, Чернівецька, Кіровоградська, Херсонська область та місто Київ.</p>

          <h2 style={{ color: '#fff', fontSize: 28, marginBottom: 16 }}>Завантажити додаток</h2>
          <p>Скачайте безкоштовний додаток NEPTUN та отримуйте миттєві сповіщення про тривоги у вашому регіоні:</p>
          <ul style={{ margin: '12px 0', paddingLeft: 24 }}>
            <li style={{ margin: '8px 0' }}><a href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app" style={{ color: '#4ade80' }}>Завантажити з Google Play (Android)</a></li>
            <li style={{ margin: '8px 0' }}><a href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk" style={{ color: '#4ade80' }}>Завантажити з App Store (iPhone/iPad)</a></li>
          </ul>

          <p><em>Для перегляду інтерактивної карти тривог увімкніть JavaScript у вашому браузері.</em></p>
        </div>
      </noscript>
    </main>
  );
}
