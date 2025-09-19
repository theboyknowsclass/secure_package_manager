// Package Status Types and Constants

export const PACKAGE_STATUS = {
  SUBMITTED: "Submitted",
  PARSED: "Parsed",
  PARSE_FAILED: "Parse Failed",
  CHECKING_LICENCE: "Checking Licence",
  LICENCE_CHECKED: "Licence Checked",
  LICENCE_CHECK_FAILED: "Licence Check Failed",
  DOWNLOADING: "Downloading",
  DOWNLOADED: "Downloaded",
  DOWNLOAD_FAILED: "Download Failed",
  SECURITY_SCANNING: "Security Scanning",
  SECURITY_SCANNED: "Security Scanned",
  SECURITY_SCAN_FAILED: "Security Scan Failed",
  PENDING_APPROVAL: "Pending Approval",
  APPROVED: "Approved",
  REJECTED: "Rejected",
} as const;

export type PackageStatus =
  (typeof PACKAGE_STATUS)[keyof typeof PACKAGE_STATUS];

// Status Categories for UI
export const STATUS_CATEGORIES = {
  PENDING: "pending",
  PROCESSING: "processing",
  COMPLETED: "completed",
} as const;

export type StatusCategory =
  (typeof STATUS_CATEGORIES)[keyof typeof STATUS_CATEGORIES];

// Helper functions
export const getStatusCategory = (status: PackageStatus): StatusCategory => {
  switch (status) {
    case PACKAGE_STATUS.SUBMITTED:
    case PACKAGE_STATUS.PARSED:
      return STATUS_CATEGORIES.PENDING;
    case PACKAGE_STATUS.CHECKING_LICENCE:
    case PACKAGE_STATUS.LICENCE_CHECKED:
    case PACKAGE_STATUS.DOWNLOADING:
    case PACKAGE_STATUS.DOWNLOADED:
    case PACKAGE_STATUS.SECURITY_SCANNING:
    case PACKAGE_STATUS.SECURITY_SCANNED:
    case PACKAGE_STATUS.PENDING_APPROVAL:
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

// Additional helper functions for granular statuses
export const isActiveProcessingStatus = (status: PackageStatus): boolean => {
  const activeStatuses: PackageStatus[] = [
    PACKAGE_STATUS.CHECKING_LICENCE,
    PACKAGE_STATUS.DOWNLOADING,
    PACKAGE_STATUS.SECURITY_SCANNING,
  ];
  return activeStatuses.includes(status);
};

export const isCompletedProcessingStatus = (status: PackageStatus): boolean => {
  const completedStatuses: PackageStatus[] = [
    PACKAGE_STATUS.LICENCE_CHECKED,
    PACKAGE_STATUS.DOWNLOADED,
    PACKAGE_STATUS.SECURITY_SCANNED,
  ];
  return completedStatuses.includes(status);
};

export const getStatusDisplayName = (status: PackageStatus): string => {
  const displayNames: Record<PackageStatus, string> = {
    [PACKAGE_STATUS.SUBMITTED]: "Submitted",
    [PACKAGE_STATUS.PARSED]: "Parsed",
    [PACKAGE_STATUS.CHECKING_LICENCE]: "Checking License",
    [PACKAGE_STATUS.LICENCE_CHECKED]: "License Checked",
    [PACKAGE_STATUS.DOWNLOADING]: "Downloading",
    [PACKAGE_STATUS.DOWNLOADED]: "Downloaded",
    [PACKAGE_STATUS.SECURITY_SCANNING]: "Security Scanning",
    [PACKAGE_STATUS.SECURITY_SCANNED]: "Security Scanned",
    [PACKAGE_STATUS.PENDING_APPROVAL]: "Pending Approval",
    [PACKAGE_STATUS.APPROVED]: "Approved",
    [PACKAGE_STATUS.REJECTED]: "Rejected",
  };
  return displayNames[status] || status;
};
