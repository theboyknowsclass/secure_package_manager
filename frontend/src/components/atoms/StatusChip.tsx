import React from "react";
import { Chip, ChipProps } from "@mui/material";

export interface StatusChipProps extends Omit<ChipProps, "color"> {
  status: string;
  color?:
    | "default"
    | "primary"
    | "secondary"
    | "error"
    | "info"
    | "success"
    | "warning";
  variant?: "filled" | "outlined";
  size?: "small" | "medium";
}

export const StatusChip: React.FC<StatusChipProps> = ({
  status,
  color = "default",
  variant = "filled",
  size = "small",
  ...props
}) => {
  return (
    <Chip
      label={status}
      color={color}
      variant={variant}
      size={size}
      {...props}
    />
  );
};

export default StatusChip;
