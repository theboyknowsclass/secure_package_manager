import React from "react";
import { Tooltip, Chip } from "@mui/material";
import {
  getLicenseColorFromScore,
  getLicenseCategoryFromScore,
} from "../../utils/licenseUtils";

export interface LicenseChipProps {
  identifier: string | null;
  score?: number | null;
  showTooltip?: boolean;
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

export const LicenseChip: React.FC<LicenseChipProps> = React.memo(
  ({
    identifier,
    score = null,
    showTooltip = true,
    size = "small",
    variant = "filled",
  }) => {
    if (!identifier) {
      const chip = (
        <Chip label="Unknown" color="default" size={size} variant={variant} />
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
      <Chip label={identifier} color={color} size={size} variant={variant} />
    );

    if (showTooltip) {
      return <Tooltip title={`${identifier} - ${category}`}>{chip}</Tooltip>;
    }

    return chip;
  }
);

export default LicenseChip;
