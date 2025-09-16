// Configuration Types

export interface ConfigStatus {
  is_complete: boolean;
  missing_keys: string[];
  requires_admin_setup: boolean;
  note?: string;
}

export interface ConfigData {
  source_repository_url: string;
  target_repository_url: string;
  source_repository_username: string;
  source_repository_password: string;
  target_repository_username: string;
  target_repository_password: string;
  cache_size_mb: number;
  max_concurrent_downloads: number;
  max_concurrent_scans: number;
  license_check_timeout_seconds: number;
  security_scan_timeout_seconds: number;
  auto_approve_licenses: string[];
  auto_reject_licenses: string[];
  security_score_threshold: number;
  license_score_threshold: number;
  enable_notifications: boolean;
  notification_email: string;
  retention_days: number;
  enable_audit_logging: boolean;
  log_level: string;
  enable_metrics: boolean;
  metrics_retention_days: number;
}
