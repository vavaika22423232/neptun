-- NEPTUN monetization platform schema (PostgreSQL)
-- Apply when NEPTUN_POSTGRES_URL is configured.
-- Redis remains primary for hot path; PG for analytics, history, and audit.

CREATE TABLE IF NOT EXISTS monetization_users (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locale TEXT DEFAULT 'uk',
  platform TEXT,
  country TEXT,
  app_version TEXT,
  last_seen_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS monetization_devices (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES monetization_users(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  push_token TEXT,
  app_version TEXT,
  os_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_monetization_devices_user ON monetization_devices(user_id);

CREATE TABLE IF NOT EXISTS monetization_subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES monetization_users(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  product_id TEXT NOT NULL,
  plan TEXT NOT NULL CHECK (plan IN ('pro', 'pro_plus', 'max', 'lifetime')),
  status TEXT NOT NULL DEFAULT 'unknown',
  original_transaction_id TEXT,
  purchase_token TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monetization_subscriptions_user ON monetization_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_monetization_subscriptions_status ON monetization_subscriptions(status);

CREATE TABLE IF NOT EXISTS monetization_notification_rules (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES monetization_users(id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  region_ids JSONB NOT NULL DEFAULT '[]',
  city_ids JSONB NOT NULL DEFAULT '[]',
  threat_types JSONB NOT NULL DEFAULT '[]',
  quiet_mode_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  quiet_mode_start TEXT,
  quiet_mode_end TEXT,
  critical_override_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  dedupe_window_minutes INT NOT NULL DEFAULT 5,
  min_severity TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS monetization_alert_events (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  region_id TEXT,
  city_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT,
  source TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_region_started ON monetization_alert_events(region_id, started_at DESC);

CREATE TABLE IF NOT EXISTS monetization_my_radar_locations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES monetization_users(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  location_type TEXT NOT NULL DEFAULT 'custom',
  region_id TEXT NOT NULL,
  city_id TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_my_radar_user ON monetization_my_radar_locations(user_id);

CREATE TABLE IF NOT EXISTS monetization_region_stats_daily (
  id TEXT PRIMARY KEY,
  region_id TEXT NOT NULL,
  date DATE NOT NULL,
  total_alerts INT NOT NULL DEFAULT 0,
  total_alarm_minutes INT NOT NULL DEFAULT 0,
  shahed_events INT NOT NULL DEFAULT 0,
  missile_events INT NOT NULL DEFAULT 0,
  ballistic_events INT NOT NULL DEFAULT 0,
  avg_duration_minutes NUMERIC,
  max_duration_minutes NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(region_id, date)
);

CREATE TABLE IF NOT EXISTS monetization_feature_flags (
  key TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  rollout_percentage INT NOT NULL DEFAULT 100,
  min_app_version TEXT,
  platform TEXT,
  config_json JSONB DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
