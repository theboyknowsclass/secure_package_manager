/**
 * Utility functions for formatting scan-related data
 */
import { ScanResult } from "../types/package";

/**
 * Format scan duration from milliseconds to human-readable format
 * @param durationMs - Duration in milliseconds
 * @returns Human-readable duration string (e.g., "1.2s", "850ms", "2m 30s")
 */
export const formatScanDuration = (durationMs: number | null): string => {
  if (durationMs === null || durationMs === undefined) {
    return "-";
  }

  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }

  const seconds = durationMs / 1000;

  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);

  if (minutes < 60) {
    return remainingSeconds > 0
      ? `${minutes}m ${remainingSeconds}s`
      : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
};

/**
 * Get total vulnerability count from scan result
 * @param scanResult - Scan result object
 * @returns Total number of vulnerabilities
 */
export const getTotalVulnerabilities = (
  scanResult: ScanResult | null
): number => {
  if (!scanResult) return 0;

  return (
    (scanResult.critical_count || 0) +
    (scanResult.high_count || 0) +
    (scanResult.medium_count || 0) +
    (scanResult.low_count || 0) +
    (scanResult.info_count || 0)
  );
};

/**
 * Get vulnerability severity breakdown for tooltips
 * @param scanResult - Scan result object
 * @returns Formatted string with severity breakdown
 */
export const getVulnerabilityBreakdown = (
  scanResult: ScanResult | null
): string => {
  if (!scanResult) return "No scan data available";

  const parts = [];

  if (scanResult.critical_count > 0) {
    parts.push(`${scanResult.critical_count} critical`);
  }
  if (scanResult.high_count > 0) {
    parts.push(`${scanResult.high_count} high`);
  }
  if (scanResult.medium_count > 0) {
    parts.push(`${scanResult.medium_count} medium`);
  }
  if (scanResult.low_count > 0) {
    parts.push(`${scanResult.low_count} low`);
  }
  if (scanResult.info_count > 0) {
    parts.push(`${scanResult.info_count} info`);
  }

  if (parts.length === 0) {
    return "No vulnerabilities found";
  }

  return parts.join(", ");
};
