/** Mirrors Flutter `BallisticAlertService`. */
export type BallisticAlertType = 'threat' | 'allClear';

const MIN_THREAT_DURATION_MS = 10_000;

type RegionCallback = (region: string | null) => void;

class BallisticAlertServiceImpl {
  private threatCallbacks: RegionCallback[] = [];
  private allClearCallbacks: RegionCallback[] = [];
  private _active = false;
  private _region: string | null = null;
  private _lastThreatAt: number | null = null;

  get isActive(): boolean {
    return this._active;
  }

  get currentRegion(): string | null {
    return this._region;
  }

  onThreat(cb: RegionCallback): () => void {
    this.threatCallbacks.push(cb);
    return () => {
      this.threatCallbacks = this.threatCallbacks.filter((x) => x !== cb);
    };
  }

  onAllClear(cb: RegionCallback): () => void {
    this.allClearCallbacks.push(cb);
    return () => {
      this.allClearCallbacks = this.allClearCallbacks.filter((x) => x !== cb);
    };
  }

  triggerThreat(region?: string | null): void {
    this._active = true;
    this._region = region ?? null;
    this._lastThreatAt = Date.now();
    for (const cb of this.threatCallbacks) cb(this._region);
  }

  triggerAllClear(region?: string | null): void {
    if (this._lastThreatAt != null && Date.now() - this._lastThreatAt < MIN_THREAT_DURATION_MS) {
      return;
    }
    this._active = false;
    this._region = null;
    for (const cb of this.allClearCallbacks) cb(region ?? null);
  }

  dismissThreat(): void {
    this._active = false;
    this._region = null;
    this._lastThreatAt = null;
  }

  static detectAlertType(message: string): BallisticAlertType | null {
    const lower = message.toLowerCase();
    if (
      lower.includes('загроза балістики') ||
      lower.includes('загроза балистики') ||
      lower.includes('балістична загроза') ||
      lower.includes('ballistic threat') ||
      (lower.includes('пуск') && lower.includes('балістик'))
    ) {
      return 'threat';
    }
    if (
      lower.includes('відбій загрози балістики') ||
      lower.includes('відбій балістики') ||
      lower.includes('відбій балістичної') ||
      lower.includes('ballistic all clear')
    ) {
      return 'allClear';
    }
    return null;
  }

  static extractRegion(message: string): string | null {
    const patterns = [
      /([\w\-]+ська область)/i,
      /(м\.\s*Київ)/i,
      /(Київ(?:ська)?)/i,
    ];
    for (const re of patterns) {
      const m = message.match(re);
      if (m?.[1]) return m[1];
    }
    return null;
  }
}

export const ballisticAlertService = new BallisticAlertServiceImpl();
