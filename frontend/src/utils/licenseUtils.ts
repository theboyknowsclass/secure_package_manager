/**
 * License utility functions for consistent color coding and categorization
 */

export type LicenseColor =
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning";

export type LicenseCategory =
  | "Pending"
  | "Blocked"
  | "Allowed"
  | "Unknown"
  | "Avoid";

/**
 * Get MUI color for license based on score
 */
export const getLicenseColorFromScore = (
  licenseScore: number | null
): LicenseColor => {
  if (licenseScore === null) {
    return "info"; // Pending - blue
  }

  if (licenseScore === 0) {
    return "error"; // Blocked - red
  } else if (licenseScore >= 80) {
    return "success"; // Allowed - green
  } else if (licenseScore >= 50) {
    return "info"; // Unknown - blue
  } else if (licenseScore >= 30) {
    return "warning"; // Avoid - orange
  } else {
    return "error"; // Blocked - red
  }
};

/**
 * Get human-readable category for license based on score
 */
export const getLicenseCategoryFromScore = (
  licenseScore: number | null
): LicenseCategory => {
  if (licenseScore === null) {
    return "Pending";
  }

  if (licenseScore === 0) {
    return "Blocked";
  } else if (licenseScore >= 80) {
    return "Allowed";
  } else if (licenseScore >= 50) {
    return "Unknown";
  } else if (licenseScore >= 30) {
    return "Avoid";
  } else {
    return "Blocked";
  }
};

/**
 * Get MUI color for general score (used for both license and security scores)
 */
export const getScoreColor = (score: number): LicenseColor => {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "error";
};

/**
 * Get MUI color for license identifier string (for direct license matching)
 */
export const getLicenseColorFromIdentifier = (
  licenseIdentifier: string
): LicenseColor => {
  const allowedLicenses = [
    "MIT",
    "Apache-2.0",
    "BSD",
    "CC0-1.0",
    "Unlicense",
    "ISC",
    "0BSD",
  ];

  const avoidLicenses = ["GPL-3.0", "LGPL-3.0"];
  const blockedLicenses = ["GPL", "GPL-2.0", "AGPL"];

  if (allowedLicenses.includes(licenseIdentifier)) {
    return "success";
  } else if (avoidLicenses.includes(licenseIdentifier)) {
    return "warning";
  } else if (blockedLicenses.includes(licenseIdentifier)) {
    return "error";
  } else {
    // Check for partial matches
    if (
      licenseIdentifier.includes("GPL-2.0") ||
      licenseIdentifier.includes("LGPL-2.0")
    ) {
      return "warning";
    } else if (
      licenseIdentifier.includes("GPL-3.0") ||
      licenseIdentifier.includes("LGPL-3.0") ||
      licenseIdentifier.includes("AGPL")
    ) {
      return "error";
    } else if (
      licenseIdentifier.includes("MIT") ||
      licenseIdentifier.includes("Apache-2.0") ||
      licenseIdentifier.includes("BSD") ||
      licenseIdentifier.includes("CC0-1.0") ||
      licenseIdentifier.includes("Unlicense") ||
      licenseIdentifier.includes("ISC") ||
      licenseIdentifier.includes("0BSD")
    ) {
      return "success";
    } else {
      return "default";
    }
  }
};
