// Package/Request Status Types (shared workflow)
export const PACKAGE_STATUS = {
  REQUESTED: "requested",
  PERFORMING_LICENCE_CHECK: "performing_licence_check",
  LICENCE_CHECK_COMPLETE: "licence_check_complete",
  PERFORMING_SECURITY_SCAN: "performing_security_scan",
  SECURITY_SCAN_COMPLETE: "security_scan_complete",
  PENDING_APPROVAL: "pending_approval",
  APPROVED: "approved",
  REJECTED: "rejected",
} as const;

export type PackageStatus = typeof PACKAGE_STATUS[keyof typeof PACKAGE_STATUS];

// License Status Types
export const LICENSE_STATUS = {
  ALWAYS_ALLOWED: "always_allowed",
  ALLOWED: "allowed",
  AVOID: "avoid",
  BLOCKED: "blocked",
} as const;

export type LicenseStatus = typeof LICENSE_STATUS[keyof typeof LICENSE_STATUS];

// Status Categories for UI
export const STATUS_CATEGORIES = {
  PENDING: "pending",
  PROCESSING: "processing", 
  COMPLETED: "completed",
} as const;

export type StatusCategory = typeof STATUS_CATEGORIES[keyof typeof STATUS_CATEGORIES];

// Helper functions
export const getStatusCategory = (status: PackageStatus): StatusCategory => {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return STATUS_CATEGORIES.PENDING;
    case PACKAGE_STATUS.PERFORMING_LICENCE_CHECK:
    case PACKAGE_STATUS.PERFORMING_SECURITY_SCAN:
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return STATUS_CATEGORIES.PROCESSING;
    case PACKAGE_STATUS.LICENCE_CHECK_COMPLETE:
    case PACKAGE_STATUS.SECURITY_SCAN_COMPLETE:
      return STATUS_CATEGORIES.PROCESSING;
    case PACKAGE_STATUS.APPROVED:
    case PACKAGE_STATUS.REJECTED:
      return STATUS_CATEGORIES.COMPLETED;
    default:
      return STATUS_CATEGORIES.PENDING;
  }
};

export const isPendingStatus = (status: PackageStatus): boolean => {
  return getStatusCategory(status) === STATUS_CATEGORIES.PENDING;
};

export const isProcessingStatus = (status: PackageStatus): boolean => {
  return getStatusCategory(status) === STATUS_CATEGORIES.PROCESSING;
};

export const isCompletedStatus = (status: PackageStatus): boolean => {
  return getStatusCategory(status) === STATUS_CATEGORIES.COMPLETED;
};

export const isPendingApprovalStatus = (status: PackageStatus): boolean => {
  return status === PACKAGE_STATUS.PENDING_APPROVAL;
};
