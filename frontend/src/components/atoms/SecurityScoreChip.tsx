import React from "react";
import { Tooltip, Typography, Chip } from "@mui/material";
import {
  SECURITY_SCAN_STATUS,
  type SecurityScanStatus,
} from "../../types/securityStatus";
import { ScanResult } from "../../types/package";
import {
  getVulnerabilityBreakdown,
  formatScanDuration,
} from "../../utils/scanUtils";

export interface SecurityScoreChipProps {
  score: number | null;
  scanStatus?: SecurityScanStatus;
  scanResult?: ScanResult | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getScoreColor = (score: number) => {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "error";
};

export const SecurityScoreChip: React.FC<SecurityScoreChipProps> = ({
  score,
  scanStatus,
  scanResult,
  showTooltip = true,
  size = "small",
  variant = "filled",
}) => {
  // Handle different scan states
  if (score !== null) {
    const color = getScoreColor(score);
    const chip = (
      <Chip
        label={`${score}/100`}
        color={color}
        size={size}
        variant={variant}
      />
    );

    if (showTooltip) {
      const tooltipContent = (
        <div>
          <div>
            <strong>Security Score:</strong> {score}/100
          </div>
          {scanResult && (
            <>
              <div>
                <strong>Vulnerabilities:</strong>{" "}
                {getVulnerabilityBreakdown(scanResult)}
              </div>
              <div>
                <strong>Scan Duration:</strong>{" "}
                {formatScanDuration(scanResult.scan_duration_ms)}
              </div>
              {score === 0 && scanResult.critical_count > 0 && (
                <div style={{ color: "#f44336", fontWeight: "bold" }}>
                  ⚠️ Critical vulnerabilities block approval
                </div>
              )}
            </>
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
  }

  // Handle scan status when score is not available
  if (scanStatus === SECURITY_SCAN_STATUS.FAILED) {
    const chip = (
      <Chip label="Scan Failed" color="error" size={size} variant={variant} />
    );

    if (showTooltip) {
      return <Tooltip title="Security scan failed">{chip}</Tooltip>;
    }
    return chip;
  }

  if (scanStatus === SECURITY_SCAN_STATUS.RUNNING) {
    const chip = (
      <Chip label="Scanning..." color="info" size={size} variant={variant} />
    );

    if (showTooltip) {
      return <Tooltip title="Security scan in progress">{chip}</Tooltip>;
    }
    return chip;
  }

  // Default case - no score available
  return (
    <Typography variant="body2" color="textSecondary">
      -
    </Typography>
  );
};

export default SecurityScoreChip;
