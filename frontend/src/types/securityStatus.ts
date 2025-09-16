// Security Scan Status Types and Constants

export const SECURITY_SCAN_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
  SKIPPED: "skipped",
} as const;

export type SecurityScanStatus =
  (typeof SECURITY_SCAN_STATUS)[keyof typeof SECURITY_SCAN_STATUS];
