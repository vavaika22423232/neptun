import { endpoints } from '../../../config/api';
import { apiGet, apiRequest, type ApiRequestOptions } from '../../../services/apiClient';
import { authService } from '../../../services/authService';

export type AlertEvent = {
  id: string;
  type: string;
  regionId: string;
  title: string;
  description: string;
  severity: string;
  startedAt: string;
  endedAt: string | null;
  metadataJson?: Record<string, unknown>;
};

export type NotificationRule = {
  id: string;
  enabled: boolean;
  regionIds: string[];
  cityIds: string[];
  threatTypes: string[];
  quietModeEnabled: boolean;
  quietModeStart: string | null;
  quietModeEnd: string | null;
  criticalOverrideEnabled: boolean;
  dedupeWindowMinutes: number;
};

export type MyRadarLocation = {
  id: string;
  label: string;
  type: string;
  regionId: string;
  cityId: string | null;
  sortOrder: number;
};

async function deviceId(): Promise<string> {
  const id = await authService.getDeviceId();
  if (!id) throw new Error('no_device_id');
  return id;
}

async function withDevice(path: string): Promise<string> {
  const id = await deviceId();
  const sep = path.includes('?') ? '&' : '?';
  return `${path}${sep}deviceId=${encodeURIComponent(id)}`;
}

async function authed(options: ApiRequestOptions = {}): Promise<ApiRequestOptions> {
  let token = await authService.getAccessToken();
  if (!token) {
    await authService.login();
    token = await authService.getAccessToken();
  }
  return { ...options, authToken: token ?? null };
}

export const monetizationApi = {
  async fetchAlertHistory(params?: { region?: string; from?: string; type?: string }): Promise<{
    events: AlertEvent[];
    maxDays: number;
    from: string;
    to: string;
  }> {
    const q = new URLSearchParams();
    if (params?.region) q.set('region', params.region);
    if (params?.from) q.set('from', params.from);
    if (params?.type) q.set('type', params.type);
    const base = await withDevice(endpoints.v1AlertsHistory);
    const url = q.toString() ? `${base}&${q}` : base;
    return apiGet(url, await authed());
  },

  async fetchNotificationRules(): Promise<{ rules: NotificationRule[]; limit: number }> {
    return apiGet(await withDevice(endpoints.v1NotificationRules), await authed());
  },

  async createNotificationRule(data: Partial<NotificationRule>): Promise<{ rule: NotificationRule }> {
    const id = await deviceId();
    return apiRequest(
      endpoints.v1NotificationRules,
      await authed({
        method: 'POST',
        body: JSON.stringify({ deviceId: id, ...data }),
      }),
    );
  },

  async updateNotificationRule(id: string, data: Partial<NotificationRule>): Promise<{ rule: NotificationRule }> {
    const devId = await deviceId();
    return apiRequest(
      `${endpoints.v1NotificationRules}/${id}`,
      await authed({
        method: 'PATCH',
        body: JSON.stringify({ deviceId: devId, ...data }),
      }),
    );
  },

  async deleteNotificationRule(id: string): Promise<void> {
    const url = await withDevice(`${endpoints.v1NotificationRules}/${id}`);
    await apiRequest(url, await authed({ method: 'DELETE' }));
  },

  async fetchMyRadar(): Promise<{ locations: MyRadarLocation[]; limit: number }> {
    return apiGet(await withDevice(endpoints.v1MyRadar), await authed());
  },

  async fetchMyRadarSummary(): Promise<{
    locations: Array<{
      location: MyRadarLocation;
      status: string;
      activeThreats: string[];
      lastUpdate: string | null;
      severity: string;
    }>;
    summaryText: string;
    updatedAt: string;
  }> {
    return apiGet(await withDevice(endpoints.v1MyRadarSummary), await authed());
  },

  async addMyRadarLocation(data: {
    label: string;
    regionId: string;
    type?: string;
    cityId?: string | null;
  }): Promise<{ location: MyRadarLocation }> {
    const id = await deviceId();
    return apiRequest(
      endpoints.v1MyRadarLocations,
      await authed({
        method: 'POST',
        body: JSON.stringify({ deviceId: id, ...data }),
      }),
    );
  },

  async deleteMyRadarLocation(id: string): Promise<void> {
    const url = await withDevice(`${endpoints.v1MyRadarLocations}/${id}`);
    await apiRequest(url, await authed({ method: 'DELETE' }));
  },

  async fetchDailyReport(region?: string, date?: string): Promise<{ report: { summaryText: string; totalAlerts: number } }> {
    const q = new URLSearchParams();
    if (region) q.set('region', region);
    if (date) q.set('date', date);
    const base = await withDevice(endpoints.v1ReportsDaily);
    const url = q.toString() ? `${base}&${q}` : base;
    return apiGet(url, await authed());
  },

  async fetchTelegramTemplates(): Promise<{ templates: { id: string; label: string }[] }> {
    return apiGet(await withDevice(endpoints.v1TelegramTemplates), await authed());
  },

  async generateTelegramSummary(input: {
    templateId: string;
    regionId?: string;
    regionName?: string;
    language?: string;
  }): Promise<{ text: string }> {
    const id = await deviceId();
    return apiRequest(
      endpoints.v1TelegramGenerate,
      await authed({
        method: 'POST',
        body: JSON.stringify({ deviceId: id, ...input }),
      }),
    );
  },

  async exportTelegramCard(input: {
    templateId: string;
    regionId?: string;
    regionName?: string;
  }): Promise<{ text: string; filename: string }> {
    const id = await deviceId();
    return apiRequest(
      endpoints.v1TelegramExport,
      await authed({
        method: 'POST',
        body: JSON.stringify({ deviceId: id, ...input }),
      }),
    );
  },

  async fetchRegionStatsDaily(
    regionId: string,
    from?: string,
    to?: string,
  ): Promise<{
    stats: Array<{
      date: string;
      totalAlerts: number;
      totalAlarmMinutes: number;
    }>;
  }> {
    const q = new URLSearchParams({ region: regionId });
    if (from) q.set('from', from);
    if (to) q.set('to', to);
    const base = await withDevice(endpoints.v1RegionsStatsDaily);
    return apiGet(`${base}&${q}`, await authed());
  },
};
