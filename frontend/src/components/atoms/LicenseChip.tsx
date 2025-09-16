import React from "react";
import { Tooltip } from "@mui/material";
import { StatusChip } from "./StatusChip";

export interface LicenseChipProps {
  identifier: string | null;
  score?: number | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

const getLicenseColorFromScore = (licenseScore: number | null) => {
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

const getLicenseCategoryFromScore = (licenseScore: number | null): string => {
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

export const LicenseChip: React.FC<LicenseChipProps> = ({
  identifier,
  score = null,
  showTooltip = true,
  size = "small",
  variant = "filled",
}) => {
  if (!identifier) {
    const chip = (
      <StatusChip
        status="Unknown"
        color="default"
        size={size}
        variant={variant}
      />
    );

    if (showTooltip) {
      return (
        <Tooltip title="Unknown License - No license information available">
          {chip}
        </Tooltip>
      );
    }
    return chip;
  }

  const color = getLicenseColorFromScore(score);
  const category = getLicenseCategoryFromScore(score);

  const chip = (
    <StatusChip
      status={identifier}
      color={color}
      size={size}
      variant={variant}
    />
  );

  if (showTooltip) {
    return <Tooltip title={`${identifier} - ${category}`}>{chip}</Tooltip>;
  }

  return chip;
};

export default LicenseChip;
