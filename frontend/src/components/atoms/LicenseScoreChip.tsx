import React from "react";
import { Tooltip, Typography, Chip } from "@mui/material";
import { getLicenseColorFromScore } from "../../utils/licenseUtils";

export interface LicenseScoreChipProps {
  score: number | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

export const LicenseScoreChip: React.FC<LicenseScoreChipProps> = React.memo(({
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

  const color = getLicenseColorFromScore(score);
  const chip = (
    <Chip label={`${score}/100`} color={color} size={size} variant={variant} />
  );

  if (showTooltip) {
    return <Tooltip title={`License Score: ${score}/100`}>{chip}</Tooltip>;
  }

  return chip;
});

export default LicenseScoreChip;
