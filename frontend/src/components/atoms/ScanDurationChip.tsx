import React from "react";
import { Chip, Tooltip } from "@mui/material";
import { ScanResult } from "../../types/package";
import { formatScanDuration, getVulnerabilityBreakdown } from "../../utils/scanUtils";

export interface ScanDurationChipProps {
  scanResult?: ScanResult | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

export const ScanDurationChip: React.FC<ScanDurationChipProps> = ({
  scanResult,
  showTooltip = true,
  size = "small",
  variant = "outlined",
}) => {
  if (!scanResult || scanResult.scan_duration_ms === null) {
    return (
      <Chip
        label="Pending"
        color="default"
        size={size}
        variant={variant}
      />
    );
  }

  const duration = formatScanDuration(scanResult.scan_duration_ms);
  const chip = (
    <Chip
      label={duration}
      color="info"
      size={size}
      variant={variant}
    />
  );

  if (showTooltip) {
    const tooltipContent = (
      <div>
        <div><strong>Scan Duration:</strong> {duration}</div>
        <div><strong>Scanner:</strong> {scanResult.scan_type}</div>
        {scanResult.trivy_version && (
          <div><strong>Version:</strong> {scanResult.trivy_version}</div>
        )}
        <div><strong>Vulnerabilities:</strong> {getVulnerabilityBreakdown(scanResult)}</div>
        {scanResult.completed_at && (
          <div><strong>Completed:</strong> {new Date(scanResult.completed_at).toLocaleString()}</div>
        )}
      </div>
    );

    return (
      <Tooltip title={tooltipContent} arrow>
        {chip}
      </Tooltip>
    );
  }

  return chip;
};

export default ScanDurationChip;
