import React from "react";
import { Tooltip, Typography } from "@mui/material";
import { StatusChip } from "./StatusChip";

export interface LicenseScoreChipProps {
  score: number | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getScoreColor = (score: number) => {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "error";
};

export const LicenseScoreChip: React.FC<LicenseScoreChipProps> = ({
  score,
  showTooltip = true,
  size = "small",
  variant = "filled",
}) => {
  if (score === null) {
    return (
      <Typography variant="body2" color="textSecondary">
        -
      </Typography>
    );
  }

  const color = getScoreColor(score);
  const chip = (
    <StatusChip
      status={`${score}/100`}
      color={color}
      size={size}
      variant={variant}
    />
  );

  if (showTooltip) {
    return <Tooltip title={`License Score: ${score}/100`}>{chip}</Tooltip>;
  }

  return chip;
};

export default LicenseScoreChip;
