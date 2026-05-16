/** Попап для шару тимчасово окупованих територій (Leaflet / MapLibre). */
export function buildOccupiedTerritoryPopupHtml(nameUk: string): string {
  const esc = nameUk.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return `<article class="neptun-popup-card neptun-popup-card--compact">
    <div class="neptun-popup-card__main">
      <header class="neptun-popup-card__header">
        <h2 class="neptun-popup-card__title">Тимчасово окупована територія</h2>
        <p class="neptun-popup-card__place">${esc}</p>
      </header>
      <p class="neptun-popup-card__occupied-note">Межі за адміністративним поділом України (джерело полігонів — той самий набір, що й області на карті). Ділянки ТОТ на материку через змінний контроль лінії зіткнення тут не виділені окремо.</p>
    </div>
  </article>`;
}
