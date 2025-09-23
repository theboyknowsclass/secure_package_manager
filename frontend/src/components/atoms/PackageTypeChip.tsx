import React from "react";
import { Chip } from "@mui/material";

export interface PackageTypeChipProps {
  type: "new" | "existing";
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

export const PackageTypeChip: React.FC<PackageTypeChipProps> = React.memo(
  ({ type, size = "small", variant = "outlined" }) => (
    <Chip
      label={type === "existing" ? "Existing" : "New"}
      color={type === "existing" ? "success" : "primary"}
      size={size}
      variant={variant}
    />
  )
);

export default PackageTypeChip;
