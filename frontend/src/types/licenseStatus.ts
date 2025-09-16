// License Status Types and Constants

export const LICENSE_STATUS = {
  ALWAYS_ALLOWED: "always_allowed",
  ALLOWED: "allowed",
  AVOID: "avoid",
  BLOCKED: "blocked",
} as const;

export type LicenseStatus =
  (typeof LICENSE_STATUS)[keyof typeof LICENSE_STATUS];
