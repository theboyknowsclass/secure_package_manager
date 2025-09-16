import React from "react";
import { Tooltip, Typography, Chip } from "@mui/material";
import {
  SECURITY_SCAN_STATUS,
  type SecurityScanStatus,
} from "../../types/securityStatus";

export interface SecurityScoreChipProps {
  score: number | null;
  scanStatus?: SecurityScanStatus;
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
      return <Tooltip title={`Security Score: ${score}/100`}>{chip}</Tooltip>;
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
