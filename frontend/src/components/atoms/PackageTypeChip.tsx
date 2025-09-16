import React from "react";
import { StatusChip } from "./StatusChip";

export interface PackageTypeChipProps {
  type: "new" | "existing";
  size?: "small" | "medium";
  variant?: "filled" | "outlined";
}

export const PackageTypeChip: React.FC<PackageTypeChipProps> = ({
  type,
  size = "small",
  variant = "outlined",
}) => {
  if (type === "existing") {
    return (
      <StatusChip
        status="Already Processed"
        color="success"
        size={size}
        variant={variant}
      />
    );
  }

  return (
    <StatusChip status="New" color="primary" size={size} variant={variant} />
  );
};

export default PackageTypeChip;
